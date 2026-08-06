"""Evaluate Baseline A0, A, and B on the frozen common benchmark."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import time
from pathlib import Path

import ultralytics
from ultralytics import YOLO


BASE_DIR = Path(__file__).resolve().parent
BENCHMARK_DIR = BASE_DIR / "benchmark_common_v1"
DATASET_YAML = BENCHMARK_DIR / "dataset.yaml"
WEIGHTS_DIR = BASE_DIR / "weights_test"
OUTPUT_DIR = BASE_DIR / "benchmark_results_common_v1"

MODELS = {
    "Baseline_A0": WEIGHTS_DIR / "best_baseline_A0.pt",
    "Baseline_A": WEIGHTS_DIR / "best_baseline_A.pt",
    "Baseline_B": WEIGHTS_DIR / "best_baseline_B.pt",
}
EXPECTED_CLASS_NAMES = [
    "Banh-mi",
    "Banh-trang-nuong",
    "Banh-xeo",
    "Bun-bo-Hue",
    "Bun-dau-mam-tom",
    "Bun-rieu",
    "Bun-thit-nuong",
    "Chao-long",
    "Com-tam",
    "Goi-cuon",
    "Pho",
    "Xoi",
]

# Fixed evaluation settings for a fair, reproducible comparison.
IMAGE_SIZE = 640
IOU_THRESHOLD = 0.7
MAP_CONFIDENCE = 0.001
BATCH_SIZE = 16
DEVICE = "cpu"
OPERATIONAL_CONFIDENCE = 0.45
OPERATIONAL_IOU = 0.45


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def to_list(value) -> list:
    if hasattr(value, "tolist"):
        return value.tolist()
    return list(value)


def validate_inputs() -> int:
    if not DATASET_YAML.exists():
        raise FileNotFoundError(
            f"Khong tim thay benchmark. Chay: python test_model/build_common_benchmark.py"
        )

    manifest = BENCHMARK_DIR / "manifest.csv"
    with manifest.open(encoding="utf-8") as file:
        image_count = sum(1 for _ in csv.DictReader(file))
    if image_count != 404:
        raise ValueError(f"Benchmark phai co 404 anh, nhung tim thay {image_count}")

    missing = [path for path in MODELS.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Khong tim thay weights: {', '.join(map(str, missing))}")
    return image_count


def per_class_rows(model_name: str, metrics) -> list[dict]:
    class_indexes = [int(index) for index in to_list(metrics.box.ap_class_index)]
    precision = to_list(metrics.box.p)
    recall = to_list(metrics.box.r)
    ap50 = to_list(metrics.box.ap50)
    ap50_95 = to_list(metrics.box.ap)

    rows = []
    for index, class_id in enumerate(class_indexes):
        rows.append(
            {
                "model": model_name,
                "class_id": class_id,
                "class_name": EXPECTED_CLASS_NAMES[class_id],
                "precision": float(precision[index]),
                "recall": float(recall[index]),
                "mAP50": float(ap50[index]),
                "mAP50_95": float(ap50_95[index]),
            }
        )
    return rows


def negative_image_paths() -> list[Path]:
    paths = []
    for image_path in sorted((BENCHMARK_DIR / "images").iterdir()):
        label_path = BENCHMARK_DIR / "labels" / f"{image_path.stem}.txt"
        if not label_path.read_text(encoding="utf-8").strip():
            paths.append(image_path)
    return paths


def evaluate(model_name: str, model_path: Path) -> tuple[dict, list[dict]]:
    model = YOLO(str(model_path))
    class_names = [model.names[index] for index in sorted(model.names)]
    if class_names != EXPECTED_CLASS_NAMES:
        raise ValueError(f"Class order khong khop cho {model_name}: {class_names}")

    start = time.perf_counter()
    metrics = model.val(
        data=str(DATASET_YAML),
        split="test",
        imgsz=IMAGE_SIZE,
        conf=MAP_CONFIDENCE,
        iou=IOU_THRESHOLD,
        batch=BATCH_SIZE,
        device=DEVICE,
        workers=0,
        save_json=False,
        plots=True,
        project=str(OUTPUT_DIR),
        name=model_name,
        exist_ok=True,
        verbose=False,
    )
    elapsed_seconds = time.perf_counter() - start
    negative_results = model.predict(
        source=[str(path) for path in negative_image_paths()],
        conf=OPERATIONAL_CONFIDENCE,
        iou=OPERATIONAL_IOU,
        imgsz=IMAGE_SIZE,
        device=DEVICE,
        verbose=False,
    )
    false_positives = sum(len(result.boxes) for result in negative_results)
    negative_images_with_detections = sum(bool(len(result.boxes)) for result in negative_results)
    result = metrics.results_dict
    summary = {
        "model": model_name,
        "weight_file": str(model_path),
        "weight_sha256": sha256(model_path),
        "ultralytics_version": ultralytics.__version__,
        "benchmark_images": 404,
        "imgsz": IMAGE_SIZE,
        "iou": IOU_THRESHOLD,
        "map_confidence": MAP_CONFIDENCE,
        "batch": BATCH_SIZE,
        "device": DEVICE,
        "precision": float(result["metrics/precision(B)"]),
        "recall": float(result["metrics/recall(B)"]),
        "mAP50": float(result["metrics/mAP50(B)"]),
        "mAP50_95": float(result["metrics/mAP50-95(B)"]),
        "fitness": float(result["fitness"]),
        "preprocess_ms_per_image": float(metrics.speed["preprocess"]),
        "inference_ms_per_image": float(metrics.speed["inference"]),
        "postprocess_ms_per_image": float(metrics.speed["postprocess"]),
        "operational_confidence": OPERATIONAL_CONFIDENCE,
        "operational_iou": OPERATIONAL_IOU,
        "negative_images": len(negative_results),
        "negative_images_with_detections": negative_images_with_detections,
        "false_positives_on_negatives": false_positives,
        "fp_per_negative_image": false_positives / len(negative_results),
        "elapsed_seconds": elapsed_seconds,
        "result_directory": str(OUTPUT_DIR / model_name),
    }
    return summary, per_class_rows(model_name, metrics)


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overwrite", action="store_true", help="Xoa ket qua benchmark cu truoc khi chay")
    args = parser.parse_args()
    image_count = validate_inputs()
    if OUTPUT_DIR.exists():
        if not args.overwrite:
            raise FileExistsError(
                f"Thu muc ket qua da ton tai: {OUTPUT_DIR}. Dung --overwrite de tao lai."
            )
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    summaries = []
    class_metrics = []
    for model_name, model_path in MODELS.items():
        print(f"\nDanh gia {model_name} tren {image_count} anh...")
        summary, rows = evaluate(model_name, model_path)
        summaries.append(summary)
        class_metrics.extend(rows)
        print(
            f"  P={summary['precision']:.4f}, R={summary['recall']:.4f}, "
            f"mAP50={summary['mAP50']:.4f}, mAP50-95={summary['mAP50_95']:.4f}, "
            f"FP negatives={summary['false_positives_on_negatives']}, "
            f"inference={summary['inference_ms_per_image']:.2f} ms/anh"
        )

    write_csv(OUTPUT_DIR / "overall_metrics.csv", summaries)
    write_csv(OUTPUT_DIR / "per_class_metrics.csv", class_metrics)
    (OUTPUT_DIR / "evaluation_config.json").write_text(
        json.dumps(
            {
                "benchmark_manifest_sha256": sha256(BENCHMARK_DIR / "manifest.csv"),
                "settings": {
                    "imgsz": IMAGE_SIZE,
                    "iou": IOU_THRESHOLD,
                    "map_confidence": MAP_CONFIDENCE,
                    "batch": BATCH_SIZE,
                    "device": DEVICE,
                    "operational_confidence": OPERATIONAL_CONFIDENCE,
                    "operational_iou": OPERATIONAL_IOU,
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nHoan tat. Ket qua benchmark: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
