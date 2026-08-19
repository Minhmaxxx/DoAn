"""Repository tests — no network, no real Supabase project.

SessionRepository exercises the real (bare-mode) st.session_state directly,
the same object a page would touch; a fixture resets the keys it owns before
and after each test so runs don't leak into each other. SupabaseRepository is
exercised against FakeSupabaseClient, a minimal stand-in for supabase-py's
fluent `.table(...).select(...).eq(...).execute()` chains that records every
call instead of hitting a network — the same dependency-injection shape
tests/test_llm.py uses for the Google/OpenAI SDK objects.
"""

from datetime import datetime
from types import SimpleNamespace

import pytest
import streamlit as st

from utils.history import (
    build_meal_record,
    meal_uuid,
    record_from_row,
    record_signature,
)
from utils.repository import (
    Repository,
    SessionRepository,
    SupabaseRepository,
    hydrate_session,
)
import utils.repository as repository


SESSION_KEYS = ("user_profile", "profile_completed", "meal_history", "saved_meal_signatures")


@pytest.fixture(autouse=True)
def clean_session_state():
    for key in SESSION_KEYS:
        st.session_state.pop(key, None)
    yield
    for key in SESSION_KEYS:
        st.session_state.pop(key, None)


def test_session_repository_implements_repository_protocol():
    assert isinstance(SessionRepository(), Repository)


# ── SessionRepository (guest mode) ───────────────────────────────────────────

def test_session_repository_profile_round_trip():
    repo = SessionRepository()
    assert repo.load_profile() is None

    repo.save_profile({"name": "Test", "age": 22})

    assert repo.load_profile() == {"name": "Test", "age": 22}
    assert st.session_state.profile_completed is True


def test_session_repository_save_meal_is_idempotent_per_signature():
    repo = SessionRepository()
    meal = {"foods": [], "total_calories": 380}

    assert repo.save_meal(meal, "sig-1") is True
    assert repo.save_meal(meal, "sig-1") is False
    assert len(repo.load_meals()) == 1


def test_session_repository_save_meal_rejects_empty_signature():
    repo = SessionRepository()
    assert repo.save_meal({"foods": [], "total_calories": 0}, "") is False
    assert repo.load_meals() == []


def test_session_repository_load_meals_is_bounded_by_limit():
    repo = SessionRepository()
    for i in range(3):
        repo.save_meal({"foods": [], "total_calories": i}, f"sig-{i}")

    assert len(repo.load_meals(limit=2)) == 2
    assert len(repo.load_meals()) == 3


def test_session_repository_delete_all_meals_frees_signatures():
    repo = SessionRepository()
    repo.save_meal({"foods": [], "total_calories": 0}, "sig-1")

    repo.delete_all_meals()

    assert repo.load_meals() == []
    assert repo.save_meal({"foods": [], "total_calories": 0}, "sig-1") is True


# ── SupabaseRepository (signed-in) ────────────────────────────────────────────

class FakeQuery:
    """Records every chained call; `.execute()` returns the configured result."""

    def __init__(self, result):
        self._result = result
        self.calls: list[tuple[str, tuple, dict]] = []

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return self

        return record

    def execute(self):
        return self._result

    def call_names(self):
        return [name for name, _, _ in self.calls]


class FakeSupabaseClient:
    def __init__(self):
        self._queries: dict[str, FakeQuery] = {}
        self.table_calls: list[str] = []

    def configure(self, table_name: str, result) -> FakeQuery:
        query = FakeQuery(result)
        self._queries[table_name] = query
        return query

    def table(self, name):
        self.table_calls.append(name)
        return self._queries[name]


PROFILE_ROW = {
    "user_id": "user-1",
    "name": "Nguyễn Văn A",
    "age": 30,
    "gender": "Nam",
    "weight_kg": 65.0,
    "height_cm": 170.0,
    "activity_level": "Vừa phải (3-5 ngày/tuần)",
    "goal": "Giữ cân",
    "created_at": "2026-08-01T00:00:00+00:00",
    "updated_at": "2026-08-01T00:00:00+00:00",
}


def test_supabase_repository_load_profile_strips_storage_only_columns():
    client = FakeSupabaseClient()
    client.configure("profiles", SimpleNamespace(data=PROFILE_ROW))
    repo = SupabaseRepository(client, "user-1")

    profile = repo.load_profile()

    assert profile == {
        "name": "Nguyễn Văn A",
        "age": 30,
        "gender": "Nam",
        "weight_kg": 65.0,
        "height_cm": 170.0,
        "activity_level": "Vừa phải (3-5 ngày/tuần)",
        "goal": "Giữ cân",
    }
    query = client._queries["profiles"]
    assert ("eq", ("user_id", "user-1"), {}) in query.calls
    assert "maybe_single" in query.call_names()


