"""
config.py — Global configuration for NutriVision
Hệ thống Trợ lý Tư vấn Dinh dưỡng Cá nhân hóa
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

# ─── Directory Paths ────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"
MODELS_DIR = ROOT_DIR / "models" / "weights"
ASSETS_DIR = ROOT_DIR / "assets"

# Important file paths
NUTRITION_DB_PATH = DATA_DIR / "nutrition_db.json"
MEAL_HISTORY_PATH = DATA_DIR / "meal_history.json"
MODEL_PATH = MODELS_DIR / "best.pt"

# ─── LLM Settings ────────────────────────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")  # 'gemini' or 'openai'
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

GEMINI_MODEL = "gemini-pro"
OPENAI_MODEL = "gpt-4o-mini"
LLM_MAX_TOKENS = 1024
LLM_TEMPERATURE = 0.7

# ─── YOLOv8 Inference Settings ───────────────────────────────────────────────
YOLO_CONF_THRESHOLD = 0.45  # Minimum confidence to accept a detection
YOLO_IOU_THRESHOLD = 0.45   # IOU threshold for Non-Maximum Suppression
YOLO_IMG_SIZE = 640          # Input resolution for YOLOv8

# ─── HITL Slider Settings ────────────────────────────────────────────────────
SLIDER_MIN = 0.25    # Minimum portion ratio (quarter portion)
SLIDER_MAX = 3.0     # Maximum portion ratio (triple portion)
SLIDER_DEFAULT = 1.0 # Default = 1 standard portion
SLIDER_STEP = 0.25   # Increment step

# ─── Streamlit UI ────────────────────────────────────────────────────────────
APP_TITLE = " NutriVision — Trợ lý Dinh dưỡng Thông minh"
APP_ICON = ""
APP_LAYOUT = "wide"

# ─── Supported Food Classes (must match YOLOv8 label names) ──────────────────
FOOD_CLASSES = [
    "pho_bo",
    "bun_bo_hue",
    "bun_cha",
    "com_tam",
    "banh_mi",
    "goi_cuon",
    "nem_ran",
    "banh_cuon",
    "chao_long",
    "xoi_ga",
]

# Human-readable Vietnamese names
FOOD_DISPLAY_NAMES = {
    "pho_bo":     "Phở bò",
    "bun_bo_hue": "Bún bò Huế",
    "bun_cha":    "Bún chả",
    "com_tam":    "Cơm tấm sườn",
    "banh_mi":    "Bánh mì",
    "goi_cuon":   "Gỏi cuốn",
    "nem_ran":    "Nem rán",
    "banh_cuon":  "Bánh cuốn",
    "chao_long":  "Cháo lòng",
    "xoi_ga":     "Xôi gà",
}

# Emoji for each food (for UI display)
FOOD_EMOJIS = {
    "pho_bo":     "",
    "bun_bo_hue": "",
    "bun_cha":    "",
    "com_tam":    "",
    "banh_mi":    "",
    "goi_cuon":   "",
    "nem_ran":    "",
    "banh_cuon":  "",
    "chao_long":  "",
    "xoi_ga":     "",
}
