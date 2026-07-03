"""
pages/3_Ho_so.py — User Profile & Biometric Setup
Collects user's biometric data and computes health metrics (BMI, BMR, TDEE).
"""

import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

import config
from utils.nutrition import (
    calculate_bmi, classify_bmi,
    calculate_bmr, calculate_tdee,
    calculate_goal_calories, get_macro_targets,
)
from utils.visualization import macro_donut_chart

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Hồ sơ — NutriVision",
    layout="wide",
)

css_path = ROOT_DIR / "assets" / "style.css"
if css_path.exists():
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ─── Init session state ───────────────────────────────────────────────────────
if "user_profile" not in st.session_state:
    st.session_state.user_profile = {
        "name": "",
        "age": 22,
        "gender": "Nam",
        "weight_kg": 65.0,
        "height_cm": 170.0,
        "activity_level": "Vừa phải (3-5 ngày/tuần)",
        "goal": "Giữ cân",
    }


def main():
    st.markdown('<h1 class="page-title"> Hồ sơ Cá nhân</h1>', unsafe_allow_html=True)
    st.markdown(
        "Nhập thông tin sinh trắc học để hệ thống tính toán "
        "**BMI, BMR, TDEE** và cá nhân hóa lời tư vấn dinh dưỡng."
    )
    st.markdown("---")

    profile = st.session_state.user_profile
    col_form, col_results = st.columns([1, 1])

    # ── Form ───────────────────────────────────────────────────────────────
    with col_form:
        st.markdown("### Thông tin cơ bản")

        with st.form("profile_form"):
            profile["name"] = st.text_input(
                "Tên của bạn",
                value=profile.get("name", ""),
                placeholder="Nguyễn Văn A",
            )

            col_g, col_a = st.columns(2)
            profile["gender"] = col_g.selectbox(
                "Giới tính",
                ["Nam", "Nữ"],
                index=0 if profile.get("gender", "Nam") == "Nam" else 1,
            )
            profile["age"] = col_a.number_input(
                "Tuổi",
                min_value=10, max_value=100,
                value=profile.get("age", 22),
            )

            col_h, col_w = st.columns(2)
            profile["height_cm"] = col_h.number_input(
                "Chiều cao (cm)",
                min_value=100.0, max_value=250.0,
                value=float(profile.get("height_cm", 170.0)),
                step=0.5,
                format="%.1f",
            )
            profile["weight_kg"] = col_w.number_input(
                "Cân nặng (kg)",
                min_value=30.0, max_value=300.0,
                value=float(profile.get("weight_kg", 65.0)),
                step=0.5,
                format="%.1f",
            )

            st.markdown("#### Mức độ vận động")
            profile["activity_level"] = st.select_slider(
                "Chọn mức độ vận động",
                options=[
                    "Ít vận động (ngồi nhiều)",
                    "Nhẹ nhàng (1-3 ngày/tuần)",
                    "Vừa phải (3-5 ngày/tuần)",
                    "Tích cực (6-7 ngày/tuần)",
                    "Rất tích cực (vận động viên)",
                ],
                value=profile.get("activity_level", "Vừa phải (3-5 ngày/tuần)"),
                label_visibility="collapsed",
            )

            st.markdown("#### Mục tiêu sức khỏe")
            profile["goal"] = st.radio(
                "Mục tiêu",
                ["Giảm cân", "Giảm cân nhanh", "Giữ cân", "Tăng cơ", "Tăng cân"],
                index=["Giảm cân", "Giảm cân nhanh", "Giữ cân", "Tăng cơ", "Tăng cân"].index(
                    profile.get("goal", "Giữ cân")
                ),
                horizontal=True,
                label_visibility="collapsed",
            )

            submitted = st.form_submit_button(
                " Lưu Hồ sơ",
                type="primary",
                use_container_width=True,
            )
            if submitted:
                st.session_state.user_profile = profile
                st.success(" Đã lưu thông tin hồ sơ!")
                st.rerun()

    # ── Results ────────────────────────────────────────────────────────────
    with col_results:
        st.markdown("### Chỉ số sức khỏe")

        bmi = calculate_bmi(profile["weight_kg"], profile["height_cm"])
        bmi_cat, bmi_color = classify_bmi(bmi)
        bmr = calculate_bmr(profile["weight_kg"], profile["height_cm"],
                            profile["age"], profile["gender"])
        tdee = calculate_tdee(bmr, profile["activity_level"])
        goal_info = calculate_goal_calories(tdee, profile["goal"])
        macro_targets = get_macro_targets(goal_info["target_calories"], profile["goal"])

        # BMI Card
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid {bmi_color};">
            <div class="metric-label">Chỉ số Khối cơ thể (BMI)</div>
            <div class="metric-value" style="color: {bmi_color};">{bmi}</div>
            <div class="metric-unit">{bmi_cat}</div>
        </div>
        """, unsafe_allow_html=True)

        # BMI scale visual
        _render_bmi_scale(bmi)

        st.markdown("---")

        col_m1, col_m2 = st.columns(2)
        col_m1.metric(
            " BMR (Trao đổi cơ bản)",
            f"{bmr:.0f} kcal/ngày",
            help="Năng lượng cơ thể cần để duy trì sự sống khi nghỉ ngơi hoàn toàn.",
        )
        col_m2.metric(
            " TDEE (Tổng tiêu hao)",
            f"{tdee:.0f} kcal/ngày",
            help="Tổng năng lượng cơ thể bạn đốt cháy mỗi ngày dựa trên mức vận động.",
        )

        st.markdown("---")
        st.markdown(f"#### Mục tiêu: **{profile['goal']}**")

        col_t1, col_t2 = st.columns(2)
        col_t1.metric(
            "Calo mục tiêu/ngày",
            f"{goal_info['target_calories']:.0f} kcal",
            f"{goal_info['calorie_change']:+.0f} kcal vs TDEE",
        )
        col_t2.markdown(
            f"<div class='goal-desc'>{goal_info['description']}</div>",
            unsafe_allow_html=True,
        )

        st.markdown("---")
        st.markdown("#### Phân bổ Macro Khuyến nghị/ngày")

        col_m, col_m2, col_m3 = st.columns(3)
        col_m.metric(" Carbohydrate", f"{macro_targets['carbohydrate_g']:.0f}g")
        col_m2.metric(" Protein", f"{macro_targets['protein_g']:.0f}g")
        col_m3.metric(" Fat", f"{macro_targets['fat_g']:.0f}g")

        fig = macro_donut_chart(
            macro_targets["carbohydrate_g"] / 4,  # Placeholder: g → kcal
            macro_targets["protein_g"] / 4,
            macro_targets["fat_g"] / 9,
            title=f"Phân bổ Macro — {profile['goal']}",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── LLM API Config ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Cấu hình API")

    with st.expander(" Nhập API Key (không bắt buộc)", expanded=False):
        st.info(
            "API key được lưu vào file `.env` LOCAL — **không bao giờ** upload lên cloud hay GitHub. "
            "Nếu đã có file `.env`, bỏ qua bước này."
        )
        col_k1, col_k2 = st.columns(2)
        gemini_key = col_k1.text_input(
            "Google Gemini API Key",
            type="password",
            placeholder="AIza...",
            help="Lấy miễn phí tại aistudio.google.com",
        )
        openai_key = col_k2.text_input(
            "OpenAI API Key (tuỳ chọn)",
            type="password",
            placeholder="sk-...",
        )

        llm_provider = st.selectbox("Nhà cung cấp LLM", ["gemini", "openai"])

        if st.button(" Lưu API Key vào .env", key="save_api"):
            _save_env_file(gemini_key, openai_key, llm_provider)
            st.success(" Đã lưu vào file `.env`. Hãy **khởi động lại ứng dụng** để áp dụng.")

    # ── About project ──────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander(" Về Dự án"):
        st.markdown("""
       **NutriVision** là đồ án tốt nghiệp ngành Khoa học Máy tính.

       **Công nghệ sử dụng:**
        - **YOLOv8n** (Ultralytics) — Object Detection nhận diện 10 món ăn Việt Nam
        - **Human-in-the-Loop (HITL)** — Slider tinh chỉnh khẩu phần để giảm sai số
        - **Google Gemini / OpenAI GPT** — Sinh lời khuyên dinh dưỡng cá nhân hóa
        - **Streamlit** — Web App Python full-stack

       **Giới hạn:**
        Hệ thống không thay thế tư vấn y tế chuyên nghiệp.
        Độ chính xác calo phụ thuộc vào chất lượng ảnh và hiệu chỉnh HITL của người dùng.
        """)


def _render_bmi_scale(bmi: float):
    """Render a simple BMI scale indicator."""
    # BMI ranges: <18.5 (Thiếu cân), 18.5-23 (Bình thường), 23-27.5 (Thừa cân), >27.5 (Béo phì)
    clamped = max(14, min(bmi, 35))
    pct = (clamped - 14) / (35 - 14) * 100

    st.markdown(f"""
    <div class="bmi-scale-container">
        <div class="bmi-scale-bar">
            <div class="bmi-segment seg-underweight">Thiếu cân<br><small>&lt;18.5</small></div>
            <div class="bmi-segment seg-normal">Bình thường<br><small>18.5–23</small></div>
            <div class="bmi-segment seg-overweight">Thừa cân<br><small>23–27.5</small></div>
            <div class="bmi-segment seg-obese">Béo phì<br><small>&gt;27.5</small></div>
        </div>
        <div class="bmi-indicator" style="left: {pct}%;">▲</div>
    </div>
    """, unsafe_allow_html=True)


def _save_env_file(gemini_key: str, openai_key: str, provider: str):
    """Write API keys to .env file."""
    env_path = ROOT_DIR / ".env"
    lines = [
        f"LLM_PROVIDER={provider}\n",
    ]
    if gemini_key:
        lines.append(f"GEMINI_API_KEY={gemini_key}\n")
    if openai_key:
        lines.append(f"OPENAI_API_KEY={openai_key}\n")

    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception as e:
        st.error(f"Lỗi ghi file .env: {e}")


if __name__ == "__main__":
    main()
