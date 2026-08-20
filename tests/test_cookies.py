"""Cookie transport tests — the retry queue, not the browser.

These exist because of a bug that cost real user data: `manager.set()` only
renders an iframe, so a cookie write followed by `st.rerun()` in the same run
never reached the browser. On the deployment that meant "Bật đồng bộ" saved a
profile to a brand-new anonymous account, dropped the refresh-token cookie,
and minted another new account on the next visit — duplicate rows in
`profiles`, and a reload that always fell back to guest.

The fake CookieManager below mirrors the two properties of the real one that
made the bug possible: `.cookies` is a snapshot from when the frontend last
answered (so a fresh write is not visible in it), and `.set()` is a request
the frontend may never carry out.
"""

import sys
from types import SimpleNamespace

import pytest

import utils.cookies as cookies


class FakeSessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None

    def __setattr__(self, name, value):
        self[name] = value


class FakeStreamlit:
    def __init__(self, context_cookies=None):
        self.session_state = FakeSessionState()
        self.context = SimpleNamespace(cookies=dict(context_cookies or {}))


class FakeCookieManager:
    """Stands in for extra_streamlit_components.CookieManager.

    `cookies` is what the frontend last reported — deliberately NOT updated by
    `set()`, because in the real component the browser only learns about a
    write when the iframe renders, which is after the script run ends.
    `delivered` records the writes a test chooses to let through.
    """

    def __init__(self, reported=None):
        self.cookies = dict(reported or {})
        self.sets: list[tuple[str, str, str]] = []  # (name, value, component key)
        self.deletes: list[tuple[str, str]] = []

    def set(self, cookie, val, key="set", **kwargs):
        self.sets.append((cookie, val, key))

    def delete(self, cookie, key="delete"):
        self.deletes.append((cookie, key))
        if cookie not in self.cookies:
            raise KeyError(cookie)  # the real component raises here
        del self.cookies[cookie]

    def deliver(self):
        """Pretend the browser carried out every write issued so far."""
        for name, value, _key in self.sets:
            self.cookies[name] = value
        for name, _key in self.deletes:
            self.cookies.pop(name, None)


@pytest.fixture
def fake_st(monkeypatch):
    instance = FakeStreamlit()
    monkeypatch.setattr(cookies, "st", instance)
    return instance


def _install_manager(monkeypatch, manager):
    """Make init_cookie_manager() return `manager`, exercising the real entry point."""
    module = SimpleNamespace(CookieManager=lambda key: manager)
    monkeypatch.setitem(sys.modules, "extra_streamlit_components", module)


# ─── The regression this module was rewritten for ────────────────────────────

def test_a_write_lost_to_a_rerun_is_reissued_on_the_next_run(fake_st, monkeypatch):
    manager = FakeCookieManager({"unrelated": "1"})
    _install_manager(monkeypatch, manager)

    cookies.init_cookie_manager()
    cookies.write_cookie("nv_refresh_token", "rt-1", max_age_days=180)
    assert [(name, value) for name, value, _k in manager.sets] == [
        ("nv_refresh_token", "rt-1")
    ]
    first_key = manager.sets[0][2]

    # The run ends in st.rerun(), so the browser never sees that iframe.
    manager.sets.clear()

    cookies.init_cookie_manager()
    assert [(name, value) for name, value, _k in manager.sets] == [
        ("nv_refresh_token", "rt-1")
    ]
    # A different component key, or Streamlit serves the cached (no-op) result.
    assert manager.sets[0][2] != first_key


def test_a_confirmed_write_stops_being_reissued(fake_st, monkeypatch):
    manager = FakeCookieManager()
    _install_manager(monkeypatch, manager)

    cookies.init_cookie_manager()
    cookies.write_cookie("nv_refresh_token", "rt-1", max_age_days=180)
    manager.deliver()
    manager.sets.clear()

    cookies.init_cookie_manager()
    assert manager.sets == []
    assert cookies.pending_writes() == {}
    assert cookies.unconfirmed_writes() == {}


def test_a_write_the_browser_never_takes_is_reported_not_swallowed(fake_st, monkeypatch):
    manager = FakeCookieManager()
    _install_manager(monkeypatch, manager)

    cookies.init_cookie_manager()
    cookies.write_cookie("nv_refresh_token", "rt-1", max_age_days=180)
    for _ in range(cookies._RETRY_RUNS + 1):
        cookies.init_cookie_manager()

    assert cookies.pending_writes() == {}
    assert cookies.unconfirmed_writes() == {"nv_refresh_token": "set"}


def test_rotating_a_value_the_browser_already_holds_is_not_a_refusal(
    fake_st, monkeypatch
):
    """Supabase rotates the refresh token on every restore.

    Comparing values would report a perfectly healthy write as refused on
    every page load, because the component's snapshot is at best one run
    behind the write it is supposed to confirm.
    """
    manager = FakeCookieManager({"nv_refresh_token": "rt-old"})
    _install_manager(monkeypatch, manager)

    cookies.init_cookie_manager()
    cookies.write_cookie("nv_refresh_token", "rt-new", max_age_days=180)
    for _ in range(cookies._RETRY_RUNS + 1):
        cookies.init_cookie_manager()

    assert cookies.unconfirmed_writes() == {}


def test_a_no_retry_write_is_never_replayed(fake_st, monkeypatch):
    """The PKCE verifier is rewritten by the render itself, so it opts out.

    Replaying it would put the previous verifier on the wire next to the fresh
    one, and whichever iframe ran last would decide whether the cookie still
    matched the code_challenge in the URL the user is about to follow.
    """
    manager = FakeCookieManager()
    _install_manager(monkeypatch, manager)

    cookies.init_cookie_manager()
    cookies.write_cookie("nv_pkce_x", "verifier-1", max_age_days=1, retry=False)
    manager.sets.clear()

    cookies.init_cookie_manager()
    assert manager.sets == []
    assert cookies.read_cookie("nv_pkce_x") == "verifier-1"


