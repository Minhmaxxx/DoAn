"""Cross-file contract checks for the deployed 12-class ontology."""

import json
from pathlib import Path

import yaml

import config
from training.data_collection import FOOD_QUERIES


ROOT_DIR = Path(__file__).resolve().parents[1]


def test_config_maps_are_bijective_and_complete():
    expected = set(config.FOOD_CLASSES)
    assert len(config.FOOD_CLASSES) == 12
    assert len(config.MODEL_CLASS_MAP) == 12
    assert list(config.MODEL_CLASS_MAP.values()) == config.FOOD_CLASSES
    assert set(config.FOOD_DISPLAY_NAMES) == expected
    assert set(config.FOOD_EMOJIS) == expected


def test_nutrition_database_matches_config():
    data = json.loads(config.NUTRITION_DB_PATH.read_text(encoding="utf-8"))
    foods = data["foods"]
    assert set(foods) == set(config.FOOD_CLASSES)
    assert data["sources"]

    for food_class, record in foods.items():
        assert record["display_name"] == config.FOOD_DISPLAY_NAMES[food_class]
        assert record["emoji"] == config.FOOD_EMOJIS[food_class]
        assert record["standard_portion_g"] > 0
        assert record["calories"] > 0
        assert all(value >= 0 for value in record["macros"].values())
        assert record["source_note"]


def test_training_yaml_and_collection_queries_use_same_classes():
    dataset = yaml.safe_load(
        (ROOT_DIR / "training" / "dataset.yaml").read_text(encoding="utf-8")
    )
    names = [dataset["names"][index] for index in range(dataset["nc"])]
    assert names == config.FOOD_CLASSES
    assert set(FOOD_QUERIES) == set(config.FOOD_CLASSES)


def test_google_model_is_environment_configurable_and_not_legacy():
    assert config.LLM_PROVIDER in {"google", "openai"}
    assert config.GOOGLE_MODEL
    assert config.GOOGLE_MODEL != "gemini-pro"
