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
MODEL_PATH = MODELS_DIR / "best_baseline_B.pt"
MODEL_NAME = "Baseline B"
MODEL_SHA256 = "18b8f1dd160a4b6df6ae0f4dc31d00ec729722daefafdc50422dc9e36d845998"
ENABLE_RANDOM_DEMO = os.getenv("ENABLE_RANDOM_DEMO", "false").lower() == "true"

# ─── LLM Settings ────────────────────────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "google").strip().lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "gemini-3.5-flash").strip() or "gemini-3.5-flash"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
LLM_MAX_TOKENS = 1024
LLM_TEMPERATURE = 0.7

# ─── YOLOv8 Inference Settings ───────────────────────────────────────────────
YOLO_CONF_THRESHOLD = 0.45  # Minimum confidence to accept a detection
YOLO_IOU_THRESHOLD = 0.45   # IOU threshold for Non-Maximum Suppression
YOLO_IMG_SIZE = 640          # Input resolution for YOLOv8
MAX_UPLOAD_SIZE_MB = 20
MAX_IMAGE_PIXELS = 25_000_000
MAX_IMAGE_DIMENSION = 5000

# ─── HITL Slider Settings ────────────────────────────────────────────────────
SLIDER_MIN = 0.25    # Minimum portion ratio (quarter portion)
SLIDER_MAX = 3.0     # Maximum portion ratio (triple portion)
SLIDER_DEFAULT = 1.0 # Default = 1 standard portion
SLIDER_STEP = 0.25   # Increment step

# ─── Streamlit UI ────────────────────────────────────────────────────────────
APP_TITLE = "NutriVision - Trợ lý Dinh dưỡng Thông minh"
APP_ICON = ""
APP_LAYOUT = "wide"

# ─── Model label contract ────────────────────────────────────────────────────
MODEL_CLASS_MAP = {
    "Banh-mi": "banh_mi",
    "Banh-trang-nuong": "banh_trang_nuong",
    "Banh-xeo": "banh_xeo",
    "Bun-bo-Hue": "bun_bo_hue",
    "Bun-dau-mam-tom": "bun_dau_mam_tom",
    "Bun-rieu": "bun_rieu",
    "Bun-thit-nuong": "bun_thit_nuong",
    "Chao-long": "chao_long",
    "Com-tam": "com_tam",
    "Goi-cuon": "goi_cuon",
    "Pho": "pho",
    "Xoi": "xoi",
}

FOOD_CLASSES = [
    "banh_mi",
    "banh_trang_nuong",
    "banh_xeo",
    "bun_bo_hue",
    "bun_dau_mam_tom",
    "bun_rieu",
    "bun_thit_nuong",
    "chao_long",
    "com_tam",
    "goi_cuon",
    "pho",
    "xoi",
]

# Human-readable Vietnamese names
FOOD_DISPLAY_NAMES = {
    "banh_mi": "Bánh mì",
    "banh_trang_nuong": "Bánh tráng nướng",
    "banh_xeo": "Bánh xèo",
    "bun_bo_hue": "Bún bò Huế",
    "bun_dau_mam_tom": "Bún đậu mắm tôm",
    "bun_rieu": "Bún riêu",
    "bun_thit_nuong": "Bún thịt nướng",
    "chao_long": "Cháo lòng",
    "com_tam": "Cơm tấm",
    "goi_cuon": "Gỏi cuốn",
    "pho": "Phở",
    "xoi": "Xôi",
}

FOOD_EMOJIS = {
    "banh_mi": "🥖",
    "banh_trang_nuong": "🍕",
    "banh_xeo": "🥞",
    "bun_bo_hue": "🍜",
    "bun_dau_mam_tom": "🍱",
    "bun_rieu": "🍜",
    "bun_thit_nuong": "🍜",
    "chao_long": "🥣",
    "com_tam": "🍚",
    "goi_cuon": "🥗",
    "pho": "🍜",
    "xoi": "🍙",
}
