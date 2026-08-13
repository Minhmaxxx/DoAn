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
from utils.state import initialize_session_state

# ─── Init session state ───────────────────────────────────────────────────────
initialize_session_state()


def main():
    if st.session_state.pop("clear_demo_credentials", False):
        st.session_state.pop("llm_runtime_config", None)
        st.session_state.demo_google_api_key = ""
        st.session_state.demo_openai_api_key = ""
        st.session_state.demo_llm_provider = (
            config.LLM_PROVIDER
            if config.LLM_PROVIDER in {"google", "openai"}
            else "openai"
        )

    st.markdown('<h1 class="page-title">Hồ sơ</h1>', unsafe_allow_html=True)
    st.caption("Dùng để tính mục tiêu dinh dưỡng cá nhân.")
    st.markdown("---")

    profile = st.session_state.user_profile
    col_form, col_results = st.columns([1, 1])

    # ── Form ───────────────────────────────────────────────────────────────
    with col_form:
        st.markdown("### Thông tin")

        with st.form("profile_form"):
            profile["name"] = st.text_input(
                "Tên hiển thị",
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

            st.markdown("Mức độ vận động")
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

            st.markdown("Mục tiêu")
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
                "Lưu thay đổi",
                type="primary",
                width="stretch",
            )
            if submitted:
                st.session_state.user_profile = profile
                st.success("Đã lưu.")
                st.rerun()

    # ── Results ────────────────────────────────────────────────────────────
    with col_results:
        st.markdown("### Mục tiêu của bạn")

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
            <div class="metric-label">BMI</div>
            <div class="metric-value" style="color: {bmi_color};">{bmi}</div>
            <div class="metric-unit">{bmi_cat}</div>
        </div>
        """, unsafe_allow_html=True)

        # BMI scale visual
        _render_bmi_scale(bmi)

        st.markdown("---")

        col_m1, col_m2 = st.columns(2)
        col_m1.metric(
            "BMR",
            f"{bmr:.0f} kcal/ngày",
            help="Năng lượng cơ thể cần để duy trì sự sống khi nghỉ ngơi hoàn toàn.",
        )
        col_m2.metric(
            "TDEE",
            f"{tdee:.0f} kcal/ngày",
            help="Tổng năng lượng cơ thể bạn đốt cháy mỗi ngày dựa trên mức vận động.",
        )

        st.markdown("---")
        st.markdown(f"Mục tiêu: **{profile['goal']}**")

        col_t1, col_t2 = st.columns(2)
        col_t1.metric(
            "Calo mỗi ngày",
            f"{goal_info['target_calories']:.0f} kcal",
            f"{goal_info['calorie_change']:+.0f} kcal vs TDEE",
        )
        col_t2.markdown(
            f"<div class='goal-desc'>{goal_info['description']}</div>",
            unsafe_allow_html=True,
        )

        st.markdown("---")
        st.markdown("Macro mỗi ngày")

        col_m, col_m2, col_m3 = st.columns(3)
        col_m.metric("Carb", f"{macro_targets['carbohydrate_g']:.0f}g")
        col_m2.metric("Protein", f"{macro_targets['protein_g']:.0f}g")
        col_m3.metric("Fat", f"{macro_targets['fat_g']:.0f}g")

        fig = macro_donut_chart(
            macro_targets["carbohydrate_g"],
            macro_targets["protein_g"],
            macro_targets["fat_g"],
            title=f"Phân bổ Macro — {profile['goal']}",
        )
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    # ── LLM API Config ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Trợ lý AI")
    assistant_enabled = st.toggle(
        "Dùng trợ lý AI",
        key="assistant_enabled",
        help="Khi tắt, NutriVision không gửi hồ sơ hoặc dữ liệu bữa ăn đến OpenAI/Google.",
    )
    if not assistant_enabled:
        st.session_state.llm_advice = None
        st.markdown(
            "<div class='assistant-status assistant-status-off'>"
            "<strong>Trợ lý đang tắt</strong><span>Ứng dụng không gửi dữ liệu đến AI.</span>"
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='assistant-status assistant-status-on'>"
            "<strong>Trợ lý đang bật</strong><span>Dữ liệu chỉ được gửi khi bạn nhấn nhận tư vấn.</span>"
            "</div>",
            unsafe_allow_html=True,
        )

    with st.expander("API key tạm thời", expanded=False):
        st.info(
            "Chỉ dùng trong phiên này và không ghi vào file."
        )
        st.warning(
            "Khi yêu cầu tư vấn, hồ sơ và bữa ăn hiện tại sẽ được gửi tới nhà cung cấp đã chọn."
        )
        col_k1, col_k2 = st.columns(2)
        openai_key = col_k1.text_input(
            "OpenAI API Key (tuỳ chọn)",
            type="password",
            placeholder="sk-...",
            key="demo_openai_api_key",
        )
        google_key = col_k2.text_input(
            "Google AI Studio API Key (tuỳ chọn)",
            type="password",
            placeholder="AIza...",
            help="Dùng cho model Gemini hoặc Gemma được AI Studio hỗ trợ.",
            key="demo_google_api_key",
        )

        runtime_config = st.session_state.get("llm_runtime_config", {})
        provider_options = ["openai", "google"]
        default_provider = runtime_config.get("provider", config.LLM_PROVIDER)
        llm_provider = st.selectbox(
            "Nhà cung cấp LLM",
            provider_options,
            index=provider_options.index(default_provider) if default_provider in provider_options else 0,
            format_func=lambda value: {
                "openai": "OpenAI",
                "google": "Google AI Studio (Gemini/Gemma)",
            }[value],
            key="demo_llm_provider",
        )

        if st.button("Dùng key cho phiên này", key="save_api"):
            st.session_state.llm_runtime_config = {
                "provider": llm_provider,
                "google_api_key": google_key.strip(),
                "openai_api_key": openai_key.strip(),
            }
            st.success("Đã cập nhật API key.")

        if st.button("Xóa API key", key="clear_api"):
            st.session_state.clear_demo_credentials = True
            st.rerun()

    # ── About project ──────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("Về ứng dụng"):
        st.markdown("""
       **NutriVision** là đồ án tốt nghiệp ngành Khoa học Máy tính.

        NutriVision nhận diện 12 món ăn Việt Nam, sau đó dùng khẩu phần bạn xác nhận để tính dinh dưỡng.

        Kết quả chỉ mang tính tham khảo, không thay thế tư vấn y tế.
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


if __name__ == "__main__":
    main()
