"""Shared app shell rendered by the central Streamlit router."""

from __future__ import annotations

import streamlit as st


def render_app_shell(current_page, landing_page, user_pages) -> None:
    """Render one registered Streamlit navigation for desktop and mobile."""
    with st.container(horizontal=True, key="app-shell"):
        with st.container(key="app-brand"):
            st.page_link(
                landing_page,
                label="NutriVision",
                disabled=landing_page.url_path == current_page.url_path,
            )
        with st.container(horizontal=True, key="app-navigation"):
            for page in user_pages:
                st.page_link(
                    page,
                    label=page.title,
                    disabled=page.url_path == current_page.url_path,
                    width="stretch",
                )
