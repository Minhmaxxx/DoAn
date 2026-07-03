"""Test script to validate all project imports and core logic."""
import sys
sys.path.insert(0, '.')

print("Testing imports...")

try:
    import config
    print("  [OK] config.py")
except Exception as e:
    print(f"  [FAIL] config.py: {e}")

try:
    from utils.nutrition import calculate_bmi, calculate_bmr, calculate_tdee, calculate_goal_calories
    bmi = calculate_bmi(65, 170)
    bmr = calculate_bmr(65, 170, 22, "Nam")
    tdee = calculate_tdee(bmr, "Vua phai (3-5 ngay/tuan)")
    goal = calculate_goal_calories(tdee, "Giam can")
    print("  [OK] utils/nutrition.py")
    print(f"       BMI={bmi}, BMR={bmr}, TDEE={tdee}, Target={goal['target_calories']}")
except Exception as e:
    print(f"  [FAIL] utils/nutrition.py: {e}")

try:
    from utils.nutrition import load_nutrition_db, calculate_adjusted_nutrition
    db = load_nutrition_db()
    print(f"  [OK] nutrition_db.json -- {len(db)} foods loaded")
    print(f"       Foods: {list(db.keys())}")
    adj = calculate_adjusted_nutrition("pho_bo", 1.5)
    print(f"  [OK] HITL calc -- pho_bo 1.5x = {adj['calories']} kcal")
except Exception as e:
    print(f"  [FAIL] nutrition_db: {e}")

try:
    from utils.llm import NutriLLM
    llm = NutriLLM()
    print(f"  [OK] utils/llm.py -- provider={llm.provider}, configured={llm.is_configured()}")
    # Test demo advice
    demo = llm._demo_advice({"total_calories": 425}, {"target_calories": 2000})
    print(f"  [OK] Demo advice generated ({len(demo)} chars)")
except Exception as e:
    print(f"  [FAIL] utils/llm.py: {e}")

try:
    from utils.visualization import macro_donut_chart, calorie_gauge
    fig1 = macro_donut_chart(52, 28, 10)
    fig2 = calorie_gauge(425, 2000)
    print("  [OK] utils/visualization.py -- charts created")
except Exception as e:
    print(f"  [FAIL] utils/visualization.py: {e}")

try:
    from models.detector import FoodDetector, Detection
    det = Detection("pho_bo", 0.92, (10, 20, 200, 300))
    print(f"  [OK] models/detector.py -- Detection: {det}")
except Exception as e:
    print(f"  [FAIL] models/detector.py: {e}")

print()
print("=" * 50)
print("All imports tested!")
