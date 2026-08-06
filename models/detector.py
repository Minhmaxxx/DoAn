# -*- coding: utf-8 -*-
"""
models/detector.py — YOLOv8 Food Detector Wrapper
Wraps Ultralytics YOLOv8 with Streamlit caching and a clean detection API.
"""

from __future__ import annotations

import hashlib
import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional

import streamlit as st

# Add project root to path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

import config


# ─── Detection Result Dataclass ──────────────────────────────────────────────

class Detection:
    """
    Represents a single food item detected in the image.

    Attributes
    ----------
    food_class : str
        Class label as defined in config.FOOD_CLASSES (e.g. 'pho')
    display_name : str
        Human-readable Vietnamese name (e.g. 'Phở')
    confidence : float
        Model confidence score between 0.0 and 1.0
    bbox : tuple[float, float, float, float]
        Bounding box as (x1, y1, x2, y2) in pixel coordinates
    """

    def __init__(
        self,
        food_class: str,
        confidence: float,
        bbox: tuple[float, float, float, float],
        raw_label: Optional[str] = None,
    ):
        self.food_class = food_class
        self.raw_label = raw_label or food_class
        self.display_name = config.FOOD_DISPLAY_NAMES.get(food_class, food_class)
        self.emoji = config.FOOD_EMOJIS.get(food_class, "")
        self.confidence = confidence
        self.bbox = bbox  # (x1, y1, x2, y2)

    def __repr__(self) -> str:
        return (
            f"Detection(food='{self.display_name}', "
            f"conf={self.confidence:.2f}, bbox={self.bbox})"
        )


# ─── YOLOv8 Wrapper ──────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def _load_model(model_path: str):
    """
    Load YOLOv8 model once and cache it for the session.
    Using @st.cache_resource ensures the heavy model is loaded exactly once.

    Parameters
    ----------
    model_path : str
        Path to the .pt model weights file.

    Returns
    -------
    YOLO model instance or None if loading fails.
    """
    try:
        from ultralytics import YOLO
        model = YOLO(model_path)
        raw_names = [model.names[index] for index in sorted(model.names)]
        expected_names = list(config.MODEL_CLASS_MAP)
        if raw_names != expected_names:
            raise ValueError(
                "Nhãn checkpoint không khớp hợp đồng 12 lớp. "
                f"Nhận được: {raw_names}"
            )
        return model
    except Exception as e:
        st.error(f" Không thể tải mô hình YOLOv8: {e}")
        return None


@lru_cache(maxsize=4)
def validate_model_artifact(model_path: str) -> tuple[bool, str]:
    """Validate that the selected deployment checkpoint exists and is unchanged."""
    path = Path(model_path)
    if not path.exists():
        return False, f"Không tìm thấy checkpoint tại {path}"

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if path.resolve() == Path(config.MODEL_PATH).resolve() and digest != config.MODEL_SHA256:
        return False, "Checksum checkpoint không khớp Baseline B đã benchmark"
    return True, digest


