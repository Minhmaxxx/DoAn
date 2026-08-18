"""LLM adapter tests that never call an external API."""

from types import SimpleNamespace

import config
from utils.llm import NutriLLM, SYSTEM_PROMPT, build_nutrition_prompt


BIOMETRICS = {
    "name": "Không gửi tên này",
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


class FakeGoogleModels:
    def __init__(self):
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(("generate", kwargs))
        return SimpleNamespace(text="Tư vấn Google")

    def generate_content_stream(self, **kwargs):
        self.calls.append(("stream", kwargs))
        return iter(
            [SimpleNamespace(text="Tư vấn "), SimpleNamespace(text="theo luồng")]
        )


def test_prompt_contains_required_context_but_not_profile_name():
    prompt = build_nutrition_prompt(BIOMETRICS, MEAL_DATA, GOAL_DATA)
    assert "Bánh mì" in prompt
    assert "2492" in prompt
    assert "Giữ cân" in prompt
    assert BIOMETRICS["name"] not in prompt


def test_prompt_and_demo_handle_zero_target_without_division_error():
    zero_goal = {**GOAL_DATA, "target_calories": 0}
    prompt = build_nutrition_prompt(BIOMETRICS, MEAL_DATA, zero_goal)
    advice = NutriLLM(provider="google", google_api_key="")._demo_advice(
        MEAL_DATA, zero_goal
    )
    assert "Mục tiêu calo/ngày" in prompt
    assert "Đây là phân tích mẫu" in advice


def test_missing_key_returns_clearly_labeled_sample_advice():
    llm = NutriLLM(provider="google", google_api_key="")
    advice = llm.generate_advice(BIOMETRICS, MEAL_DATA, GOAL_DATA)
    assert "Đây là phân tích mẫu" in advice


def test_google_non_streaming_uses_configured_model_and_system_prompt(monkeypatch):
    models = FakeGoogleModels()
    client = SimpleNamespace(models=models)
    llm = NutriLLM(provider="google", google_api_key="test-key")
    monkeypatch.setattr(llm, "_get_google", lambda: client)

    assert llm.generate_advice(BIOMETRICS, MEAL_DATA, GOAL_DATA) == "Tư vấn Google"
    call_type, kwargs = models.calls[0]
    assert call_type == "generate"
    assert kwargs["model"] == config.GOOGLE_MODEL
    assert kwargs["config"]["system_instruction"] == SYSTEM_PROMPT
    assert "Bánh mì" in kwargs["contents"]


def test_google_streaming_yields_text_chunks(monkeypatch):
    models = FakeGoogleModels()
    client = SimpleNamespace(models=models)
    llm = NutriLLM(provider="google", google_api_key="test-key")
    monkeypatch.setattr(llm, "_get_google", lambda: client)

    chunks = list(llm.stream_advice(BIOMETRICS, MEAL_DATA, GOAL_DATA))
    assert chunks == ["Tư vấn ", "theo luồng"]
    assert models.calls[0][0] == "stream"


def test_openai_non_streaming_adapter_uses_configured_model(monkeypatch):
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        message = SimpleNamespace(content="Tư vấn OpenAI")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    llm = NutriLLM(provider="openai", openai_api_key="test-key")
    monkeypatch.setattr(llm, "_get_openai", lambda: client)

    assert llm.generate_advice(BIOMETRICS, MEAL_DATA, GOAL_DATA) == "Tư vấn OpenAI"
    assert calls[0]["model"] == config.OPENAI_MODEL
    assert calls[0]["messages"][0]["content"] == SYSTEM_PROMPT


def test_openai_client_uses_bounded_timeout_and_retries(monkeypatch):
    captured = {}
    fake_client = SimpleNamespace(close=lambda: None)

    def create_client(**kwargs):
        captured.update(kwargs)
        return fake_client

    monkeypatch.setattr("openai.OpenAI", create_client)
    llm = NutriLLM(provider="openai", openai_api_key="test-key")

    assert llm._get_openai() is fake_client
    assert captured["timeout"] == config.LLM_TIMEOUT_SECONDS
    assert captured["max_retries"] == config.LLM_MAX_RETRIES


def test_connection_error_does_not_expose_exception_or_key(monkeypatch):
    secret = "AIza-secret-value"
    llm = NutriLLM(provider="google", google_api_key=secret)

    def fail():
        raise RuntimeError(f"request failed with {secret}")

    monkeypatch.setattr(llm, "_get_google", fail)
    advice = llm.generate_advice(BIOMETRICS, MEAL_DATA, GOAL_DATA)
    assert "Lỗi kết nối AI" in advice
    assert secret not in advice
    assert "RuntimeError" not in advice


def test_unknown_provider_reports_configuration_error():
    llm = NutriLLM(provider="unknown", google_api_key="test-key")
    advice = llm.generate_advice(BIOMETRICS, MEAL_DATA, GOAL_DATA)
    assert "Cấu hình LLM không hợp lệ" in advice


def test_provider_configuration_is_key_specific():
    assert NutriLLM(provider="google", google_api_key="key").is_configured()
    assert NutriLLM(provider="openai", openai_api_key="key").is_configured()
    assert not NutriLLM(provider="openai", openai_api_key="").is_configured()
