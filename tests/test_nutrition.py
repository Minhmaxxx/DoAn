"""Assertions for biometric and meal nutrition calculations."""

import pytest

from utils.nutrition import (
    calculate_adjusted_nutrition,
    calculate_bmi,
    calculate_bmr,
    calculate_goal_calories,
    calculate_tdee,
    classify_bmi,
    get_macro_targets,
    sum_meal_nutrition,
)


def test_bmi_calculation_and_invalid_height():
    assert calculate_bmi(65, 170) == 22.5
    assert calculate_bmi(65, 0) == 0.0


@pytest.mark.parametrize(
    ("bmi", "category"),
    [
        (18.4, "Thiếu cân"),
        (18.5, "Bình thường"),
        (22.9, "Bình thường"),
        (23.0, "Thừa cân"),
        (27.5, "Béo phì"),
    ],
)
def test_bmi_category_boundaries(bmi, category):
    assert classify_bmi(bmi)[0] == category


def test_bmr_uses_gender_specific_mifflin_st_jeor_offset():
    assert calculate_bmr(65, 170, 22, "Nam") == 1608
    assert calculate_bmr(65, 170, 22, "Nữ") == 1442


@pytest.mark.parametrize(
    ("activity", "factor"),
    [
        ("Ít vận động (ngồi nhiều)", 1.2),
        ("Nhẹ nhàng (1-3 ngày/tuần)", 1.375),
        ("Vừa phải (3-5 ngày/tuần)", 1.55),
        ("Tích cực (6-7 ngày/tuần)", 1.725),
        ("Rất tích cực (vận động viên)", 1.9),
    ],
)
def test_tdee_activity_lookup_contract(activity, factor):
    assert calculate_tdee(1600, activity) == round(1600 * factor, 0)


@pytest.mark.parametrize(
    ("goal", "change"),
    [
        ("Giảm cân", -500),
        ("Giảm cân nhanh", -750),
        ("Giữ cân", 0),
        ("Tăng cơ", 300),
        ("Tăng cân", 500),
    ],
)
def test_goal_calorie_adjustments(goal, change):
    result = calculate_goal_calories(2000, goal)
    assert result["target_calories"] == max(1200, 2000 + change)
    assert result["calorie_change"] == change


def test_goal_calories_respect_safety_floor():
    assert calculate_goal_calories(1300, "Giảm cân")["target_calories"] == 1200


@pytest.mark.parametrize(
    ("multiplier", "calories"),
    [(0.25, 145.0), (1.0, 580.0), (3.0, 1740.0)],
)
def test_hitl_portion_scales_linearly(multiplier, calories):
    adjusted = calculate_adjusted_nutrition("banh_xeo", multiplier)
    assert adjusted["calories"] == calories
    assert adjusted["portion_multiplier"] == multiplier


def test_duplicate_detections_are_summed_independently():
    item = calculate_adjusted_nutrition("banh_xeo", 1.0)
    totals = sum_meal_nutrition([item, item])
    assert totals["calories"] == 1160.0
    assert totals["protein_g"] == 48.0


def test_unknown_food_has_no_silent_nutrition_fallback():
    with pytest.raises(KeyError, match="Không có dữ liệu dinh dưỡng"):
        calculate_adjusted_nutrition("unknown_food", 1.0)


def test_macro_targets_reconstruct_target_calories():
    targets = get_macro_targets(2000, "Tăng cơ")
    reconstructed = (
        targets["carbohydrate_g"] * 4
        + targets["protein_g"] * 4
        + targets["fat_g"] * 9
    )
    assert reconstructed == pytest.approx(2000, abs=8)
