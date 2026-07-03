"""
training/train.py — YOLOv8 Training Script
Fine-tunes YOLOv8n on the custom Vietnamese food dataset from Roboflow.

Usage:
    python training/train.py

Requirements:
    - pip install ultralytics roboflow
    - GPU (Google Colab T4 recommended)
    - Roboflow API key set in .env
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

# ─── Configuration ────────────────────────────────────────────────────────────
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY", "")
ROBOFLOW_WORKSPACE = "your-workspace"       # Replace with your Roboflow workspace slug
ROBOFLOW_PROJECT = "vietnamese-foods"       # Replace with your project slug
ROBOFLOW_VERSION = 1                        # Dataset version number

# YOLOv8 training settings
BASE_MODEL = "yolov8n.pt"                   # Pretrained nano model (transfer learning)
EPOCHS = 150
IMG_SIZE = 640
BATCH_SIZE = 16                             # Reduce to 8 if GPU OOM
PATIENCE = 20                               # Early stopping patience
WORKERS = 4
DEVICE = "0"                                # '0' for GPU, 'cpu' for CPU

OUTPUT_DIR = ROOT_DIR / "runs" / "train"
WEIGHTS_OUTPUT = ROOT_DIR / "models" / "weights"


def download_dataset() -> str:
    """
    Download the dataset from Roboflow in YOLOv8 format.

    Returns
    -------
    str
        Path to the downloaded dataset.yaml file.
    """
    if not ROBOFLOW_API_KEY:
        raise ValueError(
            "ROBOFLOW_API_KEY not set. Add it to your .env file.\n"
            "Get your key from: https://app.roboflow.com/settings/api"
        )

    print(" Downloading dataset from Roboflow...")
    from roboflow import Roboflow

    rf = Roboflow(api_key=ROBOFLOW_API_KEY)
    project = rf.workspace(ROBOFLOW_WORKSPACE).project(ROBOFLOW_PROJECT)
    version = project.version(ROBOFLOW_VERSION)
    dataset = version.download("yolov8", location=str(ROOT_DIR / "datasets"))

    yaml_path = Path(dataset.location) / "data.yaml"
    print(f" Dataset downloaded to: {dataset.location}")
    print(f" Dataset config: {yaml_path}")
    return str(yaml_path)


def train(dataset_yaml: str) -> None:
    """
    Run YOLOv8 training.

    Parameters
    ----------
    dataset_yaml : str
        Path to the dataset YAML configuration file.
    """
    from ultralytics import YOLO

    print(f"\n Starting YOLOv8 training...")
    print(f"   Base model: {BASE_MODEL}")
    print(f"   Dataset: {dataset_yaml}")
    print(f"   Epochs: {EPOCHS}, Batch: {BATCH_SIZE}, ImgSize: {IMG_SIZE}")
    print(f"   Device: {DEVICE}")
    print()

    model = YOLO(BASE_MODEL)

    results = model.train(
        data=dataset_yaml,
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH_SIZE,
        patience=PATIENCE,
        workers=WORKERS,
        device=DEVICE,
        project=str(OUTPUT_DIR),
        name="nutrivision",
        exist_ok=True,
        # Augmentation settings
        augment=True,
        hsv_h=0.015,         # Hue augmentation
        hsv_s=0.7,           # Saturation augmentation
        hsv_v=0.4,           # Value augmentation
        degrees=10,          # Rotation degrees
        translate=0.1,
        scale=0.5,
        fliplr=0.5,
        mosaic=1.0,          # Mosaic augmentation
        mixup=0.1,
        # Hyperparameters
        lr0=0.01,
        lrf=0.01,
        momentum=0.937,
        weight_decay=0.0005,
        warmup_epochs=3,
    )

    # Copy best weights to models/weights/
    best_pt = OUTPUT_DIR / "nutrivision" / "weights" / "best.pt"
    if best_pt.exists():
        import shutil
        WEIGHTS_OUTPUT.mkdir(parents=True, exist_ok=True)
        shutil.copy2(best_pt, WEIGHTS_OUTPUT / "best.pt")
        print(f"\n Best weights saved to: {WEIGHTS_OUTPUT / 'best.pt'}")

    return results


def evaluate(dataset_yaml: str) -> None:
    """
    Evaluate the trained model on the test set.
    """
    from ultralytics import YOLO

    model_path = WEIGHTS_OUTPUT / "best.pt"
    if not model_path.exists():
        print(f" Model not found at {model_path}. Train first.")
        return

    print(f"\n Evaluating model on test set...")
    model = YOLO(str(model_path))
    metrics = model.val(
        data=dataset_yaml,
        split="test",
        imgsz=IMG_SIZE,
        conf=0.45,
        iou=0.45,
    )

    print(f"\n Evaluation Results:")
    print(f"   mAP50:    {metrics.box.map50:.4f}")
    print(f"   mAP50-95: {metrics.box.map:.4f}")
    print(f"   Precision: {metrics.box.mp:.4f}")
    print(f"   Recall:    {metrics.box.mr:.4f}")

    return metrics


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NutriVision YOLOv8 Training Script")
    parser.add_argument("--skip-download", action="store_true",
                        help="Skip Roboflow download, use existing dataset.yaml")
    parser.add_argument("--yaml", type=str, default=None,
                        help="Path to existing dataset.yaml (use with --skip-download)")
    parser.add_argument("--eval-only", action="store_true",
                        help="Only run evaluation on existing model")
    args = parser.parse_args()

    if args.skip_download and args.yaml:
        yaml_path = args.yaml
    elif args.skip_download:
        # Look for dataset.yaml in common locations
        candidates = list(ROOT_DIR.glob("datasets/**/data.yaml"))
        if candidates:
            yaml_path = str(candidates[0])
            print(f"Found dataset.yaml at: {yaml_path}")
        else:
            print(" No dataset.yaml found. Run without --skip-download to download.")
            sys.exit(1)
    else:
        yaml_path = download_dataset()

    if args.eval_only:
        evaluate(yaml_path)
    else:
        train(yaml_path)
        evaluate(yaml_path)
