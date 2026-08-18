"""Pure helpers for session-scoped meal history."""

from __future__ import annotations

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
