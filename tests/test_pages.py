"""Streamlit render smoke tests and responsive-style contracts."""

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


ROOT_DIR = Path(__file__).resolve().parents[1]
APP_FILES = [
    ROOT_DIR / "app.py",
    ROOT_DIR / "pages" / "0_Hom_nay.py",
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


def test_responsive_css_has_distinct_desktop_and_mobile_shells():
    css = (ROOT_DIR / "assets" / "style.css").read_text(encoding="utf-8")
    assert "@media (max-width: 1200px)" in css
    assert "@media (max-width: 520px)" in css
    assert 'header[data-testid="stHeader"]' in css
    assert '[data-testid="stDataFrame"]' in css
    assert '[data-testid="stTabs"] [role="tablist"]' in css
    assert '[data-testid="stRadio"] [role="radiogroup"]' in css
    assert "min-height: 48px" in css
    assert "env(safe-area-inset-bottom)" in css
    navigation = (ROOT_DIR / "utils" / "navigation.py").read_text(encoding="utf-8")
    assert "render_app_shell" in navigation
    assert "st.page_link" in navigation
    assert ".st-key-app-shell" in css
    assert ".st-key-app-mobile-header" in css
    assert '.st-key-app-navigation[data-testid="stHorizontalBlock"]' in css
    assert "flex-wrap: nowrap !important" in css
    assert ":focus-visible" in css
    assert 'class*="st-key-nav-active-"' in css
    assert '[data-testid="stExpandSidebarButton"]' in css
    assert '[data-testid="stSidebar"]' in css


def test_pwa_manifest_icons_and_static_serving_contract():
    manifest = json.loads(
        (ROOT_DIR / "static" / "manifest.webmanifest").read_text(encoding="utf-8")
    )
    assert manifest["display"] == "standalone"
    assert manifest["start_url"] == "/"
    assert {icon["sizes"] for icon in manifest["icons"]} == {"192x192", "512x512"}
    assert (ROOT_DIR / "static" / "icons" / "icon-192.png").is_file()
    assert (ROOT_DIR / "static" / "icons" / "icon-512.png").is_file()
    assert (ROOT_DIR / "static" / "icons" / "apple-touch-icon.png").is_file()
    assert "enableStaticServing = true" in (
        ROOT_DIR / ".streamlit" / "config.toml"
    ).read_text(encoding="utf-8")
    pwa_source = (ROOT_DIR / "utils" / "pwa.py").read_text(encoding="utf-8")
    assert "beforeinstallprompt" in pwa_source
    assert "apple-mobile-web-app-capable" in pwa_source
    assert "components.html" not in pwa_source
    assert "st.html(" in pwa_source
    assert "st.iframe(" in pwa_source
    assert "aria-current" in pwa_source
    assert "tab_index=-1" not in pwa_source
    assert 'scope: "/app/static/"' in pwa_source
    worker_source = (ROOT_DIR / "static" / "service-worker.js").read_text(
        encoding="utf-8"
    )
    assert 'startsWith("nutrivision-shell-")' in worker_source


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
        button for button in app.button if "Xóa tất cả" in button.label
    )
    clear_button.click().run()
    assert app.session_state["meal_history"] == []
    assert not app.exception


def test_temporary_openai_key_can_be_saved_and_cleared_from_session():
    app = AppTest.from_file(
        str(ROOT_DIR / "pages" / "3_Ho_so.py"), default_timeout=45
    )
    app.run()
    openai_key = next(
        field for field in app.text_input if field.label == "OpenAI API Key (tuỳ chọn)"
    )
    save_button = next(
        button for button in app.button if "Dùng key cho phiên này" in button.label
    )
    openai_key.input("session-test-key")
    save_button.click().run()
    assert app.session_state["llm_runtime_config"]["openai_api_key"] == "session-test-key"

    clear_button = next(
        button for button in app.button if "Xóa API key" in button.label
    )
    clear_button.click().run()
    assert "llm_runtime_config" not in app.session_state.filtered_state
    assert app.session_state["demo_google_api_key"] == ""
    assert app.session_state["demo_openai_api_key"] == ""
    assert not app.exception


def test_assistant_can_be_disabled_for_the_active_session():
    app = AppTest.from_file(
        str(ROOT_DIR / "pages" / "3_Ho_so.py"), default_timeout=45
    )
    app.run()
    assistant_toggle = next(
        toggle for toggle in app.toggle if toggle.label == "Dùng trợ lý AI"
    )
    assistant_toggle.set_value(False).run()
    assert app.session_state["assistant_enabled"] is False
    assert not app.exception


def test_profile_is_completed_only_after_form_submission():
    app = AppTest.from_file(
        str(ROOT_DIR / "pages" / "3_Ho_so.py"), default_timeout=45
    )
    app.run()
    assert app.session_state["profile_completed"] is False

    save_button = next(
        button for button in app.button if button.label == "Lưu thay đổi"
    )
    save_button.click().run()
    assert app.session_state["profile_completed"] is True
    assert any("Đã lưu hồ sơ" in success.value for success in app.success)
    assert not app.exception


@pytest.mark.parametrize("app_file", APP_FILES, ids=lambda path: path.stem)
def test_guest_mode_never_constructs_a_supabase_client(app_file):
    """The release gate must stay offline. Guest mode is what keeps it that
    way, so no page may build a Supabase client just by rendering.

    This caught a real regression: under AppTest, st.context.cookies.get()
    returns a truthy MagicMock, so bootstrap_session() believed it held a
    refresh token and built a client (and on a dev machine with real secrets
    would have tried to refresh with the mock over the network).
    """
    app = AppTest.from_file(str(app_file), default_timeout=45)
    app.run()
    assert not app.exception, [str(exception) for exception in app.exception]
    assert "_supabase_client" not in app.session_state.filtered_state
    assert app.session_state.filtered_state.get("auth_user") is None
