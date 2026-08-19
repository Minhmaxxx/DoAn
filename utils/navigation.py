"""Shared app shell rendered by the central Streamlit router."""

from __future__ import annotations

import streamlit as st

from utils.auth import sync_status


# Wording matters here: "anonymous" means stored server-side but reachable only
# from this browser, so it must not read as synced (STORAGE_PLAN.md section 4).
SYNC_NOTE = {
    "guest": "Dữ liệu hiện lưu trong phiên.",
    "anonymous": "Đã lưu trên máy chủ, chỉ thiết bị này.",
    "linked": "Đã đồng bộ giữa các thiết bị.",
}

NAV_ICONS = {
    "Hôm nay": ":material/home:",
    "Phân tích": ":material/photo_camera:",
    "Lịch sử": ":material/calendar_month:",
    "Hồ sơ": ":material/person:",
}


def render_app_shell(current_page, landing_page, user_pages) -> None:
    """Render a desktop rail that becomes mobile top/bottom navigation."""
    with st.container(horizontal=True, key="app-mobile-header"):
        st.page_link(
            landing_page,
            label="NutriVision",
            icon=":material/restaurant:",
        )
        st.markdown("<span class='mobile-live'>BẢN DEMO</span>", unsafe_allow_html=True)

    with st.container(key="app-shell"):
        with st.container(key="app-brand"):
            st.page_link(
                landing_page,
                label="NutriVision",
                icon=":material/restaurant:",
            )
            st.caption("Bữa ăn rõ ràng hơn, mỗi ngày.")

        st.markdown("<p class='nav-label'>KHÔNG GIAN CỦA BẠN</p>", unsafe_allow_html=True)
        with st.container(horizontal=True, key="app-navigation"):
            for page in user_pages:
                active = page.url_path == current_page.url_path
                key = f"nav-active-{page.url_path}" if active else f"nav-{page.url_path}"
                with st.container(key=key):
                    st.page_link(
                        page,
                        label=page.title,
                        icon=NAV_ICONS[page.title],
                        width="stretch",
                    )

        st.markdown(
            f"""
            <div class="rail-note">
                <span>12 món Việt</span>
                <strong>YOLO + HITL</strong>
                <small>{SYNC_NOTE[sync_status()]}</small>
            </div>
            """,
            unsafe_allow_html=True,
        )
