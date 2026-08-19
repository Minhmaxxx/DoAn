"""Browser cookies that survive Streamlit Community Cloud.

Why this module exists at all: `st.context.cookies` is read-only *and*, on
Streamlit Community Cloud, always empty — the platform does not forward
request cookies to the app, so a deployment saw zero cookies even when the
browser demonstrably held them (see PROGRESS.md 2026-08-19). Writing cookies
from JS via `st.html` worked, but nothing could ever read them back, which
silently broke every persisted session.

A Streamlit component sidesteps that entirely: it reads `document.cookie` in
the browser and returns the values over the component channel, never through
an HTTP header, so nothing can strip them in transit.

Two behaviours of that component are load-bearing and easy to get wrong:

- **It needs a round trip.** On the run where the component first renders it
  returns the default (`{}`); the real cookies arrive on the rerun Streamlit
  performs when the frontend answers. `cookies_ready()` distinguishes "no
  cookie" from "not answered yet", because treating the second as the first
  logs the user out on every page load.
- **SameSite must be Lax, not the component default of Strict.** Coming back
  from Google, the request is a cross-site navigation, and Strict cookies are
  withheld exactly then — which is the one moment the session cookie matters.
"""

from __future__ import annotations

import datetime
from typing import Optional

import streamlit as st

MANAGER_STATE_KEY = "_cookie_manager"
_MANAGER_WIDGET_KEY = "nv_cookie_manager"


def init_cookie_manager():
    """Render the cookie component. Call once per script run, before reading.

    app.py calls this ahead of every page, so the component is re-rendered on
    each run and the channel stays alive. Returns None when the component
    can't be created (it isn't installed, or we're under AppTest), which keeps
    guest mode working instead of taking the app down.
    """
    try:
        import extra_streamlit_components as stx
    except ImportError:
        return None

    try:
        manager = stx.CookieManager(key=_MANAGER_WIDGET_KEY)
    except Exception:
        # A duplicate-key collision or a component failure must not be fatal:
        # the app is fully usable as a guest without cookies.
        return st.session_state.get(MANAGER_STATE_KEY)

    st.session_state[MANAGER_STATE_KEY] = manager
    return manager


def _manager():
    return st.session_state.get(MANAGER_STATE_KEY)


def cookies_ready() -> bool:
    """True once the browser has actually answered with its cookies.

    False both before the component reports and when it isn't available at
    all. Callers must not conclude "the user has no session" while this is
    False — see the module docstring.
    """
    manager = _manager()
    return bool(manager is not None and manager.cookies)


def all_cookies() -> dict:
    """Every cookie the browser reported, or {} if it hasn't answered yet."""
    manager = _manager()
    if manager is None or not manager.cookies:
        return {}
    return dict(manager.cookies)


def read_cookie(name: str) -> Optional[str]:
    """Return one cookie's value, or None.

    Falls back to `st.context.cookies` when the component reported nothing:
    that path does work when running locally, and keeping it means local
    development still behaves like production rather than silently taking a
    different branch.
    """
    manager = _manager()
    if manager is not None and manager.cookies:
        value = manager.cookies.get(name)
        if isinstance(value, str) and value:
            return value

    try:
        value = st.context.cookies.get(name)
    except Exception:
        return None
    return value if isinstance(value, str) and value else None


def write_cookie(name: str, value: str, *, max_age_days: int) -> bool:
    """Persist a cookie in the browser. Returns False if that isn't possible."""
    manager = _manager()
    if manager is None:
        return False
    try:
        manager.set(
            name,
            value,
            key=f"cookie_set_{name}",
            expires_at=datetime.datetime.now() + datetime.timedelta(days=max_age_days),
            path="/",
            secure=True,
            # Lax, never Strict: the OAuth return is a cross-site navigation.
            same_site="lax",
        )
        return True
    except Exception:
        return False


def delete_cookie(name: str) -> None:
    manager = _manager()
    if manager is None:
        return
    try:
        manager.delete(name, key=f"cookie_del_{name}")
    except Exception:
        pass
