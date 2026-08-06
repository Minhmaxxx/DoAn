"""Smoke-check imports and the core 12-class data contract."""

import sys

sys.path.insert(0, ".")

failures = []


def check(name, callback):
    try:
        detail = callback()
        print(f"  [OK] {name}{f' - {detail}' if detail else ''}")
    except Exception as error:
        failures.append(name)
        print(f"  [FAIL] {name}: {error}")


print("Testing imports and contracts...")


def check_config():
    import config

    assert len(config.FOOD_CLASSES) == 12
    assert list(config.MODEL_CLASS_MAP.values()) == config.FOOD_CLASSES
    assert set(config.FOOD_DISPLAY_NAMES) == set(config.FOOD_CLASSES)
    assert set(config.FOOD_EMOJIS) == set(config.FOOD_CLASSES)
    return "12 canonical classes"


def check_nutrition():
    from utils.nutrition import (
        calculate_adjusted_nutrition,
        calculate_bmi,
        calculate_bmr,
        calculate_goal_calories,
        calculate_tdee,
        load_nutrition_db,
    )

    database = load_nutrition_db()
    assert len(database) == 12
    assert calculate_bmi(65, 170) == 22.5
    bmr = calculate_bmr(65, 170, 22, "Nam")
    tdee = calculate_tdee(bmr, "Vừa phải (3-5 ngày/tuần)")
    goal = calculate_goal_calories(tdee, "Giảm cân")
    assert tdee > bmr
    assert goal["calorie_change"] == -500
    assert calculate_adjusted_nutrition("banh_xeo", 1.0)["calories"] == 580
    return "12 foods, accented lookup keys"


def check_llm():
    from utils.llm import NutriLLM

    advice = NutriLLM(gemini_api_key="", openai_api_key="")._demo_advice(
        {"total_calories": 425},
        {"target_calories": 2000},
    )
    assert advice
    return "sample advice"


def check_visualization():
    from utils.visualization import calorie_gauge, macro_donut_chart

    assert macro_donut_chart(52, 28, 10) is not None
    assert calorie_gauge(425, 2000) is not None
    return "charts created"


def check_detector():
    import config
    from models.detector import Detection, validate_model_artifact

    detection = Detection("pho", 0.92, (10, 20, 200, 300), raw_label="Pho")
    assert detection.display_name == "Phở"
    valid, detail = validate_model_artifact(str(config.MODEL_PATH))
    assert valid, detail
    return f"{config.MODEL_NAME} checksum valid"


check("config.py", check_config)
check("utils/nutrition.py", check_nutrition)
check("utils/llm.py", check_llm)
check("utils/visualization.py", check_visualization)
check("models/detector.py", check_detector)

if failures:
    print(f"\nSmoke check failed: {', '.join(failures)}")
    raise SystemExit(1)

print("\nAll smoke checks passed.")
