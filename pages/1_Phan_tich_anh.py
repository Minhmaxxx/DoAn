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
from html import escape
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
from utils.repository import SessionRepository, get_repository
from utils.images import ImageInputError, load_uploaded_image
from utils.visualization import macro_donut_chart, calorie_gauge, macro_progress_bars
from utils.state import initialize_session_state
from utils.ui import render_page_header, render_section_header

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
    ("saved_meal_signatures", set()),
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
            max_source_pixels=config.MAX_SOURCE_IMAGE_PIXELS,
            max_source_dimension=config.MAX_SOURCE_IMAGE_DIMENSION,
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
    st.session_state.saved_meal_signatures = set()
    st.session_state.analysis_image_hash = image_hash


# ─── Main Page ────────────────────────────────────────────────────────────────
def main():
    render_page_header(
        "CAMERA → YOLO → BẠN XÁC NHẬN",
        "Phân tích bữa ăn.",
        "AI chỉ gợi ý. Bạn chọn món đúng, bỏ detection sai và điều chỉnh khẩu phần trước khi tính.",
        meta="TỐI ĐA 25 MP",
    )

    if not st.session_state.profile_completed:
        st.warning("Hãy lưu hồ sơ trước để NutriVision dùng đúng thông tin của bạn.")
        if st.button("Điền hồ sơ", type="primary", width="stretch"):
            st.switch_page("pages/3_Ho_so.py")
        return

    # ── Step 1: Image Upload ────────────────────────────────────────────────
    render_section_header(
        "01",
        "Thêm ảnh bữa ăn",
        "Dùng ảnh rõ, đủ sáng và ưu tiên góc chụp từ trên xuống.",
    )
    with st.container(key="analysis-input"):
        upload_tab, camera_tab = st.tabs(["Tải ảnh", "Camera"])

    uploaded_image = None
    with upload_tab:
        uploaded_file = st.file_uploader(
            "Ảnh bữa ăn",
            type=["jpg", "jpeg", "png", "webp"],
            help=(
                f"JPG, PNG hoặc WEBP, tối đa {config.MAX_UPLOAD_SIZE_MB} MB. "
                "Ảnh rõ nét từ trên xuống cho kết quả tốt hơn; ảnh độ phân giải "
                "quá cao nên chuyển camera về chế độ chụp thường."
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
    with st.container(key="analysis-preview"):
        col_img, col_info = st.columns([1.2, 0.8], gap="large")
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

            # Each detection keeps independent confirmation, label, and portion state.
            for slider_key in st.session_state.detection_slider_keys:
                st.session_state.pop(slider_key, None)
            st.session_state.detection_slider_keys = []
            for detection_index, detection in enumerate(detections):
                include_key = f"include_detection_{detection_index}"
                class_key = f"class_detection_{detection_index}"
                slider_key = f"portion_detection_{detection_index}"
                st.session_state[include_key] = True
                st.session_state[class_key] = detection.food_class
                st.session_state[slider_key] = 1.0
                st.session_state.detection_slider_keys.extend(
                    [include_key, class_key, slider_key]
                )

        st.success(f"Đã tìm thấy {len(detections)} món.")

    # ── Step 3: HITL — Show Results + Sliders ──────────────────────────────
    if st.session_state.analysis_done and st.session_state.detections:
        render_section_header(
            "02",
            "Xác nhận món và khẩu phần",
            "Ảnh 2D không đo được khối lượng; hãy sửa nhãn và điều chỉnh theo phần ăn thực tế.",
        )

        with st.container(key="analysis-results"):
            col_ann, col_hitl = st.columns([1, 1], gap="large")

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
                        <strong>{escape(det.display_name)}</strong>
                        <span class="confidence-badge">{det.confidence:.0%}</span>
                    </div>
                    """, unsafe_allow_html=True)

                    include_key = f"include_detection_{detection_index}"
                    class_key = f"class_detection_{detection_index}"
                    slider_key = f"portion_detection_{detection_index}"
                    if include_key not in st.session_state:
                        st.session_state[include_key] = True
                    if class_key not in st.session_state:
                        st.session_state[class_key] = det.food_class
                    st.checkbox(
                        f"Tính {det.display_name} vào bữa ăn",
                        key=include_key,
                    )
                    selected_food_class = st.selectbox(
                        f"Xác nhận món ăn cho {det.display_name}",
                        config.FOOD_CLASSES,
                        format_func=lambda food_class: config.FOOD_DISPLAY_NAMES[food_class],
                        key=class_key,
                        help="Đổi nhãn nếu mô hình nhận diện chưa đúng.",
                    )

                    if not st.session_state[include_key]:
                        st.caption("Món này đã được loại khỏi tổng dinh dưỡng.")
                        st.markdown("<hr style='margin: 8px 0; opacity: 0.2;'>", unsafe_allow_html=True)
                        continue

                    if slider_key not in st.session_state:
                        st.session_state[slider_key] = 1.0

                    ratio = st.slider(
                        f"Khẩu phần ({config.FOOD_DISPLAY_NAMES[selected_food_class]})",
                        min_value=config.SLIDER_MIN,
                        max_value=config.SLIDER_MAX,
                        step=config.SLIDER_STEP,
                        format="%.2fx",
                        key=slider_key,
                        label_visibility="collapsed",
                        help=f"1.0x = 1 khẩu phần chuẩn. Điều chỉnh nếu phần ăn của bạn nhiều hoặc ít hơn.",
                    )

                    # Calculate adjusted nutrition
                    adj = calculate_adjusted_nutrition(selected_food_class, ratio)
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
        else:
            st.session_state.meal_nutrition = None
            st.session_state.llm_advice = None
            st.info("Hãy giữ lại ít nhất một món để tính tổng dinh dưỡng.")

    # ── Step 4: LLM Advice and history ─────────────────────────────────────
    if st.session_state.meal_nutrition:
        render_section_header(
            "03",
            "Lưu hoặc hỏi trợ lý",
            "Lưu vào nhật ký phiên này; chỉ gửi dữ liệu tới AI khi bạn chủ động yêu cầu.",
        )
        assistant_enabled = st.toggle(
            "Dùng trợ lý AI",
            key="assistant_enabled",
            help="Tắt để không gửi hồ sơ và bữa ăn hiện tại đến nhà cung cấp LLM.",
        )

        current_signature = st.session_state.meal_signature
        already_saved = current_signature in st.session_state.saved_meal_signatures
        col_btn, col_save = st.columns([1, 1])
        with col_save:
            save_btn = st.button(
                "Đã lưu bữa ăn" if already_saved else "Lưu bữa ăn",
                width="stretch",
                key="save_btn",
                disabled=already_saved,
            )

        if save_btn and st.session_state.meal_nutrition:
            try:
                saved = _save_to_history(
                    st.session_state.meal_nutrition, current_signature
                )
            except Exception as error:
                st.error(f"Không lưu được bữa ăn lên máy chủ: {error}")
            else:
                if saved:
                    st.success("Đã lưu bữa ăn vào lịch sử!")
                else:
                    st.info("Bữa ăn này đã được lưu.")

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
    st.markdown("<p class='panel-kicker summary-kicker'>TỔNG DINH DƯỠNG ĐÃ XÁC NHẬN</p>", unsafe_allow_html=True)

    profile = st.session_state.user_profile
    biometrics = compute_biometrics(profile)
    goal_info = calculate_goal_calories(biometrics["tdee"], profile["goal"])
    macro_targets = get_macro_targets(goal_info["target_calories"], profile["goal"])

    with st.container(key="analysis-summary"):
        col_gauge, col_donut, col_bars = st.columns(3, gap="small")

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


def _save_to_history(meal_data: dict, signature: str) -> bool:
    """Save the confirmed meal through whichever repository this session uses.

    Guests keep the exact previous behaviour (session only); a synced account
    writes to Supabase first and only mirrors into session state once the
    server accepted it, so the history never shows a meal that was not stored.
    Raises on a failed cloud write — the caller reports it instead of showing
    a false "Đã lưu".
    """
    repo = get_repository()
    if isinstance(repo, SessionRepository):
        return repo.save_meal(meal_data, signature)

    if signature in st.session_state.saved_meal_signatures:
        return False
    saved = repo.save_meal(meal_data, signature)
    if saved:
        st.session_state.saved_meal_signatures.add(signature)
        st.session_state.meal_history = repo.load_meals()
    return saved


def _render_sample_hint():
    """Show sample food list when no image uploaded."""
    st.markdown("<p class='panel-kicker supported-kicker'>12 MÓN ĐANG ĐƯỢC HỖ TRỢ</p>", unsafe_allow_html=True)
    import config

    badges = "".join(
        f"<div class='food-badge'>{config.FOOD_DISPLAY_NAMES[food_class]}</div>"
        for food_class in config.FOOD_CLASSES
    )
    st.markdown(f"<div class='food-grid'>{badges}</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
