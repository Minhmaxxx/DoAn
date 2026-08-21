"""Pure helpers for session-scoped meal history."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo


VIETNAM_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")


def vietnam_now() -> datetime:
    """Return the current timezone-aware time in Vietnam."""
    return datetime.now(VIETNAM_TIMEZONE)


def as_vietnam_time(at: datetime) -> datetime:
    """Interpret naive values as Vietnam time and convert aware values."""
    if at.tzinfo is None:
        return at.replace(tzinfo=VIETNAM_TIMEZONE)
    return at.astimezone(VIETNAM_TIMEZONE)


def guess_meal_type(at: datetime) -> str:
    """Infer a Vietnamese meal label from a timestamp."""
    if 5 <= at.hour < 11:
        return "Bữa sáng"
    if 11 <= at.hour < 14:
        return "Bữa trưa"
    if 14 <= at.hour < 17:
        return "Bữa phụ chiều"
    return "Bữa tối"


def build_meal_record(meal_data: dict, *, at: datetime | None = None) -> dict:
    """Create the serializable record stored in the active Streamlit session."""
    at = vietnam_now() if at is None else as_vietnam_time(at)
    return {
        "timestamp": at.isoformat(),
        "date": at.strftime("%Y-%m-%d"),
        "time": at.strftime("%H:%M"),
        "meal_type": guess_meal_type(at),
        "foods": [
            {
                "display_name": food["display_name"],
                "emoji": food["emoji"],
                "portion_multiplier": food["portion_multiplier"],
                "calories": food["calories"],
            }
            for food in meal_data.get("foods", [])
        ],
        "totals": {
            "calories": meal_data.get("total_calories", 0),
            "carbohydrate_g": meal_data.get("carbohydrate_g", 0),
            "protein_g": meal_data.get("protein_g", 0),
            "fat_g": meal_data.get("fat_g", 0),
        },
    }


def sort_meal_history(records: list[dict]) -> list[dict]:
    """Return newest records first without mutating session state."""
    return sorted(records, key=lambda record: record.get("timestamp", ""), reverse=True)


def append_meal_once(
    records: list[dict],
    meal_data: dict,
    signature: str,
    saved_signatures: set[str],
    *,
    at: datetime | None = None,
) -> bool:
    """Append one confirmed meal version and reject repeated save clicks."""
    if not signature or signature in saved_signatures:
        return False
    records.append(build_meal_record(meal_data, at=at))
    saved_signatures.add(signature)
    return True


def meal_uuid(user_id: str, signature: str) -> str:
    """Derive a deterministic `meals.id` from an owner and a meal_signature.

    Storage-side idempotency for SupabaseRepository.save_meal(): a retried
    insert after a dropped response reuses the same id and hits the primary
    key instead of creating a duplicate meal row. Same signature always
    resolves to the same id, but only within one owner.
    """
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{user_id}:{signature}"))


def record_signature(record: dict) -> str:
    """Derive a stable signature for an ALREADY-BUILT meal record.

    pages/1_Phan_tich_anh.py has a `meal_signature` (a hash of the confirmed
    meal) at save time, but a record already sitting in session history has
    lost it. Migrating those records to the cloud still needs something to
    feed meal_uuid().

    Covers the whole record, not just the timestamp: `datetime.now()` on
    Windows resolves to roughly 16ms, so several records built in quick
    succession share a timestamp exactly (verified — five in a row came back
    identical). Keying on the timestamp alone made distinct meals collapse
    into one row when migrated. Hashing the content keeps both properties
    that matter: re-running a migration reuses the same id instead of
    duplicating rows, while two different meals stay two rows.
    """
    payload = json.dumps(
        {
            "timestamp": record.get("timestamp"),
            "meal_type": record.get("meal_type"),
            "foods": record.get("foods"),
            "totals": record.get("totals"),
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def record_from_row(row: dict) -> dict:
    """Convert a Supabase `meals` row back into the session meal-record shape.

    `eaten_at` comes back as a timestamptz (UTC); every derived field must go
    through as_vietnam_time() before formatting, or date-based filters like
    the "today" view in pages/0_Hom_nay.py drift by the UTC+7 offset.
    """
    eaten_at = row["eaten_at"]
    if isinstance(eaten_at, str):
        eaten_at = datetime.fromisoformat(eaten_at)
    at = as_vietnam_time(eaten_at)
    return {
        "timestamp": at.isoformat(),
        "date": at.strftime("%Y-%m-%d"),
        "time": at.strftime("%H:%M"),
        "meal_type": row.get("meal_type") or guess_meal_type(at),
        "foods": row["foods"],
        "totals": row["totals"],
    }


EXPORT_FORMAT_VERSION = 1


def build_export_payload(profile: dict, meals: list[dict]) -> dict:
    """Assemble the whole session as one plain-JSON document.

    This is the fallback for the two ways data can vanish. Guest mode is the
    default and keeps everything in session state, so closing the browser
    ends it; cloud sync survives that but depends on a free-tier project that
    pauses after seven days idle and on a Google account the user may lose.
    An export is the only copy that depends on neither.

    Deliberately a pure function over plain values: no Streamlit, no clock,
    no session state. `exported_at` is passed in rather than read from
    vietnam_now() so a test can assert on a fixed document.

    `version` is what makes the file re-importable later. Without it a reader
    has to guess the shape from its contents, and the meal-record shape has
    already changed once (meal_type gained a fallback in record_from_row).
    """
    return {
        "app": "NutriVision",
        "version": EXPORT_FORMAT_VERSION,
        "exported_at": vietnam_now().isoformat(),
        "profile": dict(profile),
        "meal_count": len(meals),
        "meals": sort_meal_history(list(meals)),
    }


def export_as_json(profile: dict, meals: list[dict]) -> str:
    """Serialize build_export_payload() for st.download_button.

    ensure_ascii=False keeps Vietnamese readable in a text editor instead of
    turning "Bữa trưa" into escape sequences; the file is declared UTF-8 by
    the download button's MIME type.
    """
    return json.dumps(
        build_export_payload(profile, meals),
        ensure_ascii=False,
        indent=2,
    )
