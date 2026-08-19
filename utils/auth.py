"""Account identity: lazy anonymous accounts upgraded to Google via Supabase.

See STORAGE_PLAN.md section 3-4. Design intent, so future edits keep the
shape:

- Every Supabase-calling function takes the client as a parameter instead of
  constructing one internally, the same way utils/llm.NutriLLM separates
  `_get_google`/`_get_openai` from the calls that use them. That is what lets
  this module be unit tested with a fake client and no network or Supabase
  project (see tests/test_auth.py).
- `ensure_account()` is the ONLY place an anonymous account gets created, and
  it must only be called right before the first write (profile save or meal
  save) — never on page load — so casual visitors don't create rows in
  `auth.users`.
- Nothing here ever puts an access or refresh token into st.session_state.
  Tokens only ever pass through persist_session()/restore_session(), which
  move them to/from the browser cookie. st.session_state is visible to every
  page and gets logged more casually than a cookie value.
"""

from __future__ import annotations

import urllib.parse
from typing import Any, Optional, Protocol, runtime_checkable

import streamlit as st

SESSION_COOKIE_NAME = "nv_refresh_token"
COOKIE_MAX_AGE_DAYS = 180


@runtime_checkable
class SupabaseAuthClient(Protocol):
    """The slice of the supabase-py `Client.auth` this module depends on.

    Kept narrow and structural (a Protocol, not the real SDK type) so tests
    can hand in a plain object with just these methods.
    """

    def sign_in_anonymously(self) -> Any: ...
    def refresh_session(self, refresh_token: str) -> Any: ...
    def link_identity(self, credentials: dict) -> Any: ...
    def exchange_code_for_session(self, params: dict) -> Any: ...
    def sign_out(self) -> Any: ...


class _CodeVerifierCookieStorage:
    """GoTrue storage backend used ONLY for the PKCE `code_verifier`.

    `link_identity()` generates a code_verifier and stashes it via
    `self._storage.set_item(...)`; `exchange_code_for_session()` reads it back
    the same way. The default storage (an in-memory dict on the Client
    object) does not survive the round trip a Google OAuth link requires:
    the browser fully navigates away to accounts.google.com and back, which
    is a fresh page load with a fresh session_state — get_client() then
    builds a brand-new Client with an empty in-memory store, so the verifier
    written during start_google_link() would already be gone by the time
    complete_oauth_callback() needs it. A cookie survives that navigation the
    same way SESSION_COOKIE_NAME does for the refresh token. Confirmed empirically
    against supabase-py 2.31 (see PROGRESS.md Giai đoạn 0 spike) — this class
    is wired in with persist_session=False, so GoTrue never uses it for the
    full session, only for this single short-lived value.
    """

    _PREFIX = "nv_pkce_"
    _MAX_AGE_SECONDS = 600  # verifiers are single-use; an OAuth redirect takes seconds, not hours

    def get_item(self, key: str) -> Optional[str]:
        try:
            raw = st.context.cookies.get(self._PREFIX + key)
        except Exception:
            return None
        # Same reason as _session_cookie(): only a real string is a value here.
        if not isinstance(raw, str) or not raw:
            return None
        return urllib.parse.unquote(raw)

    def set_item(self, key: str, value: str) -> None:
        st.html(
            f"""
            <script>
            (() => {{
              const expires = new Date(Date.now() + {self._MAX_AGE_SECONDS} * 1000).toUTCString();
              window.parent.document.cookie =
                "{self._PREFIX}{key}=" + encodeURIComponent("{value}") +
                "; expires=" + expires + "; path=/; SameSite=Lax; Secure";
            }})();
            </script>
            """,
            unsafe_allow_javascript=True,
        )

    def remove_item(self, key: str) -> None:
        st.html(
            f"""
            <script>
            window.parent.document.cookie =
              "{self._PREFIX}{key}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; SameSite=Lax; Secure";
            </script>
            """,
            unsafe_allow_javascript=True,
        )


def get_client():
    """Build (or reuse) a Supabase client from `st.secrets["supabase"]`.

    Cached in st.session_state for the rest of this browser session — not for
    speed, but for correctness: Supabase's Client listens for its own
    sign-in/refresh events and only then attaches the user's JWT to Postgrest
    requests (see PROGRESS.md Giai đoạn 0 spike). A fresh Client per call
    would mean SupabaseRepository always queries as the anon key, which RLS
    would reject. persist_session=False because this module already persists
    the refresh token itself (persist_session()/restore_session()); the
    custom storage plugged in here exists only to carry the PKCE
    code_verifier across the Google-redirect round trip — see
    _CodeVerifierCookieStorage.

    Raises ImportError if the `supabase` package isn't installed, and
    RuntimeError if the `[supabase]` secrets section is missing. Both are
    expected until Giai đoạn A/C wire real deployment credentials — callers
    that only need guest mode (current_user_id() is None) never reach this
    function.
    """
    cached = st.session_state.get("_supabase_client")
    if cached is not None:
        return cached

    from supabase import create_client  # local import: optional dependency
    from supabase.lib.client_options import SyncClientOptions

    try:
        supa_secrets = st.secrets.get("supabase", {})
    except Exception as error:  # StreamlitSecretNotFoundError when no secrets.toml exists at all
        raise RuntimeError(
            "Thiếu cấu hình Supabase trong Streamlit secrets "
            "([supabase] url / publishable_key)."
        ) from error

    url = supa_secrets.get("url")
    key = supa_secrets.get("publishable_key")
    if not url or not key:
        raise RuntimeError(
            "Thiếu cấu hình Supabase trong Streamlit secrets "
            "([supabase] url / publishable_key)."
        )
    client = create_client(
        url,
        key,
        options=SyncClientOptions(
            persist_session=False, storage=_CodeVerifierCookieStorage()
        ),
    )
    st.session_state["_supabase_client"] = client
    return client


