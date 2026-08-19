"""Session-history record and ordering tests."""

from datetime import datetime, timezone

import pytest

from utils.history import (
    append_meal_once,
    build_meal_record,
    guess_meal_type,
    meal_uuid,
    record_from_row,
    record_signature,
    sort_meal_history,
)


@pytest.mark.parametrize(
    ("hour", "meal_type"),
    [
        (5, "Bữa sáng"),
        (10, "Bữa sáng"),
        (11, "Bữa trưa"),
        (14, "Bữa phụ chiều"),
        (17, "Bữa tối"),
        (2, "Bữa tối"),
    ],
)
def test_meal_type_boundaries(hour, meal_type):
    assert guess_meal_type(datetime(2026, 8, 9, hour, 0)) == meal_type


def test_build_meal_record_keeps_only_history_contract_fields():
    meal = {
        "foods": [
            {
                "display_name": "Bánh mì",
                "emoji": "🥖",
                "portion_multiplier": 1.0,
                "calories": 380,
                "private_internal_field": "must-not-persist",
            }
        ],
        "total_calories": 380,
        "carbohydrate_g": 48,
        "protein_g": 18,
        "fat_g": 14,
    }
    at = datetime(2026, 8, 9, 12, 34, 56)
    record = build_meal_record(meal, at=at)

    assert record["timestamp"] == "2026-08-09T12:34:56+07:00"
    assert record["date"] == "2026-08-09"
    assert record["time"] == "12:34"
    assert record["meal_type"] == "Bữa trưa"
    assert record["totals"]["calories"] == 380
    assert "private_internal_field" not in record["foods"][0]


def test_build_meal_record_converts_utc_to_vietnam_time():
    record = build_meal_record(
        {"foods": [], "total_calories": 0},
        at=datetime(2026, 8, 9, 18, 30, tzinfo=timezone.utc),
    )
    assert record["date"] == "2026-08-10"
    assert record["time"] == "01:30"
    assert record["timestamp"].endswith("+07:00")


def test_sort_history_is_newest_first_without_mutation():
    records = [
        {"timestamp": "2026-08-08T10:00:00"},
        {"timestamp": "2026-08-09T10:00:00"},
    ]
    result = sort_meal_history(records)
    assert result[0]["timestamp"] == "2026-08-09T10:00:00"
    assert records[0]["timestamp"] == "2026-08-08T10:00:00"


def test_append_meal_once_rejects_repeated_signature():
    records = []
    signatures = set()
    meal = {"foods": [], "total_calories": 0}
    at = datetime(2026, 8, 9, 12, 0)

    assert append_meal_once(records, meal, "meal-v1", signatures, at=at)
    assert not append_meal_once(records, meal, "meal-v1", signatures, at=at)
    assert len(records) == 1


def test_meal_uuid_is_deterministic_and_scoped_per_owner():
    first = meal_uuid("user-a", "meal-v1")
    again = meal_uuid("user-a", "meal-v1")
    other_user = meal_uuid("user-b", "meal-v1")
    other_signature = meal_uuid("user-a", "meal-v2")

    assert first == again
    assert first != other_user
    assert first != other_signature


def test_record_from_row_converts_utc_row_to_vietnam_time():
    row = {
        "eaten_at": "2026-08-09T18:30:00+00:00",
        "meal_type": "Bữa tối",
        "foods": [
            {
                "display_name": "Bánh mì",
                "emoji": "🥖",
                "portion_multiplier": 1.0,
                "calories": 380,
            }
        ],
        "totals": {"calories": 380, "carbohydrate_g": 48, "protein_g": 18, "fat_g": 14},
    }
    record = record_from_row(row)

    assert record["date"] == "2026-08-10"
    assert record["time"] == "01:30"
    assert record["timestamp"].endswith("+07:00")
    assert record["meal_type"] == "Bữa tối"
    assert record["foods"] == row["foods"]
    assert record["totals"] == row["totals"]


def test_record_from_row_guesses_meal_type_when_missing():
    row = {
        "eaten_at": "2026-08-09T12:00:00+07:00",
        "foods": [],
        "totals": {"calories": 0, "carbohydrate_g": 0, "protein_g": 0, "fat_g": 0},
    }
    record = record_from_row(row)
    assert record["meal_type"] == "Bữa trưa"


def test_build_meal_record_and_record_from_row_agree_on_shape():
    """A record saved then reloaded from storage must match the session shape
    exactly, since pages/2_Lich_su.py renders both without branching."""
    built = build_meal_record(
        {"foods": [], "total_calories": 0},
        at=datetime(2026, 8, 9, 12, 0),
    )
    row = {
        "eaten_at": built["timestamp"],
        "meal_type": built["meal_type"],
        "foods": built["foods"],
        "totals": built["totals"],
    }
    assert record_from_row(row) == built


def test_record_signature_separates_meals_that_share_a_timestamp():
    """Regression: `datetime.now()` on Windows resolves to ~16ms, so records
    built back to back carry an identical timestamp. Keying only on that made
    two distinct meals collapse into one row when migrated to the cloud."""
    at = datetime(2026, 8, 9, 12, 0)
    first = build_meal_record({"foods": [], "total_calories": 400}, at=at)
    second = build_meal_record({"foods": [], "total_calories": 700}, at=at)

    assert first["timestamp"] == second["timestamp"]
    assert record_signature(first) != record_signature(second)


def test_record_signature_is_stable_across_calls():
    """Re-running a migration must reuse the same id rather than duplicate."""
    record = build_meal_record(
        {"foods": [], "total_calories": 400}, at=datetime(2026, 8, 9, 12, 0)
    )
    assert record_signature(record) == record_signature(dict(record))
