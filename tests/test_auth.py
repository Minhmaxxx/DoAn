"""Account identity tests — no network, no real Supabase project.

Every Supabase-facing function in utils.auth takes the client as a parameter
(see that module's docstring), so a fake client stands in here the same way
tests/test_llm.py fakes the Google/OpenAI SDK objects. `st` itself is faked
too: st.session_state needs both dict- and attribute-style access (utils.auth
uses both), and st.context.cookies has no public write API to seed from a
test, so a real Streamlit session can't carry a cookie into restore_session().
"""

import urllib.parse
from types import SimpleNamespace

import pytest

import utils.auth as auth


class FakeSessionState(dict):
    """Minimal stand-in for st.session_state: dict methods + attribute access."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None

    def __setattr__(self, name, value):
        self[name] = value


class FakeContext:
    def __init__(self, cookies=None):
        self.cookies = cookies or {}


class FakeQueryParams(dict):
    """st.query_params: dict access plus the .clear() bootstrap_session calls."""


class FakeStreamlit:
    def __init__(self, cookies=None, query_params=None):
        self.session_state = FakeSessionState()
        self.context = FakeContext(cookies)
        self.query_params = FakeQueryParams(query_params or {})
        self.html_calls: list[str] = []

    def html(self, content, **kwargs):
        self.html_calls.append(content)


class FakeAuthClient:
    """Records calls; each method's return value is set per test as needed."""

    def __init__(self):
        self.calls: list[tuple[str, tuple, dict]] = []
        self.sign_in_anonymously_result = None
        self.refresh_session_result = None
        self.refresh_session_raises = None
        self.link_identity_result = None
        self.exchange_code_result = None
        self.sign_in_with_oauth_result = None

    def sign_in_anonymously(self):
        self.calls.append(("sign_in_anonymously", (), {}))
        return self.sign_in_anonymously_result

    def refresh_session(self, refresh_token):
        self.calls.append(("refresh_session", (refresh_token,), {}))
        if self.refresh_session_raises:
            raise self.refresh_session_raises
        return self.refresh_session_result

    def sign_in_with_oauth(self, credentials):
        self.calls.append(("sign_in_with_oauth", (), {"credentials": credentials}))
        return self.sign_in_with_oauth_result

    def link_identity(self, credentials):
        self.calls.append(("link_identity", (), {"credentials": credentials}))
        return self.link_identity_result

    def exchange_code_for_session(self, params):
        self.calls.append(("exchange_code_for_session", (), {"params": params}))
        return self.exchange_code_result

    def sign_out(self):
        self.calls.append(("sign_out", (), {}))


@pytest.fixture
def fake_st(monkeypatch):
    instance = FakeStreamlit()
    monkeypatch.setattr(auth, "st", instance)
    return instance


def _anon_session(user_id="anon-1", refresh_token="rt-1"):
    return SimpleNamespace(
        user=SimpleNamespace(id=user_id, is_anonymous=True),
        session=SimpleNamespace(refresh_token=refresh_token, access_token="at-1"),
    )


def test_ensure_account_creates_once_and_persists_cookie(fake_st):
    client = FakeAuthClient()
    client.sign_in_anonymously_result = _anon_session()

    user_id = auth.ensure_account(client)

    assert user_id == "anon-1"
    assert auth.current_user_id() == "anon-1"
    assert auth.is_linked() is False
    assert any("rt-1" in call for call in fake_st.html_calls)


def test_ensure_account_is_idempotent_within_a_session(fake_st):
    client = FakeAuthClient()
    client.sign_in_anonymously_result = _anon_session()

    first = auth.ensure_account(client)
    second = auth.ensure_account(client)

    assert first == second == "anon-1"
    sign_in_calls = [call for call in client.calls if call[0] == "sign_in_anonymously"]
    assert len(sign_in_calls) == 1