# ─── Session-state identity (no tokens) ──────────────────────────────────────

def current_user_id() -> Optional[str]:
    """Return the signed-in user's id, or None in guest mode."""
    auth_user = st.session_state.get("auth_user")
    return auth_user.get("id") if auth_user else None


def is_linked() -> bool:
    """True once the account is backed by a real identity (Google), not just anonymous."""
    auth_user = st.session_state.get("auth_user")
    return bool(auth_user) and auth_user.get("is_anonymous") is False


def _set_current_user(user_id: str, is_anonymous: bool) -> None:
    st.session_state.auth_user = {"id": user_id, "is_anonymous": is_anonymous}


def _clear_current_user() -> None:
    st.session_state.pop("auth_user", None)


# ─── Cookie persistence ──────────────────────────────────────────────────────
# st.context.cookies is read-only in Streamlit 1.61 (runtime/context.py), so
# writing has to go through JS on the parent document, the same pattern
# utils/pwa.py uses for manifest metadata. This means the refresh token is not
# HttpOnly and any XSS becomes account takeover; see STORAGE_PLAN.md section 9
# for the mitigations that are load-bearing alongside this module.

def _session_cookie() -> Optional[str]:
    """Read the refresh-token cookie, or None when there isn't a usable one.

    Insists on a non-empty `str` rather than trusting truthiness. Under
    streamlit.testing's AppTest, `st.context.cookies.get(...)` returns a
    MagicMock — truthy, but not a token — which previously made the guest
    path believe it had a session, build a Supabase client and try to refresh
    with a mock object. That broke the promise that the release gate makes no
    network calls, and it would equally mishandle any non-string a future
    Streamlit version returned here.
    """
    try:
        token = st.context.cookies.get(SESSION_COOKIE_NAME)
    except Exception:
        return None
    return token if isinstance(token, str) and token else None


