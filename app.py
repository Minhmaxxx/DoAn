"""
app.py — NutriVision: Personalized Nutrition Advisory System
Main Streamlit entry point.

Run:
    streamlit run app.py
"""

from pathlib import Path

import streamlit as st

import config
from utils.auth import bootstrap_session, sync_status
from utils.state import initialize_session_state
from utils.navigation import render_app_shell
from utils.pwa import install_pwa_metadata, render_install_button
from utils.ui import render_stat_grid

# ─── Page configuration (MUST be first Streamlit call) ───────────────────────
st.set_page_config(
    page_title=config.APP_TITLE,
    page_icon="static/icons/icon-192.png",
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
    st.html(css_path)

initialize_session_state()

# Restore a signed-in identity (cookie) or finish a Google link (?code=) before
# any page runs, so pages see the right repository on their first render. A
# no-op for guests: it returns before constructing a Supabase client.
if bootstrap_session() and "meal_history_loaded" not in st.session_state:
    from utils.repository import hydrate_session

    try:
        hydrate_session()
        st.session_state.meal_history_loaded = True
    except Exception:
        st.session_state.sync_error = (
            "Không tải được dữ liệu đã lưu. Bạn vẫn dùng được app trong phiên này."
        )

# ─── Landing Page ─────────────────────────────────────────────────────────────

def main():
    with st.container(key="landing-layout"):
        copy, preview = st.columns([1.15, 0.85], gap="large")
        with copy:
            st.markdown(
                """
                <section class="landing-hero">
                    <p class="landing-eyebrow"><span></span> NHẬT KÝ DINH DƯỠNG CÓ AI HỖ TRỢ</p>
                    <h1>Nhìn món ăn.<br><em>Hiểu bữa ăn.</em></h1>
                    <p>Chụp một tấm ảnh, xác nhận món và khẩu phần, rồi theo dõi năng lượng theo đúng nhịp sống của bạn.</p>
                </section>
                """,
                unsafe_allow_html=True,
            )
            primary, secondary = st.columns(2)
            with primary:
                if st.button("Bắt đầu với hồ sơ", type="primary", width="stretch"):
                    st.switch_page("pages/3_Ho_so.py")
            with secondary:
                if st.button("Mở trang hôm nay", width="stretch"):
                    st.switch_page("pages/0_Hom_nay.py")
        with preview:
            st.markdown(
                """
                <div class="landing-preview">
                    <div class="preview-top"><span>BỮA TRƯA · 12:34</span><b>ĐÃ XÁC NHẬN</b></div>
                    <div class="preview-food"><i>01</i><div><strong>Cơm tấm</strong><small>1.0 phần · 750 kcal</small></div><span>86%</span></div>
                    <div class="preview-food"><i>02</i><div><strong>Gỏi cuốn</strong><small>0.5 phần · 90 kcal</small></div><span>79%</span></div>
                    <div class="preview-total"><span>TỔNG BỮA ĂN</span><strong>840 <small>kcal</small></strong></div>
                    <div class="preview-bars"><span style="--w:72%">CARB</span><span style="--w:54%">PROTEIN</span><span style="--w:38%">FAT</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    render_stat_grid(
        [
            ("NHẬN DIỆN", "12 món", "Món Việt phổ biến"),
            ("XÁC NHẬN", "HITL", "Bạn là người quyết định"),
            ("THEO DÕI", "7 ngày", "Calo và macro rõ ràng"),
        ]
    )

    st.markdown(
        """
        <div class="landing-process-head"><span>QUY TRÌNH</span><h2>Ba bước, không phỏng đoán.</h2></div>
        <div class="landing-steps">
            <article><span>01</span><strong>Thiết lập cơ thể</strong><p>Lưu hồ sơ để tính mục tiêu theo tuổi, thể trạng và vận động.</p></article>
            <article><span>02</span><strong>Chụp và xác nhận</strong><p>AI gợi ý món; bạn sửa nhãn, bỏ món sai và chỉnh khẩu phần.</p></article>
            <article><span>03</span><strong>Ghi lại ngày ăn</strong><p>Lưu bữa ăn, xem xu hướng và nhận tư vấn khi thực sự cần.</p></article>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="install-card"):
        st.markdown(
            """
            <div class="install-copy">
                <span>CÀI TRÊN THIẾT BỊ</span>
                <h3>NutriVision luôn ở màn hình chính.</h3>
                <p>Dùng như một web app độc lập trên Android, iPhone, iPad và desktop.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_install_button()

    st.caption(
        {
            "guest": "Dữ liệu hiện chỉ tồn tại trong phiên này và chưa đồng bộ giữa các thiết bị.",
            "anonymous": "Dữ liệu đã lưu trên máy chủ nhưng chỉ mở được từ thiết bị này — liên kết Google ở trang Hồ sơ để dùng máy khác.",
            "linked": "Dữ liệu đã đồng bộ; đăng nhập Google trên thiết bị khác để xem lại.",
        }[sync_status()]
    )


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
    install_pwa_metadata()