def test_restore_session_returns_none_without_cookie(fake_st):
    client = FakeAuthClient()
    assert auth.restore_session(client) is None
    assert auth.current_user_id() is None
    assert client.calls == []


def test_restore_session_short_circuits_when_already_signed_in(fake_st):
    fake_st.session_state.auth_user = {"id": "existing", "is_anonymous": True}
    client = FakeAuthClient()

    assert auth.restore_session(client) == "existing"
    assert client.calls == []  # no network call needed


def test_restore_session_rebuilds_identity_from_cookie(fake_st):
    fake_st.context.cookies[auth.SESSION_COOKIE_NAME] = "rt-old"
    client = FakeAuthClient()
    client.refresh_session_result = SimpleNamespace(
        session=SimpleNamespace(refresh_token="rt-new"),
        user=SimpleNamespace(id="anon-1", is_anonymous=True),
    )

    user_id = auth.restore_session(client)

    assert user_id == "anon-1"
    assert auth.is_linked() is False
    assert client.calls == [("refresh_session", ("rt-old",), {})]
    assert any("rt-new" in call for call in fake_st.html_calls)


def test_restore_session_clears_cookie_when_refresh_rejected(fake_st):
    fake_st.context.cookies[auth.SESSION_COOKIE_NAME] = "rt-bad"
    client = FakeAuthClient()
    client.refresh_session_raises = RuntimeError("invalid refresh token")

    assert auth.restore_session(client) is None
    assert auth.current_user_id() is None
    assert any("1970" in call for call in fake_st.html_calls)  # cookie deletion


def test_restore_session_clears_cookie_when_response_is_incomplete(fake_st):
    fake_st.context.cookies[auth.SESSION_COOKIE_NAME] = "rt-weird"
    client = FakeAuthClient()
    client.refresh_session_result = SimpleNamespace(session=None, user=None)

    assert auth.restore_session(client) is None
    assert any("1970" in call for call in fake_st.html_calls)


def test_start_google_link_returns_redirect_url_and_forwards_provider(fake_st):
    client = FakeAuthClient()
    client.link_identity_result = SimpleNamespace(url="https://supabase.example/redirect")

    url = auth.start_google_link(client, redirect_to="https://app.example/callback")

    assert url == "https://supabase.example/redirect"
    _, _, kwargs = client.calls[0]
    assert kwargs["credentials"] == {
        "provider": "google",
        "options": {"redirect_to": "https://app.example/callback"},
    }


def test_complete_oauth_callback_links_without_changing_user_id(fake_st):
    # Simulate ensure_account() having already run for this browser.
    fake_st.session_state.auth_user = {"id": "anon-1", "is_anonymous": True}
    client = FakeAuthClient()
    client.exchange_code_result = SimpleNamespace(
        user=SimpleNamespace(id="anon-1", is_anonymous=False),
        session=SimpleNamespace(refresh_token="rt-linked"),
    )

    user_id = auth.complete_oauth_callback(client, "auth-code-123")

    assert user_id == "anon-1"
    assert auth.is_linked() is True
    _, _, kwargs = client.calls[0]
    assert kwargs["params"] == {"auth_code": "auth-code-123"}


def test_logout_clears_cookie_and_all_personal_session_state(fake_st):
    fake_st.session_state.update(
        {
            "auth_user": {"id": "anon-1", "is_anonymous": True},
            "user_profile": {"name": "Test"},
            "profile_completed": True,
            "meal_history": [{"date": "2026-08-09"}],
            "current_meal": {"foods": []},
            "llm_advice": "some advice",
            "llm_runtime_config": {"provider": "openai"},
            "meal_signature": "sig-1",
            "saved_meal_signatures": {"sig-1"},
            "_supabase_client": object(),  # a real cached Client would be here
            "assistant_enabled": True,  # not cleared: not account-specific
        }
    )
    client = FakeAuthClient()

    auth.logout(client)

    assert auth.current_user_id() is None
    for key in (
        "auth_user",
        "user_profile",
        "profile_completed",
        "meal_history",
        "current_meal",
        "llm_advice",
        "llm_runtime_config",
        "meal_signature",
        "saved_meal_signatures",
        "_supabase_client",
    ):
        assert key not in fake_st.session_state
    assert fake_st.session_state["assistant_enabled"] is True
    assert ("sign_out", (), {}) in client.calls
    assert any("1970" in call for call in fake_st.html_calls)