def persist_session(refresh_token: str) -> None:
    """Write the refresh token to a browser cookie so it survives a reload."""
    st.html(
        f"""
        <script>
        (() => {{
          const expires = new Date(Date.now() + {COOKIE_MAX_AGE_DAYS} * 864e5).toUTCString();
          window.parent.document.cookie =
            "{SESSION_COOKIE_NAME}=" + encodeURIComponent("{refresh_token}") +
            "; expires=" + expires + "; path=/; SameSite=Lax; Secure";
        }})();
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def clear_session_cookie() -> None:
    """Delete the persisted cookie (logout, or a rejected refresh token)."""
    st.html(
        f"""
        <script>
        window.parent.document.cookie =
          "{SESSION_COOKIE_NAME}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; SameSite=Lax; Secure";
        </script>
        """,
        unsafe_allow_javascript=True,
    )


# ─── Account lifecycle ───────────────────────────────────────────────────────

def ensure_account(client: SupabaseAuthClient) -> str:
    """Create (or reuse) the account that owns this browser's data.

    Call this immediately before the first write, not on page load — see the
    module docstring. Idempotent within a session: if an account is already
    tracked in session state, returns its id without a network call.
    """
    existing = current_user_id()
    if existing:
        return existing

    response = client.sign_in_anonymously()
    _set_current_user(response.user.id, is_anonymous=True)
    persist_session(response.session.refresh_token)
    return response.user.id


def restore_session(client: SupabaseAuthClient) -> Optional[str]:
    """Rebuild identity from the browser cookie left by a previous visit.

    Returns the restored user id, or None if there was no cookie, or the
    server rejected the refresh token (expired, revoked, or Supabase project
    reset) — in which case the stale cookie is cleared so it doesn't keep
    failing on every subsequent page load.
    """
    if current_user_id():
        return current_user_id()

    token = _session_cookie()
    if not token:
        return None

    try:
        response = client.refresh_session(token)
    except Exception:
        clear_session_cookie()
        return None

    session = getattr(response, "session", None)
    user = getattr(response, "user", None)
    if not session or not user:
        clear_session_cookie()
        return None

    _set_current_user(user.id, is_anonymous=bool(user.is_anonymous))
    persist_session(session.refresh_token)
    return user.id


def start_google_link(
    client: SupabaseAuthClient, redirect_to: Optional[str] = None
) -> str:
    """Begin linking a Google identity to the current account.

    Requires an existing Supabase session — call ensure_account() first, or
    this links nothing and instead starts a fresh unrelated sign-in. Returns
    the URL to send the browser to (`st.link_button` / a redirect).

    `redirect_to` must be nested under `options`, not top-level — confirmed
    against the installed supabase-py's `SignInWithOAuthCredentials` shape
    (see PROGRESS.md Giai đoạn 0 spike). A top-level key is silently ignored,
    not rejected, so this was easy to get wrong without actually inspecting
    the SDK. When redirect_to is None the key is omitted entirely and Supabase
    falls back to the Site URL configured in its dashboard.
    """
    options = {"redirect_to": redirect_to} if redirect_to else {}
    response = client.link_identity({"provider": "google", "options": options})
    return response.url


def complete_oauth_callback(client: SupabaseAuthClient, auth_code: str) -> str:
    """Exchange the `?code=` Supabase appended after Google OAuth for a session.

    Because link_identity() is used (not a fresh sign-in), this resolves to
    the SAME user id the anonymous account already had — no data migration
    step is needed. See STORAGE_PLAN.md section 13 for the fallback if a spike
    shows that assumption doesn't hold for the installed supabase-py version.
    """
    response = client.exchange_code_for_session({"auth_code": auth_code})
    _set_current_user(response.user.id, is_anonymous=bool(response.user.is_anonymous))
    persist_session(response.session.refresh_token)
    return response.user.id


def logout(client: Optional[SupabaseAuthClient] = None) -> None:
    """Sign out of Supabase and scrub every piece of personal session state.

    Safe to call in guest mode (client=None or no active account): it just
    clears whatever local state exists.
    """
    if client is not None:
        try:
            client.sign_out()
        except Exception:
            pass  # already-expired/revoked sessions must not block logout
    clear_session_cookie()
    _clear_current_user()
    for key in (
        "user_profile",
        "profile_completed",
        "meal_history",
        "current_meal",
        "llm_advice",
        "llm_runtime_config",
        "meal_signature",
        "saved_meal_signatures",
        "_supabase_client",  # drop the cached Client too, not just the id — see get_client()
    ):
        st.session_state.pop(key, None)


# ─── App bootstrap ───────────────────────────────────────────────────────────

def sync_available() -> bool:
    """True when cloud sync can even be attempted on this deployment.

    False when the `supabase` package is missing or `[supabase]` secrets are
    absent — the state CI runs in. Pages use this to hide sync controls
    rather than offer a button that can only fail.

    Checks configuration instead of calling get_client(), so merely rendering
    the profile page as a guest doesn't construct a Supabase client.
    """
    try:
        import supabase  # noqa: F401
    except ImportError:
        return False

    try:
        supa_secrets = st.secrets.get("supabase", {})
    except Exception:
        return False
    return bool(supa_secrets.get("url") and supa_secrets.get("publishable_key"))


def sync_status() -> str:
    """One of "guest", "anonymous" or "linked" — the three states in
    STORAGE_PLAN.md section 4. Pages must never describe "anonymous" as
    synced: the data is on the server but only this browser can reach it."""
    if not current_user_id():
        return "guest"
    return "linked" if is_linked() else "anonymous"


def site_url() -> Optional[str]:
    """Where Google should send the user back after linking.

    Optional: when absent, start_google_link() omits redirect_to and Supabase
    falls back to the Site URL configured in its dashboard. Set it in secrets
    for local development, where the deployed Site URL would be wrong.
    """
    try:
        return st.secrets.get("supabase", {}).get("site_url") or None
    except Exception:
        return None


def bootstrap_session() -> Optional[str]:
    """Restore identity at app start. Returns the user id, or None for guests.

    Deliberately returns before constructing any Supabase client when there
    is neither a session cookie nor an OAuth `?code=` in the URL. That is the
    guest path, and it is also the path tests/test_pages.py takes, so the
    release gate never builds a client or touches the network.

    Every failure downgrades to guest mode instead of raising: a paused
    Supabase project or a revoked token must not make the whole app
    unopenable when detection and nutrition still work offline.
    """
    if current_user_id():
        return current_user_id()

    auth_code = st.query_params.get("code")
    if not isinstance(auth_code, str) or not auth_code:
        auth_code = None

    if not auth_code and not _session_cookie():
        return None

    try:
        client = get_client()
    except Exception:
        return None

    if auth_code:
        try:
            user_id = complete_oauth_callback(client.auth, auth_code)
        except Exception:
            st.session_state["sync_error"] = (
                "Không hoàn tất được liên kết Google. Hãy thử lại từ trang Hồ sơ."
            )
            return None
        # Drop ?code= so a refresh doesn't retry an already-spent auth code.
        st.query_params.clear()
        return user_id

    try:
        return restore_session(client.auth)
    except Exception:
        return None
