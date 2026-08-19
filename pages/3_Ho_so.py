"""
pages/3_Ho_so.py — User Profile & Biometric Setup
Collects user's biometric data and computes health metrics (BMI, BMR, TDEE).
"""

import json
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
from utils.pwa import render_install_button
from utils.state import initialize_session_state
from utils.ui import render_page_header, render_section_header
from utils import auth
from utils.repository import enable_sync, get_repository

# ─── Init session state ───────────────────────────────────────────────────────
initialize_session_state()

# The three states from STORAGE_PLAN.md section 4. "anonymous" must never be
# labelled as synced: the data is on the server but reachable only from this
# browser's cookie.
SYNC_META = {
    "guest": "LƯU TRONG PHIÊN",
    "anonymous": "LƯU TRÊN MÁY CHỦ",
    "linked": "ĐÃ ĐỒNG BỘ",
}


def main():
    profile_saved = st.session_state.pop("profile_saved", False)

    if st.session_state.pop("clear_demo_credentials", False):
        st.session_state.pop("llm_runtime_config", None)
        st.session_state.demo_google_api_key = ""
        st.session_state.demo_openai_api_key = ""
        st.session_state.demo_llm_provider = (
            config.LLM_PROVIDER
            if config.LLM_PROVIDER in {"google", "openai"}
            else "openai"
        )

    status = auth.sync_status()
    render_page_header(
        "THÔNG TIN CƠ THỂ",
        "Hồ sơ của bạn.",
        "Các chỉ số này giúp ước tính nhu cầu năng lượng; kết quả chỉ mang tính tham khảo.",
        meta=SYNC_META[status],
    )
    if profile_saved:
        st.success("Đã lưu hồ sơ.")

    sync_error = st.session_state.pop("sync_error", None)
    if sync_error:
        st.warning(sync_error)

    profile = st.session_state.user_profile
    with st.container(key="profile-layout"):
        col_form, col_results = st.columns([0.9, 1.1], gap="large")

    # ── Form ───────────────────────────────────────────────────────────────
    with col_form:
        st.markdown("<p class='panel-kicker'>01 · THÔNG TIN ĐẦU VÀO</p>", unsafe_allow_html=True)

        with st.form("profile_form"):
            name = st.text_input(
                "Tên hiển thị",
                value=profile.get("name", ""),
                placeholder="Nguyễn Văn A",
            )

            col_g, col_a = st.columns(2)
            gender = col_g.selectbox(
                "Giới tính",
                ["Nam", "Nữ"],
                index=0 if profile.get("gender", "Nam") == "Nam" else 1,
            )
            age = col_a.number_input(
                "Tuổi",
                min_value=10, max_value=100,
                value=profile.get("age", 22),
            )

            col_h, col_w = st.columns(2)
            height_cm = col_h.number_input(
                "Chiều cao (cm)",
                min_value=100.0, max_value=250.0,
                value=float(profile.get("height_cm", 170.0)),
                step=0.5,
                format="%.1f",
            )
            weight_kg = col_w.number_input(
                "Cân nặng (kg)",
                min_value=30.0, max_value=300.0,
                value=float(profile.get("weight_kg", 65.0)),
                step=0.5,
                format="%.1f",
            )

            st.markdown("Mức độ vận động")
            activity_level = st.select_slider(
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
            goal_options = ["Giảm cân", "Giữ cân", "Tăng cơ", "Tăng cân"]
            goal = st.radio(
                "Mục tiêu",
                goal_options,
                index=goal_options.index(profile.get("goal", "Giữ cân")),
                horizontal=True,
                label_visibility="collapsed",
            )

            submitted = st.form_submit_button(
                "Lưu thay đổi",
                type="primary",
                width="stretch",
            )
            if submitted:
                new_profile = {
                    "name": name.strip(),
                    "age": age,
                    "gender": gender,
                    "weight_kg": weight_kg,
                    "height_cm": height_cm,
                    "activity_level": activity_level,
                    "goal": goal,
                }
                try:
                    get_repository().save_profile(new_profile)
                except Exception as error:
                    # Never claim "Đã lưu hồ sơ" when the server refused it —
                    # keep the edit on screen so the user can retry.
                    st.error(f"Không lưu được hồ sơ lên máy chủ: {error}")
                else:
                    # SessionRepository stores into session state directly, but
                    # SupabaseRepository only writes the database — refresh the
                    # session copy here so both backends leave the same on-screen
                    # state after a save.
                    st.session_state.user_profile = new_profile
                    st.session_state.profile_completed = True
                    st.session_state.llm_advice = None
                    st.session_state.profile_saved = True
                    st.rerun()

    # ── Results ────────────────────────────────────────────────────────────
    with col_results:
        st.markdown("<p class='panel-kicker'>02 · CHỈ SỐ THAM KHẢO</p>", unsafe_allow_html=True)

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

        st.markdown(f"**Mục tiêu hiện tại:** {profile['goal']}")

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

        st.markdown("**Macro mỗi ngày**")

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

    # ── Cloud sync ─────────────────────────────────────────────────────────
    render_section_header(
        "03",
        "Đồng bộ và thiết bị",
        "Mặc định dữ liệu chỉ nằm trong phiên này. Bạn chọn khi nào đưa lên máy chủ.",
    )
    _render_sync_section(status)

    # ── LLM API Config ─────────────────────────────────────────────────────
    render_section_header(
        "04",
        "Quyền riêng tư và trợ lý AI",
        "Bạn quyết định khi nào dữ liệu hồ sơ và bữa ăn được gửi tới nhà cung cấp AI.",
    )
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
    render_section_header(
        "05",
        "Cài trên thiết bị",
        "Thêm NutriVision lên màn hình chính để mở như một ứng dụng độc lập.",
    )
    with st.container(key="profile-install"):
        render_install_button()

    with st.expander("Về ứng dụng"):
        st.markdown("""
       **NutriVision** là đồ án tốt nghiệp ngành Khoa học Máy tính.

        NutriVision nhận diện 12 món ăn Việt Nam, sau đó dùng khẩu phần bạn xác nhận để tính dinh dưỡng.

        Kết quả chỉ mang tính tham khảo, không thay thế tư vấn y tế.
        """)


def _render_google_signin_button():
    """Sign in with Google to recover an account created on another device.

    Two-step on purpose: the OAuth URL is only built after a click, never
    during a plain render, so a guest visiting this page still constructs no
    Supabase client (tests/test_pages.py enforces that). Both a redirect and
    a visible link are offered because the redirect runs in the parent
    document and can be blocked.
    """
    if st.button("Đăng nhập bằng Google", key="google_signin"):
        try:
            st.session_state.google_signin_url = auth.start_google_signin(
                auth.get_client().auth, auth.site_url()
            )
        except Exception as error:
            st.error(f"Không tạo được liên kết đăng nhập: {error}")

    url = st.session_state.get("google_signin_url")
    if url:
        st.link_button("Tiếp tục tới Google", url, type="primary", width="stretch")
        st.caption("Nếu trang không tự chuyển, bấm nút trên.")
        st.html(
            f"<script>window.parent.location.href = {json.dumps(url)};</script>",
            unsafe_allow_javascript=True,
        )


def _render_sync_section(status: str):
    """Render the guest / anonymous / linked controls for cloud sync."""
    if status == "guest":
        blocker = auth.sync_blocker()
        if blocker:
            st.info(
                "Bản triển khai này chưa bật đồng bộ, nên dữ liệu chỉ tồn tại "
                "trong phiên và sẽ mất khi đóng trình duyệt."
            )
            st.caption(f"Lý do: {blocker}")
            return
        col_new, col_back = st.columns(2)
        with col_new:
            st.markdown("**Chưa có dữ liệu trên máy chủ**")
            st.caption(
                "Lưu hồ sơ và lịch sử hiện có lên tài khoản mới. "
                "Không cần đăng ký hay mật khẩu."
            )
            if st.button("Bật đồng bộ", type="primary", key="enable_sync"):
                try:
                    enable_sync()
                except Exception as error:
                    st.error(f"Không bật được đồng bộ: {error}")
                else:
                    st.rerun()
        with col_back:
            st.markdown("**Đã có tài khoản Google**")
            st.caption(
                "Dùng khi bạn đã liên kết Google ở thiết bị khác và muốn lấy lại "
                "dữ liệu cũ. Dữ liệu chưa lưu trong phiên này sẽ bị thay thế."
            )
            _render_google_signin_button()
        return

    if status == "anonymous":
        st.success("Dữ liệu đã được lưu trên máy chủ.")
        st.warning(
            "Hiện chỉ **trình duyệt này** mở được dữ liệu đó. Xóa cookie hoặc đổi "
            "thiết bị là mất. Liên kết Google để dùng trên máy khác."
        )
        st.caption(
            "Nếu tài khoản Google này đã liên kết ở thiết bị khác, hãy **Đăng xuất** "
            "rồi chọn *Đăng nhập bằng Google* — liên kết lần hai sẽ báo lỗi và "
            "không lấy được dữ liệu cũ."
        )
    else:
        st.success("Đã liên kết Google — đăng nhập trên thiết bị khác để xem dữ liệu.")

    col_link, col_out = st.columns(2)
    with col_link:
        if status == "anonymous":
            try:
                url = auth.start_google_link(
                    auth.get_client().auth, auth.site_url()
                )
            except Exception as error:
                st.error(f"Không tạo được liên kết Google: {error}")
            else:
                st.link_button("Liên kết Google", url, width="stretch")
    with col_out:
        if st.button("Đăng xuất", width="stretch", key="logout"):
            try:
                client_auth = auth.get_client().auth
            except Exception:
                client_auth = None  # logout must work even if Supabase is down
            auth.logout(client_auth)
            st.session_state.pop("meal_history_loaded", None)
            st.rerun()


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
