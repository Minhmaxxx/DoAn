"""
pages/1_Phan_tich_anh.py — Food Detection + HITL Calorie Estimation
The core page of NutriVision.

Features:
- Upload image or capture from camera
- YOLOv8 food detection with bounding box overlay
- Human-in-the-Loop (HITL) sliders per detected food
- Real-time calorie & macro calculation
- LLM nutrition advice generation
"""

import json
import sys
import hashlib
from pathlib import Path

import streamlit as st
from PIL import Image

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

import config
from models.detector import FoodDetector
from utils.nutrition import (
    calculate_adjusted_nutrition,
    sum_meal_nutrition,
    calculate_bmi,
    classify_bmi,
    calculate_bmr,
    calculate_tdee,
    calculate_goal_calories,
    get_macro_targets,
)
from utils.llm import NutriLLM
from utils.history import build_meal_record
from utils.images import ImageInputError, load_uploaded_image
from utils.visualization import macro_donut_chart, calorie_gauge, macro_progress_bars
from utils.state import initialize_session_state

# ─── Initialize session state ─────────────────────────────────────────────────
for key, default in [
    ("detections", []),
    ("annotated_image", None),
    ("detection_slider_keys", []),
    ("meal_nutrition", None),
    ("llm_advice", None),
    ("analysis_done", False),
    ("analysis_image_hash", None),
    ("meal_signature", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

initialize_session_state()


# ─── Cached Detector ──────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Đang tải mô hình YOLOv8...")
def get_detector():
    return FoodDetector()


# ─── Helper: Compute Biometrics ───────────────────────────────────────────────
def compute_biometrics(profile: dict) -> dict:
    bmi = calculate_bmi(profile["weight_kg"], profile["height_cm"])
    bmi_cat, _ = classify_bmi(bmi)
    bmr = calculate_bmr(profile["weight_kg"], profile["height_cm"],
                        profile["age"], profile["gender"])
    tdee = calculate_tdee(bmr, profile["activity_level"])
    return {**profile, "bmi": bmi, "bmi_category": bmi_cat, "bmr": bmr, "tdee": tdee}


def _open_image(source) -> Image.Image | None:
    try:
        return load_uploaded_image(
            source,
            max_pixels=config.MAX_IMAGE_PIXELS,
            max_dimension=config.MAX_IMAGE_DIMENSION,
        )
    except ImageInputError as error:
        st.error(str(error))
        return None


def _reset_analysis(image_hash: str) -> None:
    if st.session_state.analysis_image_hash == image_hash:
        return
    for slider_key in st.session_state.detection_slider_keys:
        st.session_state.pop(slider_key, None)
    st.session_state.detection_slider_keys = []
    st.session_state.detections = []
    st.session_state.annotated_image = None
    st.session_state.meal_nutrition = None
    st.session_state.llm_advice = None
    st.session_state.analysis_done = False
    st.session_state.meal_signature = None
    st.session_state.analysis_image_hash = image_hash


# ─── Main Page ────────────────────────────────────────────────────────────────
def main():
    st.markdown('<h1 class="page-title">Phân tích bữa ăn</h1>', unsafe_allow_html=True)
    st.caption("Tải ảnh, xác nhận khẩu phần, rồi lưu kết quả.")
    st.markdown("---")

    # ── Step 1: Image Upload ────────────────────────────────────────────────
    st.markdown("### 1. Thêm ảnh")
    upload_tab, camera_tab = st.tabs(["Tải ảnh", "Camera"])

    uploaded_image = None
    with upload_tab:
        uploaded_file = st.file_uploader(
            "Ảnh bữa ăn",
            type=["jpg", "jpeg", "png", "webp"],
            help=(
                f"JPG, PNG hoặc WEBP, tối đa {config.MAX_UPLOAD_SIZE_MB} MB. "
                "Ảnh rõ nét từ trên xuống cho kết quả tốt hơn."
            ),
            key="file_uploader",
        )
        if uploaded_file:
            uploaded_image = _open_image(uploaded_file)

    with camera_tab:
        camera_image = st.camera_input("Chụp ảnh", key="camera_input")
        if camera_image:
            uploaded_image = _open_image(camera_image)

    if uploaded_image is None:
        st.info("Thêm ảnh bữa ăn để bắt đầu.")
        _render_sample_hint()
        return

    image_hash = hashlib.sha256(
        uploaded_image.tobytes() + str(uploaded_image.size).encode()
    ).hexdigest()
    _reset_analysis(image_hash)

    # Preview
    col_img, col_info = st.columns([1, 1])
    with col_img:
        st.image(uploaded_image, caption="Ảnh đã chọn", width="stretch")
    with col_info:
        w, h = uploaded_image.size
        st.caption(f"{w} x {h} px · {uploaded_image.mode}")
        analyze_btn = st.button(
            "Phân tích ảnh",
            type="primary",
            width="stretch",
            key="analyze_btn",
        )

    # ── Step 2: Run Detection ───────────────────────────────────────────────
    if analyze_btn:
        st.session_state.analysis_done = False
        st.session_state.meal_nutrition = None
        st.session_state.llm_advice = None
        with st.spinner("Đang nhận diện..."):
            detector = get_detector()
            detections = detector.detect(uploaded_image)

            if not detections:
                st.session_state.detections = []
                st.session_state.annotated_image = None
                st.warning(
                    "Không nhận diện được món ăn. Hãy thử ảnh rõ hơn hoặc món trong danh sách hỗ trợ."
                )
                return

            annotated = detector.draw_boxes(uploaded_image, detections)
            st.session_state.detections = detections
            st.session_state.annotated_image = annotated
            st.session_state.analysis_done = True
            st.session_state.llm_advice = None  # Reset old advice

            # Each detection needs its own portion, including duplicate dishes.
            for slider_key in st.session_state.detection_slider_keys:
                st.session_state.pop(slider_key, None)
            st.session_state.detection_slider_keys = []
            for detection_index, _ in enumerate(detections):
                slider_key = f"portion_detection_{detection_index}"
                st.session_state[slider_key] = 1.0
                st.session_state.detection_slider_keys.append(slider_key)

        st.success(f"Đã tìm thấy {len(detections)} món.")

    # ── Step 3: HITL — Show Results + Sliders ──────────────────────────────
    if st.session_state.analysis_done and st.session_state.detections:
        st.markdown("---")
        st.markdown("### 2. Xác nhận khẩu phần")
        st.caption("Ảnh 2D không đo được khối lượng. Điều chỉnh thanh trượt theo phần ăn thực tế.")

        col_ann, col_hitl = st.columns([1, 1])

        with col_ann:
            if st.session_state.annotated_image:
                st.image(
                    st.session_state.annotated_image,
                    caption="Kết quả nhận diện",
                    width="stretch",
                )

        with col_hitl:
            st.markdown("Khẩu phần")
            adjusted_items = []

            for detection_index, det in enumerate(st.session_state.detections):
                with st.container():
                    st.markdown(f"""
                    <div class="food-card">
                        <strong>{det.display_name}</strong>
                        <span class="confidence-badge">{det.confidence:.0%}</span>
                    </div>
                    """, unsafe_allow_html=True)

                    slider_key = f"portion_detection_{detection_index}"
                    if slider_key not in st.session_state:
                        st.session_state[slider_key] = 1.0

                    ratio = st.slider(
                        f"Khẩu phần ({det.display_name})",
                        min_value=config.SLIDER_MIN,
                        max_value=config.SLIDER_MAX,
                        step=config.SLIDER_STEP,
                        format="%.2fx",
                        key=slider_key,
                        label_visibility="collapsed",
                        help=f"1.0x = 1 khẩu phần chuẩn. Điều chỉnh nếu phần ăn của bạn nhiều hoặc ít hơn.",
                    )

                    # Calculate adjusted nutrition
                    adj = calculate_adjusted_nutrition(det.food_class, ratio)
                    if adj:
                        adjusted_items.append(adj)
                        cols = st.columns(4)
                        cols[0].metric("Calo", f"{adj['calories']:.0f} kcal")
                        cols[1].metric("Carb", f"{adj['carbohydrate_g']:.0f}g")
                        cols[2].metric("Protein", f"{adj['protein_g']:.0f}g")
                        cols[3].metric("Fat", f"{adj['fat_g']:.0f}g")
                        st.caption(f"{ratio}x phần chuẩn · khoảng {adj['portion_g']:.0f}g")
                    st.markdown("<hr style='margin: 8px 0; opacity: 0.2;'>", unsafe_allow_html=True)

        # Meal summary
        if adjusted_items:
            meal_totals = sum_meal_nutrition(adjusted_items)
            meal_signature = json.dumps(adjusted_items, sort_keys=True, ensure_ascii=False)
            if st.session_state.meal_signature != meal_signature:
                st.session_state.llm_advice = None
                st.session_state.meal_signature = meal_signature
            st.session_state.meal_nutrition = {
                "foods": adjusted_items,
               **meal_totals,
                "total_calories": meal_totals["calories"],
            }
            _render_meal_summary(meal_totals, adjusted_items)

    # ── Step 4: LLM Advice and history ─────────────────────────────────────
    if st.session_state.meal_nutrition:
        st.markdown("---")
        st.markdown("### 3. Hoàn tất")
        assistant_enabled = st.toggle(
            "Dùng trợ lý AI",
            key="assistant_enabled",
            help="Tắt để không gửi hồ sơ và bữa ăn hiện tại đến nhà cung cấp LLM.",
        )

        col_btn, col_save = st.columns([1, 1])
        with col_save:
            save_btn = st.button(
                "Lưu bữa ăn",
                width="stretch",
                key="save_btn",
            )

        if save_btn and st.session_state.meal_nutrition:
            _save_to_history(st.session_state.meal_nutrition)
            st.success("Đã lưu bữa ăn vào lịch sử!")

        if not assistant_enabled:
            st.session_state.llm_advice = None
            with col_btn:
                st.button(
                    "Trợ lý AI đang tắt",
                    disabled=True,
                    width="stretch",
                    key="advice_disabled_btn",
                )
            st.markdown(
                "<div class='assistant-status assistant-status-off'>"
                "<strong>Không gửi dữ liệu đến AI</strong><span>Bật công tắc khi cần tư vấn.</span>"
                "</div>",
                unsafe_allow_html=True,
            )
            return

        profile = st.session_state.user_profile
        biometrics = compute_biometrics(profile)
        goal_info = calculate_goal_calories(biometrics["tdee"], profile["goal"])
        macro_targets = get_macro_targets(goal_info["target_calories"], profile["goal"])
        goal_data = {
            "goal_name": profile["goal"],
            "target_calories": goal_info["target_calories"],
            "macro_targets": macro_targets,
        }

        with col_btn:
            get_advice_btn = st.button(
                "Nhận tư vấn",
                type="primary",
                width="stretch",
                key="advice_btn",
            )

        with st.expander("Thông tin cá nhân đang dùng", expanded=False):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("BMI", f"{biometrics['bmi']}", biometrics["bmi_category"])
            c2.metric("TDEE", f"{biometrics['tdee']:.0f} kcal/ngày")
            c3.metric("Mục tiêu calo", f"{goal_info['target_calories']:.0f} kcal")
            c4.metric("Mục tiêu", profile["goal"])
            st.caption("Chỉnh thông tin tại trang Hồ sơ.")

        if get_advice_btn:
            runtime_config = st.session_state.get("llm_runtime_config", {})
            provider = runtime_config.get("provider", config.LLM_PROVIDER)
            google_key = runtime_config.get("google_api_key", "").strip() or None
            openai_key = runtime_config.get("openai_api_key", "").strip() or None
            llm = NutriLLM(
                provider=provider,
                google_api_key=google_key,
                openai_api_key=openai_key,
            )
            with st.container(border=True):
                st.caption("Tư vấn AI")
                advice_container = st.empty()
                full_advice = ""

                with st.spinner("AI đang phân tích và viết tư vấn..."):
                    for chunk in llm.stream_advice(
                        biometrics,
                        st.session_state.meal_nutrition,
                        goal_data,
                    ):
                        full_advice += chunk
                        advice_container.markdown(full_advice + "▌")

                advice_container.markdown(full_advice)
            st.session_state.llm_advice = full_advice

        elif st.session_state.llm_advice:
            with st.container(border=True):
                st.caption("Tư vấn AI")
                st.markdown(st.session_state.llm_advice)


def _render_meal_summary(meal_totals: dict, adjusted_items: list):
    """Render the meal summary section with charts."""
    st.markdown("---")
    st.markdown("### Tổng dinh dưỡng")

    profile = st.session_state.user_profile
    biometrics = compute_biometrics(profile)
    goal_info = calculate_goal_calories(biometrics["tdee"], profile["goal"])
    macro_targets = get_macro_targets(goal_info["target_calories"], profile["goal"])

    col_gauge, col_donut, col_bars = st.columns(3)

    with col_gauge:
        fig_gauge = calorie_gauge(
            meal_totals["calories"],
            goal_info["target_calories"],
            title="Calo Bữa Ăn",
        )
        st.plotly_chart(fig_gauge, width="stretch", config={"displayModeBar": False})

    with col_donut:
        fig_donut = macro_donut_chart(
            meal_totals["carbohydrate_g"],
            meal_totals["protein_g"],
            meal_totals["fat_g"],
        )
        st.plotly_chart(fig_donut, width="stretch", config={"displayModeBar": False})

    with col_bars:
        fig_bars = macro_progress_bars(
            meal_totals,
            macro_targets,
            title="Tiến độ Macro Bữa Ăn so với Mục tiêu Ngày",
        )
        st.plotly_chart(fig_bars, width="stretch", config={"displayModeBar": False})

    # Summary table
    st.markdown("Chi tiết")
    table_data = []
    for item in adjusted_items:
        table_data.append({
            "Món ăn": item["display_name"],
            "Khẩu phần": f"{item['portion_multiplier']}x ({item['portion_g']}g)",
            "Calo (kcal)": f"{item['calories']:.0f}",
            "Carb (g)": f"{item['carbohydrate_g']:.1f}",
            "Protein (g)": f"{item['protein_g']:.1f}",
            "Fat (g)": f"{item['fat_g']:.1f}",
        })

    table_data.append({
            "Món ăn": "TỔNG CỘNG",
            "Khẩu phần": "-",
            "Calo (kcal)": f"{meal_totals['calories']:.0f}",
            "Carb (g)": f"{meal_totals['carbohydrate_g']:.1f}",
            "Protein (g)": f"{meal_totals['protein_g']:.1f}",
            "Fat (g)": f"{meal_totals['fat_g']:.1f}",
    })

    import pandas as pd
    df = pd.DataFrame(table_data)
    st.dataframe(df, width="stretch", hide_index=True)


def _save_to_history(meal_data: dict):
    """Save the current meal only within the active browser session."""
    st.session_state.meal_history.append(build_meal_record(meal_data))


def _render_sample_hint():
    """Show sample food list when no image uploaded."""
    st.markdown("---")
    st.markdown("Món được hỗ trợ")
    import config

    badges = "".join(
        f"<div class='food-badge'>{config.FOOD_DISPLAY_NAMES[food_class]}</div>"
        for food_class in config.FOOD_CLASSES
    )
    st.markdown(f"<div class='food-grid'>{badges}</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
