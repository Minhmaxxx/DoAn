"""Small authored UI primitives shared by Streamlit pages."""

from __future__ import annotations

from html import escape

import streamlit as st


def render_page_header(
    eyebrow: str,
    title: str,
    description: str,
    *,
    meta: str | None = None,
) -> None:
    """Render a consistent editorial page heading."""
    meta_html = f'<span class="page-meta">{escape(meta)}</span>' if meta else ""
    st.markdown(
        f"""
        <header class="page-head">
            <div class="page-head-row">
                <p class="page-eyebrow">{escape(eyebrow)}</p>
                {meta_html}
            </div>
            <h1 class="page-title">{escape(title)}</h1>
            <p class="page-description">{escape(description)}</p>
        </header>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(index: str, title: str, description: str = "") -> None:
    """Render a numbered section heading for task-oriented pages."""
    description_html = (
        f'<p class="section-description">{escape(description)}</p>'
        if description
        else ""
    )
    st.markdown(
        f"""
        <div class="section-head">
            <span class="section-index">{escape(index)}</span>
            <div>
                <h2>{escape(title)}</h2>
                {description_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stat_grid(items: list[tuple[str, str, str]]) -> None:
    """Render compact metrics without relying on Streamlit's column DOM."""
    cards = "".join(
        (
            '<div class="stat-card">'
            f'<span class="stat-label">{escape(label)}</span>'
            f'<strong class="stat-value">{escape(value)}</strong>'
            f'<small class="stat-note">{escape(note)}</small>'
            "</div>"
        )
        for label, value, note in items
    )
    st.markdown(f'<div class="stat-grid">{cards}</div>', unsafe_allow_html=True)


def render_empty_state(title: str, description: str, code: str = "00") -> None:
    """Render a quiet empty state that still feels intentional."""
    st.markdown(
        f"""
        <div class="empty-state">
            <span>{escape(code)}</span>
            <div>
                <strong>{escape(title)}</strong>
                <p>{escape(description)}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