def test_logout_tolerates_no_client_and_a_failed_sign_out(fake_st):
    fake_st.session_state.auth_user = {"id": "anon-1", "is_anonymous": True}
    auth.logout(None)
    assert auth.current_user_id() is None

    fake_st.session_state.auth_user = {"id": "anon-1", "is_anonymous": True}
    client = FakeAuthClient()
    client.sign_out = lambda: (_ for _ in ()).throw(RuntimeError("network down"))
    auth.logout(client)  # must not raise
    assert auth.current_user_id() is None


def test_get_client_fails_clearly_without_network(monkeypatch, fake_st):
    """Either the optional `supabase` package isn't installed yet (Giai đoạn A
    not run) or secrets.toml has no [supabase] section — get_client() must
    report one of those two documented, specific errors rather than crash.

    Forces the "no [supabase] section" branch via a fake st.secrets rather
    than relying on the real environment: a dev machine that has completed
    Giai đoạn A (like this one, for the spike) has a real secrets.toml on
    disk, which would otherwise make this test silently stop testing the
    failure path it exists to cover.
    """
    fake_st.secrets = SimpleNamespace(get=lambda key, default=None: default)

    with pytest.raises((ImportError, RuntimeError)):
        auth.get_client()


def test_get_client_caches_one_client_per_session(monkeypatch, fake_st):
    """A fresh Client on every call would query Postgrest with the anon key
    even after sign-in, because Supabase only attaches the user's JWT to
    Postgrest requests on its own Client instance via a sign-in/refresh
    event listener (see PROGRESS.md Giai đoạn 0 spike). get_client() must
    hand back the SAME object every time within one session."""
    fake_st.secrets = SimpleNamespace(
        get=lambda key, default=None: (
            {"url": "https://x.supabase.co", "publishable_key": "k"}
            if key == "supabase"
            else default
        )
    )
    created_calls = []

    def fake_create_client(url, key, options=None):
        created_calls.append((url, key, options))
        return SimpleNamespace(marker="the-one-client")

    import supabase

    monkeypatch.setattr(supabase, "create_client", fake_create_client)

    first = auth.get_client()
    second = auth.get_client()

    assert first is second
    assert len(created_calls) == 1
    _, _, options = created_calls[0]
    assert options.persist_session is False
    assert isinstance(options.storage, auth._CodeVerifierCookieStorage)


def test_code_verifier_storage_round_trips_through_cookie(fake_st):
    """set_item() writes a cookie via JS; get_item() reads it back on a LATER
    script run — simulated here by manually seeding fake_st.context.cookies,
    since a real browser round trip can't happen inside a unit test."""
    storage = auth._CodeVerifierCookieStorage()
    key = "supabase.auth.token-code-verifier"

    storage.set_item(key, "verifier-with-special/chars+here")
    written_script = fake_st.html_calls[-1]
    assert f"nv_pkce_{key}" in written_script

    fake_st.context.cookies[f"nv_pkce_{key}"] = urllib.parse.quote(
        "verifier-with-special/chars+here"
    )
    assert storage.get_item(key) == "verifier-with-special/chars+here"


def test_code_verifier_storage_get_item_missing_returns_none(fake_st):
    assert auth._CodeVerifierCookieStorage().get_item("nope") is None


def test_code_verifier_storage_remove_item_expires_the_cookie(fake_st):
    storage = auth._CodeVerifierCookieStorage()
    storage.remove_item("supabase.auth.token-code-verifier")
    assert any(
        "1970" in call and "nv_pkce_supabase.auth.token-code-verifier" in call
        for call in fake_st.html_calls
    )


