# utils/__init__.py
from .nutrition import (
    load_nutrition_db,
    get_food_nutrition,
    calculate_adjusted_nutrition,
    sum_meal_nutrition,
    calculate_bmi,
    classify_bmi,
    calculate_bmr,
    calculate_tdee,
    calculate_goal_calories,
    get_macro_targets,
)
from .llm import NutriLLM
from .visualization import (
    macro_donut_chart,
    calorie_gauge,
    daily_calorie_chart,
    macro_progress_bars,
)

__all__ = [
    "load_nutrition_db", "get_food_nutrition", "calculate_adjusted_nutrition",
    "sum_meal_nutrition", "calculate_bmi", "classify_bmi", "calculate_bmr",
    "calculate_tdee", "calculate_goal_calories", "get_macro_targets",
    "NutriLLM",
    "macro_donut_chart", "calorie_gauge", "daily_calorie_chart", "macro_progress_bars",
]