def test_supabase_repository_load_profile_returns_none_when_missing():
    """postgrest-py's maybe_single().execute() returns None outright (not a
    response object with .data=None) when zero rows match — confirmed against
    the real SDK in the Giai đoạn 0 spike, not just assumed."""
    client = FakeSupabaseClient()
    client.configure("profiles", None)
    repo = SupabaseRepository(client, "user-1")

    assert repo.load_profile() is None


def test_supabase_repository_save_profile_upserts_with_user_id_attached():
    client = FakeSupabaseClient()
    client.configure("profiles", SimpleNamespace(data=[PROFILE_ROW]))
    repo = SupabaseRepository(client, "user-1")

    repo.save_profile({"name": "Test", "age": 25})

    upsert_calls = [
        (args, kwargs)
        for name, args, kwargs in client._queries["profiles"].calls
        if name == "upsert"
    ]
    assert len(upsert_calls) == 1
    (payload,), _ = upsert_calls[0]
    assert payload == {"user_id": "user-1", "name": "Test", "age": 25}


def test_supabase_repository_load_meals_maps_rows_and_scopes_query():
    rows = [
        {
            "eaten_at": "2026-08-09T05:00:00+07:00",
            "meal_type": "Bữa sáng",
            "foods": [],
            "totals": {"calories": 0, "carbohydrate_g": 0, "protein_g": 0, "fat_g": 0},
        }
    ]
    client = FakeSupabaseClient()
    client.configure("meals", SimpleNamespace(data=rows))
    repo = SupabaseRepository(client, "user-1")

    meals = repo.load_meals(limit=10)

    assert meals == [record_from_row(rows[0])]
    query = client._queries["meals"]
    assert ("eq", ("user_id", "user-1"), {}) in query.calls
    assert ("limit", (10,), {}) in query.calls


def test_supabase_repository_load_meals_handles_empty_result():
    client = FakeSupabaseClient()
    client.configure("meals", SimpleNamespace(data=None))
    repo = SupabaseRepository(client, "user-1")

    assert repo.load_meals() == []


def test_supabase_repository_save_meal_uses_deterministic_id_and_dedup_upsert():
    client = FakeSupabaseClient()
    client.configure("meals", SimpleNamespace(data=[{"id": "some-uuid"}]))
    repo = SupabaseRepository(client, "user-1")

    saved = repo.save_meal({"foods": [], "total_calories": 380}, "sig-1")

    assert saved is True
    upsert_calls = [
        (args, kwargs)
        for name, args, kwargs in client._queries["meals"].calls
        if name == "upsert"
    ]
    assert len(upsert_calls) == 1
    (row,), kwargs = upsert_calls[0]
    assert row["id"] == meal_uuid("user-1", "sig-1")
    assert row["user_id"] == "user-1"
    assert kwargs == {"on_conflict": "id", "ignore_duplicates": True}


def test_supabase_repository_save_meal_rejects_empty_signature_without_network():
    client = FakeSupabaseClient()
    repo = SupabaseRepository(client, "user-1")

    assert repo.save_meal({"foods": [], "total_calories": 0}, "") is False
    assert client.table_calls == []


def test_supabase_repository_delete_all_meals_scopes_to_owner():
    client = FakeSupabaseClient()
    client.configure("meals", SimpleNamespace(data=[]))
    repo = SupabaseRepository(client, "user-1")

    repo.delete_all_meals()

    query = client._queries["meals"]
    assert "delete" in query.call_names()
    assert ("eq", ("user_id", "user-1"), {}) in query.calls


# ── save_record (used when migrating guest data into an account) ─────────────

def test_session_repository_save_record_rejects_a_duplicate_timestamp():
    repo = SessionRepository()
    record = build_meal_record({"foods": [], "total_calories": 100})

    assert repo.save_record(record) is True
    assert repo.save_record(record) is False
    assert len(st.session_state.meal_history) == 1