class FoodDetector:
    """
    High-level food detection interface.

    Usage
    -----
    >>> detector = FoodDetector()
    >>> detections = detector.detect(pil_image)
    >>> annotated = detector.draw_boxes(pil_image, detections)
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or str(config.MODEL_PATH)
        self._model = None
        self.is_valid, self.validation_message = validate_model_artifact(self.model_path)
        self.is_demo_mode = not self.is_valid and config.ENABLE_RANDOM_DEMO

        if not self.is_valid and self.is_demo_mode:
            st.warning(
                f"Demo ngẫu nhiên đang bật: {self.validation_message}. "
                "Kết quả này không được dùng để kiểm thử."
            )
        elif not self.is_valid:
            st.error(self.validation_message)

    def _ensure_model(self):
        """Lazy-load the model on first use."""
        if self._model is None and self.is_valid:
            self._model = _load_model(self.model_path)

    def detect(self, image: "PIL.Image.Image") -> list[Detection]:
        """
        Run food detection on a PIL Image.

        Parameters
        ----------
        image : PIL.Image.Image
            Input image (RGB format).

        Returns
        -------
        list[Detection]
            Sorted list of detections by confidence (highest first).
        """
        if self.is_demo_mode:
            return self._demo_detections()
        if not self.is_valid:
            return []

        self._ensure_model()
        if self._model is None:
            return []

        try:
            import numpy as np
            img_array = np.array(image.convert("RGB"))
            results = self._model.predict(
                source=img_array,
                conf=config.YOLO_CONF_THRESHOLD,
                iou=config.YOLO_IOU_THRESHOLD,
                imgsz=config.YOLO_IMG_SIZE,
                verbose=False,
            )

            detections = []
            for r in results:
                for box in r.boxes:
                    cls_idx = int(box.cls[0])
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = box.xyxy[0].tolist()

                    # Map index to class name
                    raw_label = self._model.names.get(cls_idx, f"class_{cls_idx}")
                    if raw_label not in config.MODEL_CLASS_MAP:
                        raise ValueError(f"Nhãn model chưa được ánh xạ: {raw_label}")
                    food_class = config.MODEL_CLASS_MAP[raw_label]

                    detections.append(Detection(
                        food_class=food_class,
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                        raw_label=raw_label,
                    ))

            # Sort by confidence descending
            detections.sort(key=lambda d: d.confidence, reverse=True)
            return detections

        except Exception as e:
            st.error(f" Lỗi trong quá trình nhận diện: {e}")
            return []

    def draw_boxes(
        self,
        image: "PIL.Image.Image",
        detections: list[Detection],
    ) -> "PIL.Image.Image":
        """
        Draw bounding boxes and labels on the image.

        Parameters
        ----------
        image : PIL.Image.Image
            Original input image.
        detections : list[Detection]
            Detections from the detect() method.

        Returns
        -------
        PIL.Image.Image
            Annotated image with bounding boxes drawn.
        """
        try:
            from PIL import ImageDraw, ImageFont

            img = image.copy().convert("RGB")
            draw = ImageDraw.Draw(img)

            # Color palette for boxes
            colors = [
                "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
                "#FFEAA7", "#DDA0DD", "#98FB98", "#F0E68C",
                "#87CEEB", "#FFA07A",
            ]

            try:
                font = ImageFont.truetype("DejaVuSans.ttf", 18)
            except OSError:
                font = ImageFont.load_default()

            for det in detections:
                class_index = config.FOOD_CLASSES.index(det.food_class)
                color = colors[class_index % len(colors)]
                x1, y1, x2, y2 = det.bbox

                # Draw rectangle
                draw.rectangle([x1, y1, x2, y2], outline=color, width=3)

                # Draw label background
                label = f"{det.display_name} ({det.confidence:.0%})"
                text_box = draw.textbbox((0, 0), label, font=font)
                label_width = text_box[2] - text_box[0] + 12
                label_height = text_box[3] - text_box[1] + 10
                label_x = min(max(x1, 0), max(img.width - label_width, 0))
                label_y = max(y1 - label_height, 0)
                draw.rectangle(
                    [label_x, label_y, label_x + label_width, label_y + label_height],
                    fill=color,
                )
                draw.text((label_x + 6, label_y + 4), label, fill="#101018", font=font)

            return img

        except Exception as e:
            st.warning(f"Không thể vẽ bounding box: {e}")
            return image

    def _demo_detections(self) -> list[Detection]:
        """
        Return simulated detections for demo/development mode.
        Used when the trained model file is not yet available.
        """
        import random
        demo_foods = random.sample(config.FOOD_CLASSES, k=random.randint(1, 3))
        detections = []
        for i, food_class in enumerate(demo_foods):
            # Generate plausible bounding boxes
            x1 = random.randint(50, 200) + i * 150
            y1 = random.randint(50, 150)
            x2 = x1 + random.randint(150, 250)
            y2 = y1 + random.randint(120, 200)
            conf = random.uniform(0.72, 0.97)

            detections.append(Detection(
                food_class=food_class,
                confidence=conf,
                bbox=(x1, y1, x2, y2),
            ))
        return detections
