"""Detector validation plus the real Baseline B core pipeline smoke test."""

import hashlib
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import streamlit as st
from PIL import Image

import config
from models.detector import Detection, FoodDetector, validate_model_artifact
from utils.history import build_meal_record
from utils.llm import NutriLLM, build_nutrition_prompt
from utils.nutrition import calculate_adjusted_nutrition, sum_meal_nutrition


ROOT_DIR = Path(__file__).resolve().parents[1]
POSITIVE_FIXTURE = (
    ROOT_DIR
    / "test_model"
    / "benchmark_common_v1"
    / "images"
    / "1002_jpg.rf.4de4b051a6630d45d1024bd6e112a996.jpg"
)
NEGATIVE_FIXTURE = (
    ROOT_DIR
    / "test_model"
    / "benchmark_common_v1"
    / "images"
    / "bg_002_jpg.rf.f428a7380f308f462b9418be9d579d54.jpg"
)


def test_detection_uses_canonical_display_contract():
    detection = Detection("pho", 0.92, (10, 20, 200, 300), raw_label="Pho")
    assert detection.display_name == "Phở"
    assert detection.raw_label == "Pho"


def test_missing_model_artifact_is_rejected(tmp_path):
    valid, message = validate_model_artifact(str(tmp_path / "missing.pt"))
    assert not valid
    assert "Không tìm thấy checkpoint" in message


def test_production_path_with_wrong_checksum_is_rejected(tmp_path, monkeypatch):
    artifact = tmp_path / "wrong.pt"
    artifact.write_bytes(b"not-the-benchmark-model")
    monkeypatch.setattr(config, "MODEL_PATH", artifact)
    validate_model_artifact.cache_clear()
    try:
        valid, message = validate_model_artifact(str(artifact))
    finally:
        validate_model_artifact.cache_clear()
    assert not valid
    assert "Checksum checkpoint không khớp" in message


def test_unknown_raw_model_label_is_not_silently_dropped(monkeypatch):
    box = SimpleNamespace(
        cls=np.array([0]),
        conf=np.array([0.9]),
        xyxy=np.array([[1.0, 2.0, 20.0, 30.0]]),
    )
    fake_model = SimpleNamespace(
        names={0: "Unsupported-label"},
        predict=lambda **kwargs: [SimpleNamespace(boxes=[box])],
    )
    detector = object.__new__(FoodDetector)
    detector.is_demo_mode = False
    detector.is_valid = True
    detector._model = fake_model
    errors = []
    monkeypatch.setattr(st, "error", errors.append)

    assert detector.detect(Image.new("RGB", (32, 32))) == []
    assert errors
    assert "Nhãn model chưa được ánh xạ" in errors[0]


@pytest.mark.model
def test_real_baseline_b_upload_to_history_pipeline():
    assert config.MODEL_PATH.exists(), f"Thiếu checkpoint release: {config.MODEL_PATH}"
    assert POSITIVE_FIXTURE.exists(), f"Thiếu fixture release: {POSITIVE_FIXTURE}"
    assert NEGATIVE_FIXTURE.exists(), f"Thiếu fixture release: {NEGATIVE_FIXTURE}"
    assert hashlib.sha256(POSITIVE_FIXTURE.read_bytes()).hexdigest() == (
        "07fb336590bd3a8e7209e13f90ebfdda04fb0b1e2f2f53f905e8179e56467c7d"
    )

    detector = FoodDetector()
    with Image.open(POSITIVE_FIXTURE) as source:
        detections = detector.detect(source.convert("RGB"))
    assert detections
    assert detections[0].food_class == "banh_mi"
    assert detections[0].confidence >= 0.60

    adjusted_items = [
        calculate_adjusted_nutrition(detection.food_class, 1.0)
        for detection in detections
    ]
    totals = sum_meal_nutrition(adjusted_items)
    meal_data = {"foods": adjusted_items, **totals, "total_calories": totals["calories"]}
    goal_data = {
        "goal_name": "Giữ cân",
        "target_calories": 2000,
        "macro_targets": {
            "carbohydrate_g": 250,
            "protein_g": 125,
            "fat_g": 56,
        },
    }
    biometrics = {
        "age": 22,
        "gender": "Nam",
        "height_cm": 170,
        "weight_kg": 65,
        "bmi": 22.5,
        "bmi_category": "Bình thường",
        "activity_level": "Vừa phải (3-5 ngày/tuần)",
        "tdee": 2492,
    }
    prompt = build_nutrition_prompt(biometrics, meal_data, goal_data)
    advice = NutriLLM(provider="google", google_api_key="").generate_advice(
        biometrics, meal_data, goal_data
    )
    record = build_meal_record(meal_data)

    assert totals["calories"] == 380.0
    assert "Bánh mì" in prompt
    assert "Đây là phân tích mẫu" in advice
    assert record["foods"][0]["display_name"] == "Bánh mì"

    with Image.open(NEGATIVE_FIXTURE) as source:
        assert detector.detect(source.convert("RGB")) == []
