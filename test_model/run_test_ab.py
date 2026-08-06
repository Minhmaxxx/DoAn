"""Create qualitative A0/A/B comparison images for the report."""

from __future__ import annotations

import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO


BASE_DIR = Path(__file__).resolve().parent
WEIGHTS_DIR = BASE_DIR / "weights_test"
IMAGE_DIR = BASE_DIR / "anh_test"
OUTPUT_DIR = BASE_DIR / "Ket_Qua_So_Sanh"

MODELS = {
    "Baseline_A0": WEIGHTS_DIR / "best_baseline_A0.pt",
    "Baseline_A": WEIGHTS_DIR / "best_baseline_A.pt",
    "Baseline_B": WEIGHTS_DIR / "best_baseline_B.pt",
}

# This is the app's current operational threshold, not the mAP evaluation threshold.
CONFIDENCE_THRESHOLD = 0.45
IOU_THRESHOLD = 0.45
IMAGE_SIZE = 640
MAX_PANEL_WIDTH = 640
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def describe_predictions(result) -> str:
    if result.boxes is None or len(result.boxes) == 0:
        return "khong co detection"

    predictions = []
    for box in result.boxes:
        class_id = int(box.cls.item())
        confidence = float(box.conf.item())
        predictions.append(f"{result.names[class_id]} ({confidence:.1%})")
    return ", ".join(predictions)


def annotated_image(result) -> Image.Image:
    # Ultralytics returns a BGR NumPy array; Pillow expects RGB.
    plotted = result.plot(labels=True, conf=True, boxes=True)
    return Image.fromarray(plotted[:, :, ::-1]).convert("RGB")


def resize_for_report(image: Image.Image) -> Image.Image:
    scale = min(1.0, MAX_PANEL_WIDTH / image.width)
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    return image.resize(size, Image.Resampling.LANCZOS)


def comparison_image(original: Image.Image, panels: list[tuple[str, Image.Image]]) -> Image.Image:
    resized_panels = [(title, resize_for_report(image)) for title, image in panels]
    header_height = 36
    panel_height = max(image.height for _, image in resized_panels)
    canvas = Image.new(
        "RGB",
        (sum(image.width for _, image in resized_panels), panel_height + header_height),
        "white",
    )
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=18)

    x = 0
    for title, panel in resized_panels:
        text_box = draw.textbbox((0, 0), title, font=font)
        text_width = text_box[2] - text_box[0]
        draw.text(
            (x + (panel.width - text_width) / 2, 8),
            title,
            fill="black",
            font=font,
        )
        canvas.paste(panel, (x, header_height))
        x += panel.width

    return canvas


def validate_inputs() -> list[Path]:
    missing = [path for path in MODELS.values() if not path.exists()]
    if missing:
        paths = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"Khong tim thay model: {paths}")

    image_paths = sorted(
        path
        for path in IMAGE_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )
    if not image_paths:
        raise FileNotFoundError(f"Khong tim thay anh test trong: {IMAGE_DIR}")
    return image_paths


def prediction_rows(image_name: str, model_name: str, result) -> list[dict]:
    if result.boxes is None or len(result.boxes) == 0:
        return [
            {
                "image": image_name,
                "model": model_name,
                "class_name": "",
                "confidence": "",
                "detections": 0,
            }
        ]

    rows = []
    for box in result.boxes:
        class_id = int(box.cls.item())
        rows.append(
            {
                "image": image_name,
                "model": model_name,
                "class_name": result.names[class_id],
                "confidence": f"{float(box.conf.item()):.6f}",
                "detections": len(result.boxes),
            }
        )
    return rows


def main() -> None:
    image_paths = validate_inputs()
    model_outputs = {
        model_name: OUTPUT_DIR / model_name for model_name in MODELS
    }
    comparison_output = OUTPUT_DIR / "So_Sanh"
    for directory in (*model_outputs.values(), comparison_output):
        directory.mkdir(parents=True, exist_ok=True)

    models = {}
    for model_name, model_path in MODELS.items():
        print(f"Dang tai {model_name}: {model_path}")
        models[model_name] = YOLO(str(model_path))
    print(
        f"Chay {len(image_paths)} anh voi conf={CONFIDENCE_THRESHOLD}, "
        f"iou={IOU_THRESHOLD}, imgsz={IMAGE_SIZE}"
    )

    rows = []
    for image_path in image_paths:
        print(f"\nAnh: {image_path.name}")
        original = Image.open(image_path).convert("RGB")
        plotted_panels = [("ANH GOC", original)]

        for model_name, model in models.items():
            result = model.predict(
                source=str(image_path),
                conf=CONFIDENCE_THRESHOLD,
                iou=IOU_THRESHOLD,
                imgsz=IMAGE_SIZE,
                verbose=False,
            )[0]
            print(f"  {model_name}: {describe_predictions(result)}")
            rows.extend(prediction_rows(image_path.name, model_name, result))

            plotted = annotated_image(result)
            plotted.save(model_outputs[model_name] / f"{image_path.stem}.jpg", quality=95)
            plotted_panels.append((model_name.replace("_", " ").upper(), plotted))

        comparison_image(original, plotted_panels).save(
            comparison_output / f"{image_path.stem}.jpg",
            quality=95,
        )

    with (OUTPUT_DIR / "qualitative_predictions.csv").open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nHoan tat. Ket qua duoc luu tai: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