# ── bootstrap_session / sync_status ──────────────────────────────────────────

def test_bootstrap_session_stays_guest_without_cookie_or_code(monkeypatch, fake_st):
    """The guest path — and the path tests/test_pages.py takes — must return
    before a Supabase client is ever constructed, so the release gate cannot
    make a network call."""
    monkeypatch.setattr(
        auth,
        "get_client",
        lambda: pytest.fail("bootstrap_session built a client in guest mode"),
    )

    assert auth.bootstrap_session() is None
    assert auth.sync_status() == "guest"


def test_bootstrap_session_reuses_an_already_restored_identity(fake_st):
    fake_st.session_state.auth_user = {"id": "anon-1", "is_anonymous": True}
    assert auth.bootstrap_session() == "anon-1"


def test_bootstrap_session_restores_from_cookie(monkeypatch, fake_st):
    fake_st.context.cookies[auth.SESSION_COOKIE_NAME] = "rt-1"
    client = FakeAuthClient()
    client.refresh_session_result = SimpleNamespace(
        user=SimpleNamespace(id="anon-7", is_anonymous=True),
        session=SimpleNamespace(refresh_token="rt-2"),
    )
    monkeypatch.setattr(auth, "get_client", lambda: SimpleNamespace(auth=client))

    assert auth.bootstrap_session() == "anon-7"
    assert auth.sync_status() == "anonymous"


def test_bootstrap_session_completes_oauth_and_drops_the_spent_code(monkeypatch, fake_st):
    fake_st.query_params["code"] = "auth-code-123"
    client = FakeAuthClient()
    client.exchange_code_result = SimpleNamespace(
        user=SimpleNamespace(id="anon-7", is_anonymous=False),
        session=SimpleNamespace(refresh_token="rt-linked"),
    )
    monkeypatch.setattr(auth, "get_client", lambda: SimpleNamespace(auth=client))

    assert auth.bootstrap_session() == "anon-7"
    assert auth.sync_status() == "linked"
    # A refresh must not retry an already-spent auth code.
    assert "code" not in fake_st.query_params


def test_bootstrap_session_downgrades_to_guest_when_supabase_is_unreachable(
    monkeypatch, fake_st
):
    """A paused project or revoked token must not make the app unopenable —
    detection and nutrition still work without an account."""
    fake_st.context.cookies[auth.SESSION_COOKIE_NAME] = "rt-1"
    monkeypatch.setattr(
        auth, "get_client", lambda: (_ for _ in ()).throw(RuntimeError("down"))
    )

    assert auth.bootstrap_session() is None
    assert auth.sync_status() == "guest"


def test_bootstrap_session_reports_a_failed_google_link(monkeypatch, fake_st):
    fake_st.query_params["code"] = "auth-code-123"
    client = FakeAuthClient()
    client.exchange_code_for_session = lambda params: (_ for _ in ()).throw(
        RuntimeError("expired")
    )
    monkeypatch.setattr(auth, "get_client", lambda: SimpleNamespace(auth=client))

    assert auth.bootstrap_session() is None
    assert "sync_error" in fake_st.session_state


def test_sync_status_distinguishes_anonymous_from_linked(fake_st):
    fake_st.session_state.auth_user = {"id": "u", "is_anonymous": True}
    assert auth.sync_status() == "anonymous"

    fake_st.session_state.auth_user = {"id": "u", "is_anonymous": False}
    assert auth.sync_status() == "linked"


