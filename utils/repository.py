"""Data access behind one interface, so pages don't need to know guest vs signed-in.

SessionRepository backs the guest experience described in utils/state.py: data
lives only in st.session_state and is gone when the browser session ends.
SupabaseRepository backs a signed-in account (anonymous or Google-linked, see
utils/auth.py) once Giai đoạn C wires this into the pages. Both implement the
same Repository protocol, so a page calls get_repository() once and doesn't
branch on auth state itself.
"""

from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable

import streamlit as st

from utils.history import (
    build_meal_record,
    meal_uuid,
    record_from_row,
    record_signature,
    sort_meal_history,
)


@runtime_checkable
class Repository(Protocol):
    """Interface both backends implement — see class docstrings for contracts."""

    def load_profile(self) -> Optional[dict]: ...
    def save_profile(self, profile: dict) -> None: ...
    def load_meals(self, limit: int = 50) -> list[dict]: ...
    def save_meal(self, meal_data: dict, signature: str) -> bool: ...
    def save_record(self, record: dict) -> bool: ...
    def delete_all_meals(self) -> None: ...


class SessionRepository:
    """Guest-mode repository: reads and writes st.session_state directly.

    This mirrors the pre-storage-plan behavior in pages/1_Phan_tich_anh.py and
    pages/3_Ho_so.py exactly, so switching a page to go through this class
    instead of touching st.session_state inline is a no-op for guests.
    """

    def load_profile(self) -> Optional[dict]:
        return st.session_state.get("user_profile")

    def save_profile(self, profile: dict) -> None:
        st.session_state.user_profile = profile
        st.session_state.profile_completed = True

    def load_meals(self, limit: int = 50) -> list[dict]:
        records = sort_meal_history(st.session_state.get("meal_history", []))
        return records[:limit]

    def save_meal(self, meal_data: dict, signature: str) -> bool:
        """Append one confirmed meal version and reject repeated save clicks.

        Same idempotency contract as utils.history.append_meal_once(), kept
        here instead of delegated to it because the two callers hold their
        list/set in different places (bare locals there, session-state
        collections here).
        """
        records = st.session_state.setdefault("meal_history", [])
        saved_signatures = st.session_state.setdefault("saved_meal_signatures", set())
        if not signature or signature in saved_signatures:
            return False
        records.append(build_meal_record(meal_data))
        saved_signatures.add(signature)
        return True

    def save_record(self, record: dict) -> bool:
        """Store an already-built record (used when migrating guest data).

        Deduplicates on the content hash, not the timestamp: Windows clock
        resolution lets distinct meals share a timestamp — see
        utils.history.record_signature().
        """
        records = st.session_state.setdefault("meal_history", [])
        signature = record_signature(record)
        if any(record_signature(r) == signature for r in records):
            return False
        records.append(record)
        return True

    def delete_all_meals(self) -> None:
        st.session_state.meal_history = []
        st.session_state.saved_meal_signatures = set()


