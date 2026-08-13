"""
app.py — NutriVision: Personalized Nutrition Advisory System
Main Streamlit entry point.

Run:
    streamlit run app.py
"""

import hashlib
import json
from pathlib import Path

import streamlit as st

import config
from utils.state import initialize_session_state
from utils.navigation import render_app_shell

# ─── Page configuration (MUST be first Streamlit call) ───────────────────────
st.set_page_config(
    page_title=config.APP_TITLE,
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "Get help": "https://github.com/Minhmaxxx/DoAn",
        "About": "## NutriVision\nYOLOv8n Baseline B · 12 lớp · HITL · LLM"
    }
)

# ─── Load custom CSS ──────────────────────────────────────────────────────────
css_path = Path(__file__).parent / "assets" / "style.css"
if css_path.exists():
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

initialize_session_state()

# ─── Landing Page ─────────────────────────────────────────────────────────────

def main():
    st.markdown(
        """
        <section class="landing-hero">
            <p class="landing-eyebrow">DINH DƯỠNG THEO BỮA ĂN THỰC TẾ</p>
            <h1>Ăn gì hôm nay, hiểu rõ hôm đó.</h1>
            <p>NutriVision nhận diện món ăn, để bạn tự xác nhận khẩu phần và theo dõi kết quả theo hồ sơ cá nhân.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    primary, secondary = st.columns(2)
    with primary:
        if st.button("Thiết lập hồ sơ", type="primary", width="stretch"):
            st.switch_page("pages/3_Ho_so.py")
    with secondary:
        if st.button("Mở không gian của tôi", width="stretch"):
            st.switch_page("pages/0_Hom_nay.py")

    st.markdown("### Cách bắt đầu")
    st.markdown(
        "<div class='landing-steps'>"
        "<div><span>01</span><strong>Điền hồ sơ</strong><p>Xác định mục tiêu calo phù hợp.</p></div>"
        "<div><span>02</span><strong>Phân tích bữa ăn</strong><p>Chụp ảnh và điều chỉnh khẩu phần.</p></div>"
        "<div><span>03</span><strong>Theo dõi hôm nay</strong><p>Lưu bữa ăn, xem tổng quan hoặc hỏi AI.</p></div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.caption("Dữ liệu hiện chỉ tồn tại trong phiên này. Kết nối bằng khóa cá nhân sẽ được bổ sung khi có hệ thống tài khoản.")


def _show_system_status():
    """Show current system configuration status."""
    col1, col2, col3 = st.columns(3)

    with col1:
        if config.MODEL_PATH.exists():
            digest = hashlib.sha256(config.MODEL_PATH.read_bytes()).hexdigest()
            if digest == config.MODEL_SHA256:
                st.success("Mô hình sẵn sàng")
            else:
                st.error("Checkpoint tồn tại nhưng checksum không hợp lệ")
        else:
            st.error(f"Thiếu checkpoint: {config.MODEL_PATH.name}")

    with col2:
        runtime_config = st.session_state.get("llm_runtime_config", {})
        provider = runtime_config.get("provider", config.LLM_PROVIDER)
        runtime_key = runtime_config.get(f"{provider}_api_key", "").strip()
        environment_key = config.GEMINI_API_KEY if provider == "google" else config.OPENAI_API_KEY
        has_key = bool(runtime_key or environment_key)
        if not st.session_state.assistant_enabled:
            st.info("Trợ lý AI đang tắt")
        elif provider not in {"google", "openai"}:
            st.error(f"LLM_PROVIDER không hợp lệ: {provider}")
        elif has_key and provider == "google":
            st.success("Trợ lý Google sẵn sàng")
        elif has_key:
            st.success("Trợ lý OpenAI sẵn sàng")
        else:
            st.info("Chưa có API key")

    with col3:
        try:
            with config.NUTRITION_DB_PATH.open(encoding="utf-8") as file:
                food_count = len(json.load(file)["foods"])
            if food_count == len(config.FOOD_CLASSES):
                st.success(f"Dữ liệu {food_count} món sẵn sàng")
            else:
                st.error(f"Dinh dưỡng mới có {food_count}/{len(config.FOOD_CLASSES)} món")
        except (OSError, KeyError, json.JSONDecodeError) as error:
            st.error(f"Lỗi nutrition DB: {error}")


if __name__ == "__main__":
    landing_page = st.Page(main, title="Giới thiệu", url_path="", default=True)
    today_page = st.Page(
        "pages/0_Hom_nay.py",
        title="Hôm nay",
        url_path="hom-nay",
    )
    analysis_page = st.Page(
        "pages/1_Phan_tich_anh.py",
        title="Phân tích",
        url_path="phan-tich",
    )
    history_page = st.Page(
        "pages/2_Lich_su.py",
        title="Lịch sử",
        url_path="lich-su",
    )
    profile_page = st.Page(
        "pages/3_Ho_so.py",
        title="Hồ sơ",
        url_path="ho-so",
    )
    evaluation_page = st.Page(
        "pages/4_Danh_gia_mo_hinh.py",
        title="Đánh giá mô hình",
        url_path="danh-gia",
        visibility="hidden",
    )
    primary_pages = [today_page, analysis_page, history_page, profile_page]
    current_page = st.navigation(
        [landing_page, *primary_pages, evaluation_page],
        position="hidden",
    )
    render_app_shell(current_page, landing_page, primary_pages)
    current_page.run()