def test_supabase_repository_save_record_derives_its_id_from_the_content_hash():
    """Re-running a migration must reuse the same row id rather than
    duplicating every meal, so the id comes from the record's content — not
    its timestamp, which distinct meals can share (see record_signature)."""
    client = FakeSupabaseClient()
    client.configure("meals", SimpleNamespace(data=[{"id": "x"}]))
    repo = SupabaseRepository(client, "user-1")
    record = build_meal_record({"foods": [], "total_calories": 100})

    assert repo.save_record(record) is True

    (row,), kwargs = next(
        (args, kw) for name, args, kw in client._queries["meals"].calls if name == "upsert"
    )
    assert row["id"] == meal_uuid("user-1", record_signature(record))
    assert row["eaten_at"] == record["timestamp"]
    assert kwargs == {"on_conflict": "id", "ignore_duplicates": True}


def test_supabase_repository_save_record_keeps_meals_sharing_a_timestamp_apart():
    """The bug this guards: two meals built in the same 16ms Windows clock tick
    must still become two rows, not silently overwrite each other."""
    client = FakeSupabaseClient()
    client.configure("meals", SimpleNamespace(data=[{"id": "x"}]))
    repo = SupabaseRepository(client, "user-1")
    at = datetime(2026, 8, 9, 12, 0)

    repo.save_record(build_meal_record({"foods": [], "total_calories": 400}, at=at))
    repo.save_record(build_meal_record({"foods": [], "total_calories": 700}, at=at))

    ids = [
        args[0]["id"]
        for name, args, _ in client._queries["meals"].calls
        if name == "upsert"
    ]
    assert len(ids) == 2
    assert ids[0] != ids[1]


# ── hydrate_session / enable_sync ────────────────────────────────────────────

class FakeRepo:
    def __init__(self, profile=None, meals=None):
        self.profile = profile
        self.meals = meals or []
        self.saved_profiles: list[dict] = []
        self.saved_records: list[dict] = []

    def load_profile(self):
        return self.profile

    def save_profile(self, profile):
        self.saved_profiles.append(profile)
        self.profile = profile

    def load_meals(self, limit: int = 50):
        return self.meals[:limit]

    def save_meal(self, meal_data, signature):
        return True

    def save_record(self, record):
        self.saved_records.append(record)
        return True

    def delete_all_meals(self):
        self.meals = []


def test_hydrate_session_fills_profile_and_meals_from_storage():
    stored_profile = {"name": "Đã lưu", "age": 40}
    stored_meals = [build_meal_record({"foods": [], "total_calories": 500})]

    hydrate_session(FakeRepo(profile=stored_profile, meals=stored_meals))

    assert st.session_state.user_profile == stored_profile
    assert st.session_state.profile_completed is True
    assert st.session_state.meal_history == stored_meals


def test_hydrate_session_leaves_profile_alone_when_account_has_none():
    st.session_state.user_profile = {"name": "Chưa lưu"}
    st.session_state.profile_completed = False

    hydrate_session(FakeRepo(profile=None, meals=[]))

    assert st.session_state.user_profile == {"name": "Chưa lưu"}
    assert st.session_state.profile_completed is False


def test_enable_sync_uploads_existing_guest_data_before_reloading(monkeypatch):
    """A guest who filled in a profile and logged meals, then opts in, must not
    lose either — both get pushed up before the session is re-read."""
    guest_profile = {"name": "Khách", "age": 22}
    guest_meal = build_meal_record({"foods": [], "total_calories": 300})
    st.session_state.user_profile = guest_profile
    st.session_state.profile_completed = True
    st.session_state.meal_history = [guest_meal]

    fake_repo = FakeRepo()
    monkeypatch.setattr(
        repository, "SupabaseRepository", lambda client, user_id: fake_repo
    )
    import utils.auth as auth_module

    monkeypatch.setattr(auth_module, "get_client", lambda: SimpleNamespace(auth=object()))
    monkeypatch.setattr(auth_module, "ensure_account", lambda client_auth: "user-9")

    assert repository.enable_sync() == "user-9"
    assert fake_repo.saved_profiles == [guest_profile]
    assert fake_repo.saved_records == [guest_meal]


def test_enable_sync_skips_an_unsaved_profile(monkeypatch):
    st.session_state.user_profile = {"name": ""}
    st.session_state.profile_completed = False
    st.session_state.meal_history = []

    fake_repo = FakeRepo()
    monkeypatch.setattr(
        repository, "SupabaseRepository", lambda client, user_id: fake_repo
    )

    import utils.auth as auth_module

    monkeypatch.setattr(auth_module, "get_client", lambda: SimpleNamespace(auth=object()))
    monkeypatch.setattr(auth_module, "ensure_account", lambda client_auth: "user-9")

    repository.enable_sync()

    assert fake_repo.saved_profiles == []
    assert fake_repo.saved_records == []