class SupabaseRepository:
    """Signed-in repository: Supabase Postgres (see storage_schema.sql) is the
    source of truth. `client` is a supabase-py `Client`, injected rather than
    constructed here so tests can pass a fake — see tests/test_repository.py.
    """

    def __init__(self, client: Any, user_id: str):
        self._client = client
        self._user_id = user_id

    def load_profile(self) -> Optional[dict]:
        # postgrest-py's maybe_single().execute() returns None outright (not
        # a response object with .data=None) when zero rows match — confirmed
        # against the real SDK, see PROGRESS.md Giai đoạn 0 spike.
        result = (
            self._client.table("profiles")
            .select("*")
            .eq("user_id", self._user_id)
            .maybe_single()
            .execute()
        )
        row = result.data if result else None
        if not row:
            return None
        return {
            "name": row["name"],
            "age": row["age"],
            "gender": row["gender"],
            "weight_kg": row["weight_kg"],
            "height_cm": row["height_cm"],
            "activity_level": row["activity_level"],
            "goal": row["goal"],
        }

    def save_profile(self, profile: dict) -> None:
        self._client.table("profiles").upsert(
            {"user_id": self._user_id, **profile}
        ).execute()

    def load_meals(self, limit: int = 50) -> list[dict]:
        result = (
            self._client.table("meals")
            .select("*")
            .eq("user_id", self._user_id)
            .order("eaten_at", desc=True)
            .limit(limit)
            .execute()
        )
        return [record_from_row(row) for row in (result.data or [])]

    def save_meal(self, meal_data: dict, signature: str) -> bool:
        """Insert one confirmed meal. See utils.history.meal_uuid() for why
        the id is derived from (user_id, signature) instead of random: a
        retried insert after a dropped response reuses the same id and is
        rejected as a duplicate key instead of creating a second meal row.
        """
        if not signature:
            return False
        return self._upsert_record(build_meal_record(meal_data), signature)

    def save_record(self, record: dict) -> bool:
        """Store an already-built record (used when migrating guest data)."""
        return self._upsert_record(record, record_signature(record))

    def _upsert_record(self, record: dict, signature: str) -> bool:
        row = {
            "id": meal_uuid(self._user_id, signature),
            "user_id": self._user_id,
            "eaten_at": record["timestamp"],
            "meal_type": record["meal_type"],
            "foods": record["foods"],
            "totals": record["totals"],
        }
        result = (
            self._client.table("meals")
            .upsert(row, on_conflict="id", ignore_duplicates=True)
            .execute()
        )
        return bool(result.data)

    def delete_all_meals(self) -> None:
        self._client.table("meals").delete().eq("user_id", self._user_id).execute()


def get_repository() -> Repository:
    """Pick the repository for the current session's auth state.

    Local import: keeps get_client()'s optional `supabase` package import out
    of the guest-mode path, where it should never be needed.
    """
    from utils.auth import current_user_id, get_client

    user_id = current_user_id()
    if user_id is None:
        return SessionRepository()
    return SupabaseRepository(get_client(), user_id)


def enable_sync() -> str:
    """Turn a guest into an anonymous account and push existing session data up.

    Sync is opt-in rather than triggered automatically by the first save (which
    is what STORAGE_PLAN.md section 6 originally sketched). Two reasons, both
    load-bearing:

    - Uploading someone's health profile to a server the moment they press
      "Lưu thay đổi", without ever asking, is not a decision to make silently.
    - It keeps guest mode the genuine default, so tests/test_pages.py stays
      offline by construction instead of by mocking. A dev machine with a real
      secrets.toml would otherwise create a live anonymous account on every
      AppTest run of the profile page.

    The lazy-creation property STORAGE_PLAN.md section 3 asks for is unchanged:
    a visitor who never opts in creates no row in auth.users.

    Raises whatever get_client()/sign_in_anonymously() raise — the caller shows
    the failure instead of silently leaving the user in guest mode believing
    they are synced.
    """
    from utils.auth import ensure_account, get_client

    client = get_client()
    user_id = ensure_account(client.auth)
    repo = SupabaseRepository(client, user_id)

    # Push what the guest already had, then re-read so session and server agree.
    if st.session_state.get("profile_completed"):
        repo.save_profile(st.session_state.user_profile)
    for record in st.session_state.get("meal_history", []):
        repo.save_record(record)

    hydrate_session(repo)
    return user_id


def hydrate_session(repo: Optional[Repository] = None) -> None:
    """Load the account's stored profile and meals into session state.

    Called after enabling sync and after restoring a session on app start, so
    every page can keep reading st.session_state as before without knowing
    whether the data came from the cloud or the session.
    """
    repo = repo or get_repository()

    profile = repo.load_profile()
    if profile:
        st.session_state.user_profile = profile
        st.session_state.profile_completed = True

    st.session_state.meal_history = repo.load_meals()
