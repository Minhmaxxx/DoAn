"""Shared Streamlit session-state defaults."""

from __future__ import annotations

from copy import deepcopy

import streamlit as st


DEFAULT_USER_PROFILE = {
    "name": "",
    "age": 22,
    "gender": "Nam",
    "weight_kg": 65.0,
    "height_cm": 170.0,
    "activity_level": "Vừa phải (3-5 ngày/tuần)",
    "goal": "Giữ cân",
}


def initialize_session_state() -> None:
    """Create shared state and migrate profiles missing newly added fields."""
    profile = st.session_state.setdefault("user_profile", deepcopy(DEFAULT_USER_PROFILE))
    for key, value in DEFAULT_USER_PROFILE.items():
        profile.setdefault(key, value)

    st.session_state.setdefault("meal_history", [])
    st.session_state.setdefault("current_meal", None)