def test_a_replay_and_a_new_value_in_one_run_stay_distinct(fake_st, monkeypatch):
    manager = FakeCookieManager()
    _install_manager(monkeypatch, manager)

    cookies.init_cookie_manager()
    cookies.write_cookie("nv_refresh_token", "rt-1", max_age_days=180)
    manager.sets.clear()

    cookies.init_cookie_manager()  # replays rt-1
    cookies.write_cookie("nv_refresh_token", "rt-2", max_age_days=180)

    keys = [key for _n, _v, key in manager.sets]
    assert len(set(keys)) == len(keys)  # two components sharing a key is an error
    assert [value for _n, value, _k in manager.sets] == ["rt-1", "rt-2"]
    assert cookies.read_cookie("nv_refresh_token") == "rt-2"


def test_rewriting_the_same_value_the_replay_just_sent_is_not_duplicated(
    fake_st, monkeypatch
):
    manager = FakeCookieManager()
    _install_manager(monkeypatch, manager)

    cookies.init_cookie_manager()
    cookies.write_cookie("nv_refresh_token", "rt-1", max_age_days=180)
    manager.sets.clear()

    cookies.init_cookie_manager()  # replays rt-1
    cookies.write_cookie("nv_refresh_token", "rt-1", max_age_days=180)

    assert len(manager.sets) == 1


# ─── Reads must reflect our own writes, not just the frontend snapshot ───────

def test_a_fresh_write_reads_back_before_the_browser_confirms(fake_st, monkeypatch):
    manager = FakeCookieManager()
    _install_manager(monkeypatch, manager)

    cookies.init_cookie_manager()
    cookies.write_cookie("nv_refresh_token", "rt-1", max_age_days=180)

    assert manager.cookies == {}  # the snapshot genuinely does not have it yet
    assert cookies.read_cookie("nv_refresh_token") == "rt-1"
    assert cookies.all_cookies()["nv_refresh_token"] == "rt-1"


def test_a_deleted_cookie_reads_as_absent_while_the_snapshot_still_has_it(
    fake_st, monkeypatch
):
    manager = FakeCookieManager({"nv_refresh_token": "rt-1"})
    _install_manager(monkeypatch, manager)

    cookies.init_cookie_manager()
    cookies.delete_cookie("nv_refresh_token")

    # Without the tombstone, bootstrap_session() would restore the session the
    # user just logged out of, on the very next run.
    assert cookies.read_cookie("nv_refresh_token") is None
    assert "nv_refresh_token" not in cookies.all_cookies()


def test_deleting_a_cookie_that_was_never_there_costs_nothing(fake_st, monkeypatch):
    """GoTrue clears storage keys it never wrote on every sign_in_with_oauth().

    Those must not queue retries: they would render a delete iframe on every
    run and then show up in the diagnostics as writes the browser refused.
    """
    manager = FakeCookieManager()
    _install_manager(monkeypatch, manager)

    cookies.init_cookie_manager()
    cookies.delete_cookie("nv_pkce_supabase.auth.token")

    assert manager.deletes == []
    assert cookies.pending_writes() == {}
    cookies.init_cookie_manager()
    assert cookies.unconfirmed_writes() == {}


def test_deleting_a_present_cookie_survives_the_component_raising(fake_st, monkeypatch):
    manager = FakeCookieManager({"nv_refresh_token": "rt-1"})
    _install_manager(monkeypatch, manager)

    cookies.init_cookie_manager()
    cookies.delete_cookie("nv_refresh_token")
    assert [name for name, _key in manager.deletes] == ["nv_refresh_token"]

    # The real component deletes from its own snapshot and then raises KeyError
    # on a second attempt; the retry must not take the app down.
    cookies.init_cookie_manager()
    assert cookies.read_cookie("nv_refresh_token") is None


def test_st_context_is_the_last_resort_only(fake_st, monkeypatch):
    fake_st.context.cookies = {"nv_refresh_token": "from-context"}
    manager = FakeCookieManager({"nv_refresh_token": "from-component"})
    _install_manager(monkeypatch, manager)

    cookies.init_cookie_manager()
    assert cookies.read_cookie("nv_refresh_token") == "from-component"
    assert cookies.read_cookie("absent") is None


# ─── Readiness ───────────────────────────────────────────────────────────────

def test_cookies_are_not_ready_before_the_component_answers(fake_st, monkeypatch):
    manager = FakeCookieManager()  # default {} == "hasn't answered yet"
    _install_manager(monkeypatch, manager)

    cookies.init_cookie_manager()
    assert cookies.cookies_ready() is False


def test_readiness_is_sticky_once_the_component_has_answered(fake_st, monkeypatch):
    manager = FakeCookieManager({"unrelated": "1"})
    _install_manager(monkeypatch, manager)
    cookies.init_cookie_manager()
    assert cookies.cookies_ready() is True

    # A later empty answer must not read as "not asked yet" and stall bootstrap.
    manager.cookies = {}
    cookies.init_cookie_manager()
    assert cookies.cookies_ready() is True


def test_a_missing_component_library_leaves_guest_mode_working(fake_st, monkeypatch):
    monkeypatch.setitem(sys.modules, "extra_streamlit_components", None)

    assert cookies.init_cookie_manager() is None
    assert cookies.cookies_ready() is False
    assert cookies.read_cookie("nv_refresh_token") is None
    assert cookies.write_cookie("nv_refresh_token", "rt-1", max_age_days=180) is False
    cookies.delete_cookie("nv_refresh_token")  # must not raise
