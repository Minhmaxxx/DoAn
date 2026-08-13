"""Streamlit render smoke tests and responsive-style contracts."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


ROOT_DIR = Path(__file__).resolve().parents[1]
APP_FILES = [
    ROOT_DIR / "app.py",
    ROOT_DIR / "pages" / "1_Phan_tich_anh.py",
    ROOT_DIR / "pages" / "2_Lich_su.py",
    ROOT_DIR / "pages" / "3_Ho_so.py",
    ROOT_DIR / "pages" / "4_Danh_gia_mo_hinh.py",
]


@pytest.mark.parametrize("app_file", APP_FILES, ids=lambda path: path.stem)
def test_streamlit_page_renders_without_exception(app_file):
    app = AppTest.from_file(str(app_file), default_timeout=45)
    app.run()
    assert not app.exception, [str(exception) for exception in app.exception]


def test_responsive_css_keeps_mobile_navigation_and_overflow_guards():
    css = (ROOT_DIR / "assets" / "style.css").read_text(encoding="utf-8")
    assert "@media (max-width: 768px)" in css
    assert "@media (max-width: 480px)" in css
    assert 'header[data-testid="stHeader"]' in css
    assert '[data-testid="stDataFrame"]' in css
    assert '[data-baseweb="tab-list"]' in css
    assert '[data-testid="stRadio"] [role="radiogroup"]' in css


def test_history_clear_only_changes_active_session():
    app = AppTest.from_file(
        str(ROOT_DIR / "pages" / "2_Lich_su.py"), default_timeout=45
    )
    app.session_state["meal_history"] = [
        {
            "timestamp": "2026-08-09T12:00:00",
            "date": "2026-08-09",
            "time": "12:00",
            "meal_type": "Bữa trưa",
            "foods": [
                {
                    "emoji": "🥖",
                    "display_name": "Bánh mì",
                    "portion_multiplier": 1.0,
                }
            ],
            "totals": {
                "calories": 380,
                "carbohydrate_g": 48,
                "protein_g": 18,
                "fat_g": 14,
            },
        }
    ]
    app.run()
    clear_button = next(
        button for button in app.button if "Xóa tất cả lịch sử" in button.label
    )
    clear_button.click().run()
    assert app.session_state["meal_history"] == []
    assert not app.exception


def test_temporary_google_key_can_be_saved_and_cleared_from_session():
    app = AppTest.from_file(
        str(ROOT_DIR / "pages" / "3_Ho_so.py"), default_timeout=45
    )
    app.run()
    google_key = next(
        field for field in app.text_input if field.label == "Google AI Studio API Key"
    )
    save_button = next(
        button for button in app.button if "Dùng API Key trong phiên demo" in button.label
    )
    google_key.input("session-test-key")
    save_button.click().run()
    assert app.session_state["llm_runtime_config"]["google_api_key"] == "session-test-key"

    clear_button = next(
        button for button in app.button if "Xóa API Key khỏi phiên demo" in button.label
    )
    clear_button.click().run()
    assert "llm_runtime_config" not in app.session_state.filtered_state
    assert app.session_state["demo_google_api_key"] == ""
    assert app.session_state["demo_openai_api_key"] == ""
    assert not app.exception
