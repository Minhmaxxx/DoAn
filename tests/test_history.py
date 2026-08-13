"""Session-history record and ordering tests."""

from datetime import datetime

import pytest

from utils.history import build_meal_record, guess_meal_type, sort_meal_history


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

    assert record["timestamp"] == "2026-08-09T12:34:56"
    assert record["date"] == "2026-08-09"
    assert record["time"] == "12:34"
    assert record["meal_type"] == "Bữa trưa"
    assert record["totals"]["calories"] == 380
    assert "private_internal_field" not in record["foods"][0]


def test_sort_history_is_newest_first_without_mutation():
    records = [
        {"timestamp": "2026-08-08T10:00:00"},
        {"timestamp": "2026-08-09T10:00:00"},
    ]
    result = sort_meal_history(records)
    assert result[0]["timestamp"] == "2026-08-09T10:00:00"
    assert records[0]["timestamp"] == "2026-08-08T10:00:00"
