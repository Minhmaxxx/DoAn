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

Three behaviours of that component are load-bearing and easy to get wrong:

- **It needs a round trip.** On the run where the component first renders it
  returns the default (`{}`); the real cookies arrive on the rerun Streamlit
  performs when the frontend answers. `cookies_ready()` distinguishes "no
  cookie" from "not answered yet", because treating the second as the first
  logs the user out on every page load.
- **SameSite must be Lax, not the component default of Strict.** Coming back
  from Google, the request is a cross-site navigation, and Strict cookies are
  withheld exactly then — which is the one moment the session cookie matters.
- **A write is only a request to write.** `manager.set()` renders an iframe;
  the cookie reaches the browser when that iframe's JS runs, which is after
  the script finishes. An `st.rerun()` in the same run tears the element tree
  down first, so the write never happens. Measured on the deployment: after
  "Bật đồng bộ" — which called `st.rerun()` immediately — the browser held no
  `nv_refresh_token`, so every reload fell back to guest and re-enabling sync
  kept minting duplicate accounts.

That last point is what the pending queue below exists for: a write is
recorded in session state and re-issued at the top of the next few runs until
the browser reports it back, so callers may `st.rerun()` freely.
"""

from __future__ import annotations

import datetime
from typing import Optional

import streamlit as st

MANAGER_STATE_KEY = "_cookie_manager"
_MANAGER_WIDGET_KEY = "nv_cookie_manager"

# What we believe the browser holds, including writes it hasn't confirmed yet.
# A value of None is a tombstone written by delete_cookie(), so a read later in
# the same session cannot resurrect a session the user just logged out of.
_OVERLAY_KEY = "_cookie_overlay"
# Writes/deletes still waiting for the browser to confirm them.
_PENDING_KEY = "_cookie_pending"
# Names that ran out of retries without ever being confirmed.
_UNCONFIRMED_KEY = "_cookie_unconfirmed"
# Sticky: once the component has answered, it stays answered. Otherwise a later
# empty answer would read as "not asked yet" and stall bootstrap forever.
_ANSWERED_KEY = "_cookie_component_answered"
# What has already been sent to the browser during THIS run: {name: (op, value)}.
# Reset by init_cookie_manager(), which runs exactly once per run.
_ISSUED_KEY = "_cookie_issued_this_run"
# Monotonic suffix for component keys, so no two component instances in one run
# collide and every instance has arguments Streamlit hasn't cached.
_SEQ_KEY = "_cookie_seq"

# How many further runs an unconfirmed write is re-issued for. One retry covers
# the plain st.rerun() case; three covers a click that reruns more than once.
_RETRY_RUNS = 3


def _session_dict(key: str) -> dict:
    store = st.session_state.get(key)
    if not isinstance(store, dict):
        store = {}
        st.session_state[key] = store
    return store


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
    if getattr(manager, "cookies", None):
        st.session_state[_ANSWERED_KEY] = True
    st.session_state[_ISSUED_KEY] = {}
    _replay_pending(manager)
    return manager


def _manager():
    return st.session_state.get(MANAGER_STATE_KEY)


def _snapshot() -> dict:
    """What the component last reported. Can be stale within a session."""
    manager = _manager()
    reported = getattr(manager, "cookies", None) if manager is not None else None
    return dict(reported) if reported else {}


def _replay_pending(manager) -> None:
    """Re-issue writes and deletes the browser hasn't confirmed yet.

    Runs at the top of every script run, before anything can `st.rerun()`
    away from it — that ordering is the entire point (see module docstring).
    """
    pending = _session_dict(_PENDING_KEY)
    if not pending:
        return
    reported = getattr(manager, "cookies", None) or {}

    for name in list(pending):
        entry = pending[name]
        if entry["op"] == "delete":
            confirmed = name not in reported
        else:
            confirmed = reported.get(name) == entry["value"]

        if confirmed or entry["runs_left"] <= 0:
            del pending[name]
            if not confirmed:
                # Out of retries and still unseen. Recorded so
                # cookie_diagnostics() can say so, instead of the session just
                # quietly evaporating on the next reload.
                _session_dict(_UNCONFIRMED_KEY)[name] = entry["op"]
            continue

        entry["runs_left"] -= 1
        if entry["op"] == "delete":
            _issue_delete(manager, name)
        else:
            _issue_set(manager, name, entry["value"], entry["max_age_days"])


def _next_seq() -> int:
    seq = st.session_state.get(_SEQ_KEY, 0) + 1
    st.session_state[_SEQ_KEY] = seq
    return seq


def _issue_set(manager, name: str, value: str, max_age_days: int) -> bool:
    _session_dict(_ISSUED_KEY)[name] = ("set", value)
    try:
        manager.set(
            name,
            value,
            # A fresh component key every time: two instances sharing a key in
            # one run is a duplicate-key error, and reusing one across runs
            # with unchanged args lets Streamlit serve the cached result
            # without the frontend doing anything — a silent no-op retry.
            key=f"cookie_set_{name}_{_next_seq()}",
            # Timezone-aware on purpose. CookieManager sends isoformat() to the
            # browser, and JS parses a naive timestamp as *local* time — on
            # Streamlit Cloud (UTC) that shifted every expiry by the viewer's
            # offset.
            expires_at=datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(days=max_age_days),
            path="/",
            secure=True,
            # Lax, never Strict: the OAuth return is a cross-site navigation.
            same_site="lax",
        )
        return True
    except Exception:
        return False


def _issue_delete(manager, name: str) -> None:
    _session_dict(_ISSUED_KEY)[name] = ("delete", None)
    try:
        manager.delete(name, key=f"cookie_del_{name}_{_next_seq()}")
    except KeyError:
        # CookieManager.delete() drops the name from its own snapshot and
        # raises when it wasn't there. The frontend call already went out, so
        # there is nothing to act on.
        pass
    except Exception:
        pass


def cookies_ready() -> bool:
    """True once the browser has actually answered with its cookies.

    False both before the component reports and when it isn't available at
    all. Callers must not conclude "the user has no session" while this is
    False — see the module docstring.
    """
    if st.session_state.get(_ANSWERED_KEY):
        return True
    manager = _manager()
    if manager is not None and getattr(manager, "cookies", None):
        st.session_state[_ANSWERED_KEY] = True
        return True
    return False


def all_cookies() -> dict:
    """Every cookie we believe the browser holds, unconfirmed writes included."""
    merged = _snapshot()
    for name, value in _session_dict(_OVERLAY_KEY).items():
        if value is None:
            merged.pop(name, None)
        else:
            merged[name] = value
    return merged


def read_cookie(name: str) -> Optional[str]:
    """Return one cookie's value, or None.

    Reads our own overlay before the component's snapshot. That snapshot is
    taken when the component answers and is not necessarily refreshed again
    within a session, so a cookie written a moment ago would otherwise read
    back as absent — and a deleted one as still present.

    Falls back to `st.context.cookies` last, because that path does work when
    running locally; keeping it means local development still behaves like
    production rather than silently taking a different branch.
    """
    overlay = _session_dict(_OVERLAY_KEY)
    if name in overlay:
        value = overlay[name]
        return value if isinstance(value, str) and value else None

    value = _snapshot().get(name)
    if isinstance(value, str) and value:
        return value

    try:
        value = st.context.cookies.get(name)
    except Exception:
        return None
    return value if isinstance(value, str) and value else None


def write_cookie(
    name: str, value: str, *, max_age_days: int, retry: bool = True
) -> bool:
    """Persist a cookie in the browser.

    Returns whether the write could be issued at all. Landing it in the
    browser may still take another run or two, which _replay_pending() drives.

    Pass `retry=False` for a value the app rewrites on every render anyway
    (the PKCE verifier). Retrying those is worse than useless: a replay would
    re-send the *previous* verifier alongside the fresh one written later in
    the same run, and whichever iframe ran last would decide whether the
    OAuth URL's code_challenge still matched.
    """
    _session_dict(_OVERLAY_KEY)[name] = value
    _session_dict(_UNCONFIRMED_KEY).pop(name, None)
    pending = _session_dict(_PENDING_KEY)
    if retry:
        pending[name] = {
            "op": "set",
            "value": value,
            "max_age_days": max_age_days,
            "runs_left": _RETRY_RUNS,
        }
    else:
        pending.pop(name, None)

    manager = _manager()
    if manager is None:
        return False
    if _session_dict(_ISSUED_KEY).get(name) == ("set", value):
        return True  # the replay at the top of this run already sent it
    return _issue_set(manager, name, value, max_age_days)


def delete_cookie(name: str) -> None:
    already_absent = read_cookie(name) is None  # before the tombstone below
    _session_dict(_OVERLAY_KEY)[name] = None
    _session_dict(_UNCONFIRMED_KEY).pop(name, None)

    if already_absent:
        # Nothing for the browser to remove. GoTrue calls remove_item() for
        # keys it never wrote — sign_in_with_oauth() clears its whole session
        # storage first — and queuing retries for those would render a delete
        # iframe on every run and then report them as writes the browser
        # refused.
        _session_dict(_PENDING_KEY).pop(name, None)
        return

    _session_dict(_PENDING_KEY)[name] = {
        "op": "delete",
        "value": None,
        "max_age_days": 0,
        "runs_left": _RETRY_RUNS,
    }
    manager = _manager()
    if manager is None:
        return
    if _session_dict(_ISSUED_KEY).get(name) == ("delete", None):
        return  # the replay at the top of this run already sent it
    _issue_delete(manager, name)


def pending_writes() -> dict:
    """Names still waiting for the browser to confirm, for diagnostics."""
    return {name: entry["op"] for name, entry in _session_dict(_PENDING_KEY).items()}


def unconfirmed_writes() -> dict:
    """Names the browser never confirmed after every retry, for diagnostics."""
    return dict(_session_dict(_UNCONFIRMED_KEY))
