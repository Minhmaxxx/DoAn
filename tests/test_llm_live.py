"""Optional synthetic live check for the configured LLM provider and model."""

import os

import pytest

import config
from utils.llm import NutriLLM


BIOMETRICS = {
    "age": 22,
    "gender": "Nam",
    "height_cm": 170,
    "weight_kg": 65,
    "bmi": 22.5,
    "bmi_category": "Bình thường",
    "activity_level": "Vừa phải (3-5 ngày/tuần)",
    "tdee": 2492,
}
MEAL_DATA = {
    "foods": [
        {
            "emoji": "🥖",
            "display_name": "Bánh mì",
            "calories": 380,
            "portion_multiplier": 1.0,
            "portion_g": 200,
        }
    ],
    "total_calories": 380,
    "carbohydrate_g": 48,
    "protein_g": 18,
    "fat_g": 14,
    "fiber_g": 2.5,
}
GOAL_DATA = {
    "goal_name": "Giữ cân",
    "target_calories": 2492,
    "macro_targets": {
        "carbohydrate_g": 312,
        "protein_g": 156,
        "fat_g": 69,
    },
}


@pytest.mark.live
def test_selected_llm_model_live():
    if os.getenv("RUN_LIVE_LLM_TEST") != "1":
        pytest.skip("Đặt RUN_LIVE_LLM_TEST=1 để gọi API thật")

    key = config.OPENAI_API_KEY if config.LLM_PROVIDER == "openai" else config.GEMINI_API_KEY
    assert config.LLM_PROVIDER in {"google", "openai"}, "LLM_PROVIDER không hợp lệ"
    assert key, f"Thiếu API key cho provider {config.LLM_PROVIDER}"

    advice = NutriLLM(provider=config.LLM_PROVIDER).generate_advice(
        BIOMETRICS,
        MEAL_DATA,
        GOAL_DATA,
    )
    assert advice.strip()
    assert "Lỗi kết nối AI" not in advice
