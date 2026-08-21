"""Proof that user text never reaches the browser as markup.

Every page in this app authors raw HTML through `st.markdown(...,
unsafe_allow_html=True)` — the shell, the cards and the stat grids are all
hand-written. That is a deliberate design choice (Streamlit's stock widgets
cannot produce the layout), and it means the escaping is load-bearing rather
than incidental.

Two kinds of test live here, and they fail for different reasons:

  * The behaviour tests below run a real page with an attack payload in the
    data and assert the payload comes out inert. They prove the escaping
    works *today*, end to end, including anything Streamlit does to the
    string on the way out.

  * `test_every_interpolation_into_raw_html_is_escaped_or_numeric` reads the
    source and fails the moment someone adds an unescaped `{...}` inside an
    HTML block. It proves nothing about today's behaviour; it exists so the
    *next* interpolation cannot be added silently. Behaviour tests only cover
    the payloads someone thought to write down.

Why user text can reach these blocks at all: the profile's display name is a
free-text field, and since cloud sync landed, meal records are read back out
of Postgres — so `meal_type` and each food's `display_name` are whatever the
database holds, not necessarily what this version of the app wrote.
"""

import ast
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


ROOT_DIR = Path(__file__).resolve().parents[1]

# A payload that needs no <script> tag, so it survives sanitizers that only
# strip scripts, and that is unmistakable in the output either way.
PAYLOAD = '<img src=x onerror="alert(1)">'

# Files that author raw HTML. Kept explicit rather than globbed: a new file
# reaching for unsafe_allow_html should have to be added here on purpose.
HTML_AUTHORING_FILES = [
    ROOT_DIR / "app.py",
    ROOT_DIR / "pages" / "0_Hom_nay.py",
    ROOT_DIR / "pages" / "1_Phan_tich_anh.py",
    ROOT_DIR / "pages" / "3_Ho_so.py",
    ROOT_DIR / "pages" / "4_Danh_gia_mo_hinh.py",
    ROOT_DIR / "utils" / "navigation.py",
    ROOT_DIR / "utils" / "ui.py",
]

# Placeholders holding HTML that was assembled earlier in the same module.
# Each of these is built by a comprehension that escapes its own inputs, so
# escaping again here would double-encode the tags into visible text.
PREBUILT_HTML_NAMES = {
    "badges",     # pages/1_Phan_tich_anh.py, food badges
    "cards",      # utils/ui.py, stat grid
    "meta_html",  # utils/ui.py, optional page meta
    "description_html",  # utils/ui.py, optional section description
}


def _profile(**overrides) -> dict:
    profile = {
        "name": "Test",
        "age": 25,
        "gender": "Nam",
        "height_cm": 170.0,
        "weight_kg": 65.0,
        "activity_level": "Vận động nhẹ (1-3 ngày/tuần)",
        "goal": "Duy trì cân nặng",
    }
    profile.update(overrides)
    return profile


def _rendered_html(app: AppTest) -> str:
    return "\n".join(str(element.value) for element in app.markdown)


def test_a_display_name_containing_markup_is_shown_as_text():
    """The one free-text field in the app is the profile's display name.

    It is interpolated into the page heading on every page through
    render_page_header(), so a single missed escape there would be reflected
    on all of them.
    """
    app = AppTest.from_file(str(ROOT_DIR / "pages" / "0_Hom_nay.py"), default_timeout=45)
    app.session_state["user_profile"] = _profile(name=PAYLOAD)
    app.session_state["profile_completed"] = True
    app.run()

    assert not app.exception, [str(exception) for exception in app.exception]
    html = _rendered_html(app)
    # The value did reach the page — otherwise this test would pass for the
    # boring reason that nothing was rendered at all.
    assert "&lt;img src=x onerror=" in html
    assert PAYLOAD not in html


def test_a_meal_read_back_from_the_database_cannot_inject_markup():
    """Meal records are no longer authored solely by this app.

    Since sync landed, `foods[].display_name` and `meal_type` come out of
    Postgres. RLS means an attacker cannot write into another user's rows, so
    the realistic case is a value this app never wrote — an older client, a
    hand-edited row, a restored backup — rather than a stranger's payload.
    It still must not become markup.
    """
    app = AppTest.from_file(str(ROOT_DIR / "pages" / "0_Hom_nay.py"), default_timeout=45)
    app.session_state["user_profile"] = _profile()
    app.session_state["profile_completed"] = True

    from utils.history import vietnam_now

    now = vietnam_now()
    app.session_state["meal_history"] = [
        {
            "timestamp": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M"),
            "meal_type": PAYLOAD,
            "foods": [
                {
                    "emoji": "🥖",
                    "display_name": PAYLOAD,
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

    assert not app.exception, [str(exception) for exception in app.exception]
    html = _rendered_html(app)
    assert "&lt;img src=x onerror=" in html
    assert PAYLOAD not in html


def _numeric_format(spec: ast.FormattedValue) -> bool:
    """True when the placeholder is formatted as a number.

    `{x:.0f}` cannot emit a tag no matter what x holds — the format spec
    either produces digits or raises. That is a stronger guarantee than
    escaping, so those placeholders need no escape() call.
    """
    if spec.format_spec is None:
        return False
    text = "".join(
        node.value
        for node in ast.walk(spec.format_spec)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    )
    return text.endswith(("f", "d", "%", "e", "g"))


def _unsafe_placeholders(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    findings = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        raw_html = any(
            keyword.arg == "unsafe_allow_html"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is True
            for keyword in node.keywords
        )
        if not raw_html or not node.args:
            continue
        for placeholder in ast.walk(node.args[0]):
            if not isinstance(placeholder, ast.FormattedValue):
                continue
            expression = ast.get_source_segment(source, placeholder.value) or ""
            if "escape(" in expression:
                continue
            if _numeric_format(placeholder):
                continue
            if expression in PREBUILT_HTML_NAMES:
                continue
            findings.append(f"{path.name}:{placeholder.lineno}: {{{expression}}}")
    return findings


@pytest.mark.parametrize(
    "path", HTML_AUTHORING_FILES, ids=lambda path: path.stem
)
def test_every_interpolation_into_raw_html_is_escaped_or_numeric(path):
    """Fail on any new `{...}` inside an HTML block that is not neutralized.

    Three ways to satisfy this, in order of preference: format the value as a
    number, wrap it in html.escape(), or — only for HTML assembled elsewhere
    in the module — name it in PREBUILT_HTML_NAMES with a comment saying who
    escapes its inputs.

    The audit this locks in found no live hole: every placeholder carrying
    user text was already escaped. What it did find was several carrying
    values from config and utils.nutrition that were escaped by nobody,
    trusted only because today they happen to be constants written by us.
    That is a fact about the data, not about the code, and it is exactly the
    kind of assumption that stops being true quietly.
    """
    findings = _unsafe_placeholders(path)
    assert not findings, "unescaped interpolation into raw HTML:\n" + "\n".join(findings)
