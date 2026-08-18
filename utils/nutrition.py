"""
utils/nutrition.py — Nutrition calculation utilities
Computes BMI, BMR, TDEE, and calorie adjustments for user goals.
"""

from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path
from typing import Optional
import sys

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))
import config


# ─── Load Nutrition Database ─────────────────────────────────────────────────

@lru_cache(maxsize=1)
def load_nutrition_db() -> dict:
    """
    Load the nutrition database from JSON.

    Returns
    -------
    dict
        Full nutrition database keyed by food class name.
    """
    try:
        with open(config.NUTRITION_DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        foods = data["foods"]
        expected = set(config.FOOD_CLASSES)
        actual = set(foods)
        if actual != expected:
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            raise ValueError(f"Nutrition DB sai hợp đồng lớp; thiếu={missing}, thừa={extra}")
        return foods
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        raise ValueError(f"Lỗi đọc nutrition_db.json: {e}")


def get_food_nutrition(food_class: str) -> Optional[dict]:
    """
    Get nutrition data for a specific food class.

    Parameters
    ----------
    food_class : str
        Food class ID (e.g. 'pho')

    Returns
    -------
    dict or None
        Nutrition data dictionary if found, else None.
    """
    db = load_nutrition_db()
    return db.get(food_class)


def calculate_adjusted_nutrition(
    food_class: str,
    portion_multiplier: float,
) -> dict:
    """
    Calculate nutrition values adjusted by a portion multiplier (HITL slider).

    Parameters
    ----------
    food_class : str
        Food class ID.
    portion_multiplier : float
        Portion ratio from the HITL slider (e.g. 1.5 = 1.5x standard portion).

    Returns
    -------
    dict
        Adjusted nutrition values:
        {
            'calories': float,
            'carbohydrate_g': float,
            'protein_g': float,
            'fat_g': float,
            'fiber_g': float,
            'portion_g': float,
            'portion_label': str,
        }
    """
    food = get_food_nutrition(food_class)
    if food is None:
        raise KeyError(f"Không có dữ liệu dinh dưỡng cho lớp: {food_class}")

    macros = food["macros"]
    std_g = food["standard_portion_g"]

    return {
        "food_class": food_class,
        "display_name": food["display_name"],
        "emoji": food["emoji"],
        "calories": round(food["calories"] * portion_multiplier, 1),
        "carbohydrate_g": round(macros["carbohydrate_g"] * portion_multiplier, 1),
        "protein_g": round(macros["protein_g"] * portion_multiplier, 1),
        "fat_g": round(macros["fat_g"] * portion_multiplier, 1),
        "fiber_g": round(macros.get("fiber_g", 0) * portion_multiplier, 1),
        "portion_g": round(std_g * portion_multiplier, 0),
        "portion_multiplier": portion_multiplier,
        "standard_portion_label": food["standard_portion_label"],
    }


def sum_meal_nutrition(adjusted_items: list[dict]) -> dict:
    """
    Sum up nutrition values across all items in a meal.

    Parameters
    ----------
    adjusted_items : list[dict]
        List of adjusted nutrition dicts from calculate_adjusted_nutrition().

    Returns
    -------
    dict
        Total nutrition summary for the meal.
    """
    totals = {
        "calories": 0.0,
        "carbohydrate_g": 0.0,
        "protein_g": 0.0,
        "fat_g": 0.0,
        "fiber_g": 0.0,
    }
    for item in adjusted_items:
        for key in totals:
            totals[key] += item.get(key, 0.0)

    # Round all values
    return {k: round(v, 1) for k, v in totals.items()}


# ─── Body Metrics ─────────────────────────────────────────────────────────────

def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    """Calculate Body Mass Index."""
    height_m = height_cm / 100
    if height_m <= 0:
        return 0.0
    return round(weight_kg / (height_m ** 2), 1)


def classify_bmi(bmi: float) -> tuple[str, str]:
    """
    Classify BMI into category and return label with color.

    Returns
    -------
    tuple[str, str]
        (category_label, color_hex)
    """
    if bmi < 18.5:
        return "Thiếu cân", "#3498db"
    elif bmi < 23.0:
        return "Bình thường", "#2ecc71"
    elif bmi < 27.5:
        return "Thừa cân", "#f39c12"
    else:
        return "Béo phì", "#e74c3c"


def calculate_bmr(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
) -> float:
    """
    Calculate Basal Metabolic Rate using the Mifflin-St Jeor Equation.

    Parameters
    ----------
    weight_kg : float
    height_cm : float
    age : int
    gender : str
        'Nam' or 'Nữ'

    Returns
    -------
    float
        BMR in kcal/day.
    """
    bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age)
    if gender == "Nam":
        bmr += 5
    else:
        bmr -= 161
    return round(bmr, 0)


def calculate_tdee(bmr: float, activity_level: str) -> float:
    """
    Calculate Total Daily Energy Expenditure.

    Parameters
    ----------
    bmr : float
        Basal Metabolic Rate.
    activity_level : str
        One of: 'Ít vận động', 'Nhẹ nhàng', 'Vừa phải', 'Tích cực', 'Rất tích cực'

    Returns
    -------
    float
        TDEE in kcal/day.
    """
    multipliers = {
        "Ít vận động (ngồi nhiều)": 1.2,
        "Nhẹ nhàng (1-3 ngày/tuần)": 1.375,
        "Vừa phải (3-5 ngày/tuần)": 1.55,
        "Tích cực (6-7 ngày/tuần)": 1.725,
        "Rất tích cực (vận động viên)": 1.9,
    }
    factor = multipliers.get(activity_level, 1.2)
    return round(bmr * factor, 0)


def calculate_goal_calories(tdee: float, goal: str) -> dict:
    """
    Calculate recommended daily calories based on health goal.

    Returns
    -------
    dict with keys: target_calories, calorie_change, description
    """
    goals = {
        "Giảm cân": {
            "change": -500,
            "description": "Thâm hụt 500 kcal/ngày → giảm ~0.5kg/tuần",
        },
        "Giữ cân": {
            "change": 0,
            "description": "Duy trì cân nặng hiện tại",
        },
        "Tăng cơ": {
            "change": 300,
            "description": "Dư 300 kcal/ngày → tăng cơ từ từ",
        },
        "Tăng cân": {
            "change": 500,
            "description": "Dư 500 kcal/ngày → tăng cân hiệu quả",
        },
    }
    info = goals.get(goal, {"change": 0, "description": "Giữ nguyên"})
    target = max(1200, tdee + info["change"])  # Safety minimum 1200 kcal
    return {
        "target_calories": round(target, 0),
        "calorie_change": info["change"],
        "description": info["description"],
    }


def get_macro_targets(target_calories: float, goal: str) -> dict:
    """
    Recommend macronutrient targets based on goal calories.

    Returns macro targets in grams.
    """
    ratios = {
        "Giảm cân":       {"carb": 0.40, "protein": 0.35, "fat": 0.25},
        "Giữ cân":        {"carb": 0.50, "protein": 0.25, "fat": 0.25},
        "Tăng cơ":        {"carb": 0.45, "protein": 0.35, "fat": 0.20},
        "Tăng cân":       {"carb": 0.50, "protein": 0.25, "fat": 0.25},
    }
    r = ratios.get(goal, ratios["Giữ cân"])
    return {
        "carbohydrate_g": round(target_calories * r["carb"] / 4, 0),  # 4 kcal/g
        "protein_g":      round(target_calories * r["protein"] / 4, 0),
        "fat_g":          round(target_calories * r["fat"] / 9, 0),   # 9 kcal/g
    }
