"""Build the frozen, leakage-filtered common test benchmark for A0, A, and B."""

from __future__ import annotations

import csv
import hashlib
import shutil
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SOURCE_DIR = BASE_DIR.parent / "datasets" / "Baseline_B_yolov8" / "test"
OUTPUT_DIR = BASE_DIR / "benchmark_common_v1"
CLASS_NAMES = [
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

# Confirmed by the source-aware leakage audit. Never delete source data; exclude
# only these files from the copied benchmark.
EXCLUSIONS = {
    "38_jpg.rf.f0002c724dc3a82eb50c3c848cfd4370.jpg": "near_duplicate_train",
    "429_jpg.rf.6074109df50deec338d6d464cfbd3b3d.jpg": "near_duplicate_train",
    "472_jpg.rf.dd7923351447d4675559809da8006650.jpg": "near_duplicate_train",
    "bg_039_jpg.rf.4f0f42931e0ba9909731e9c25be8fef1.jpg": "near_duplicate_train",
    "322_jpg.rf.e093a841bf26cc9a965ab669785f0336.jpg": "near_duplicate_train",
    "144_jpg.rf.3b14652041564220ebb89248c42ee028.jpg": "near_duplicate_train",
    "xoi_xeo_5d39beae72fe_jpg.rf.c502c13a6a73ebf68fe3eca838920826.jpg": "near_duplicate_train",
    "156_jpg.rf.05daeca9cea3540b8f1574decb832e0d.jpg": "near_duplicate_train",
    "12_jpg.rf.7f62ef5b027b0ceeacb0889f0b885738.jpg": "near_duplicate_train",
    "xoi_xeo_f6ad76d8bab0_jpg.rf.4e49b51ad718ff7d51909070783423e4.jpg": "near_duplicate_train",
    "272_jpg.rf.f7ed76b333180b86a94f2fb909a4c863.jpg": "near_duplicate_train",
    "528_jpg.rf.15718c42ce9fa7faba080415ebc3a3d6.jpg": "near_duplicate_train",
    "227_jpg.rf.a5e043f1a51efba5c96efd59efc1091a.jpg": "near_duplicate_train",
    "xoi_xeo_a13b546b6ebf_jpg.rf.12538275a41d4df508f1d77c021c3705.jpg": "near_duplicate_validation",
    "183_jpg.rf.292e0b2cb23addd500e80437b5b20a32.jpg": "near_duplicate_validation",
    "401_jpg.rf.059961b76cf98fc249d3f10ef39c4822.jpg": "crop_or_reframe_train",
    "209_jpg.rf.773f48673443811d5bb1eb1f60457975.jpg": "crop_or_reframe_train",
    "277_jpg.rf.b16b16a05d7a3fca4df63370499fb5cd.jpg": "crop_or_reframe_train",
    "501_jpg.rf.35dd130891a0b6515c4520136ed338e3.jpg": "crop_or_reframe_train",
    "44_jpg.rf.86cda05a6db79b56ccb3437bb1d0232c.jpg": "crop_or_reframe_train",
    "1388_jpg.rf.9c898fbcb5c0d49e2f5f01e46151de18.jpg": "crop_or_reframe_validation",
    "711_jpg.rf.4c00fd2e02ce33509c0f6e2cb54ea7af.jpg": "crop_or_reframe_validation",
    "xoi_xeo_1b9c81ee6ebb_jpg.rf.b3023821c0dac7dd97ffc2dfa269cf7a.jpg": "composite_components_seen_train",
    "703_jpg.rf.07e14c251fabddbe11c0395f4806a18c.jpg": "same_scene_validation",
    "116_jpg.rf.b6baa33ba15f901313286849e3407790.jpg": "same_scene_train",
    "250_jpg.rf.e715f19a1280b7a2d676995ca4da72ca.jpg": "same_scene_train",
    "592_jpg.rf.9944b3ab0cdeee4a619ee4476dc2aa6e.jpg": "internal_test_duplicate_of_247",
    "47_jpg.rf.5e67b474b86b2d06aa11f8d11a1134f6.jpg": "internal_test_duplicate_of_158",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def label_summary(label_path: Path) -> tuple[str, int]:
    rows = [line.split() for line in label_path.read_text(encoding="utf-8").splitlines() if line]
    class_ids = sorted({int(row[0]) for row in rows})
    if any(class_id < 0 or class_id >= len(CLASS_NAMES) for class_id in class_ids):
        raise ValueError(f"Class ID khong hop le trong {label_path}")
    return ";".join(str(class_id) for class_id in class_ids), len(rows)


def write_dataset_yaml() -> None:
    names = ", ".join(f"'{name}'" for name in CLASS_NAMES)
    (OUTPUT_DIR / "dataset.yaml").write_text(
        "train: images\n"
        "val: images\n"
        "test: images\n"
        f"nc: {len(CLASS_NAMES)}\n"
        f"names: [{names}]\n",
        encoding="utf-8",
    )


def build() -> None:
    source_images = SOURCE_DIR / "images"
    source_labels = SOURCE_DIR / "labels"
    if not source_images.exists() or not source_labels.exists():
        raise FileNotFoundError(f"Khong tim thay dataset nguon: {SOURCE_DIR}")
    if OUTPUT_DIR.exists():
        raise FileExistsError(
            f"Benchmark da ton tai: {OUTPUT_DIR}. Xoa thu muc nay neu muon tao lai."
        )

    output_images = OUTPUT_DIR / "images"
    output_labels = OUTPUT_DIR / "labels"
    output_images.mkdir(parents=True)
    output_labels.mkdir(parents=True)

    image_paths = sorted(path for path in source_images.iterdir() if path.is_file())
    missing_exclusions = sorted(set(EXCLUSIONS) - {path.name for path in image_paths})
    if missing_exclusions:
        raise FileNotFoundError(f"Khong tim thay anh trong danh sach loai: {missing_exclusions}")

    rows = []
    excluded_rows = []
    for image_path in image_paths:
        label_path = source_labels / f"{image_path.stem}.txt"
        if not label_path.exists():
            raise FileNotFoundError(f"Thieu label cho {image_path.name}")

        exclusion_reason = EXCLUSIONS.get(image_path.name)
        class_ids, box_count = label_summary(label_path)
        if exclusion_reason:
            excluded_rows.append(
                {
                    "source_image": image_path.name,
                    "reason": exclusion_reason,
                    "class_ids": class_ids,
                    "box_count": box_count,
                }
            )
            continue

        shutil.copy2(image_path, output_images / image_path.name)
        shutil.copy2(label_path, output_labels / label_path.name)
        rows.append(
            {
                "image": image_path.name,
                "source_image": str(image_path),
                "source_label": str(label_path),
                "image_sha256": sha256(image_path),
                "label_sha256": sha256(label_path),
                "class_ids": class_ids,
                "box_count": box_count,
            }
        )

    with (OUTPUT_DIR / "manifest.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    with (OUTPUT_DIR / "excluded.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=excluded_rows[0].keys())
        writer.writeheader()
        writer.writerows(excluded_rows)

    write_dataset_yaml()
    (OUTPUT_DIR / "README.md").write_text(
        "# Common Benchmark v1\n\n"
        "This benchmark contains copied, not moved, files from "
        "`datasets/Baseline_B_yolov8/test`. It excludes 26 cross-split "
        "leaks and one image from each of two internal duplicate pairs. "
        "Use the frozen `manifest.csv` and `dataset.yaml` to evaluate A0, A, "
        "and B. Do not tune training or confidence thresholds against this set.\n",
        encoding="utf-8",
    )

    if len(rows) != 404 or len(excluded_rows) != 28:
        raise RuntimeError(
            f"Benchmark khong dung kich thuoc: {len(rows)} kept, {len(excluded_rows)} excluded"
        )
    print(f"Da tao {len(rows)} anh benchmark tai: {OUTPUT_DIR}")
    print(f"Da loai {len(excluded_rows)} anh; xem: {OUTPUT_DIR / 'excluded.csv'}")


if __name__ == "__main__":
    build()