def test_sync_available_follows_configuration_without_building_a_client(monkeypatch, fake_st):
    monkeypatch.setattr(
        auth,
        "get_client",
        lambda: pytest.fail("sync_available() must not construct a client"),
    )

    fake_st.secrets = SimpleNamespace(get=lambda key, default=None: default)
    assert auth.sync_available() is False

    fake_st.secrets = SimpleNamespace(
        get=lambda key, default=None: {"url": "https://x.supabase.co"}
    )
    assert auth.sync_available() is False  # publishable_key missing

    fake_st.secrets = SimpleNamespace(
        get=lambda key, default=None: {
            "url": "https://x.supabase.co",
            "publishable_key": "k",
        }
    )
    assert auth.sync_available() is True


def test_sync_blocker_names_the_specific_missing_piece(fake_st):
    """One generic "chưa cấu hình" for three different causes makes a
    misconfigured deployment impossible to diagnose from the UI."""
    fake_st.secrets = SimpleNamespace(
        get=lambda key, default=None: {"url": "https://x.supabase.co"}
    )
    blocker = auth.sync_blocker()
    assert blocker is not None and "publishable_key" in blocker
    assert "url" not in blocker  # url is present, don't blame it

    def raise_secrets(key, default=None):
        raise RuntimeError("no secrets.toml anywhere")

    fake_st.secrets = SimpleNamespace(get=raise_secrets)
    assert "Streamlit secrets" in auth.sync_blocker()

    fake_st.secrets = SimpleNamespace(
        get=lambda key, default=None: {
            "url": "https://x.supabase.co",
            "publishable_key": "k",
        }
    )
    assert auth.sync_blocker() is None


def test_start_google_signin_needs_no_session_and_forwards_redirect(fake_st):
    """Signing in is not the same call as linking: a second device is a guest
    with no session, so link_identity() there would mint a new anonymous
    account and then fail instead of reaching the existing account."""
    client = FakeAuthClient()
    client.sign_in_with_oauth_result = SimpleNamespace(
        url="https://supabase.example/authorize"
    )

    url = auth.start_google_signin(client, redirect_to="https://app.example")

    assert url == "https://supabase.example/authorize"
    _, _, kwargs = client.calls[0]
    assert kwargs["credentials"] == {
        "provider": "google",
        "options": {"redirect_to": "https://app.example"},
    }


def test_start_google_signin_omits_redirect_when_not_configured(fake_st):
    """No redirect_to means Supabase falls back to its dashboard Site URL,
    which is what production wants."""
    client = FakeAuthClient()
    client.sign_in_with_oauth_result = SimpleNamespace(url="https://x/authorize")

    auth.start_google_signin(client)

    _, _, kwargs = client.calls[0]
    assert kwargs["credentials"] == {"provider": "google", "options": {}}


def test_session_cookie_is_percent_decoded(fake_st):
    """persist_session() writes through encodeURIComponent, so the browser
    returns the encoded form. Reading it raw handed a corrupted token to
    refresh_session() for any token containing an escaped character."""
    fake_st.context.cookies[auth.SESSION_COOKIE_NAME] = "abc%2Fdef%2Bghi%3D"
    assert auth._session_cookie() == "abc/def+ghi="


def test_restore_session_records_why_it_gave_up(fake_st):
    """Dropping to guest silently is indistinguishable from never having had
    a cookie, which is what made this failure so hard to place on a live
    deployment."""
    fake_st.context.cookies[auth.SESSION_COOKIE_NAME] = "rt-bad"
    client = FakeAuthClient()
    client.refresh_session_raises = RuntimeError("refresh token not found")

    assert auth.restore_session(client) is None
    assert "refresh token not found" in fake_st.session_state["sync_error"]


def test_cookie_diagnostics_reports_what_the_server_received(fake_st):
    fake_st.context.cookies.update(
        {auth.SESSION_COOKIE_NAME: "abcd", "nv_pkce_x": "v", "other": "1"}
    )
    info = auth.cookie_diagnostics()

    assert info["readable"] is True
    assert info["has_session_cookie"] is True
    assert info["session_cookie_length"] == 4
    assert info["pkce_cookies"] == ["nv_pkce_x"]
    assert info["total_cookies"] == 3
