# -*- coding: utf-8 -*-
"""
models/detector.py — YOLOv8 Food Detector Wrapper
Wraps Ultralytics YOLOv8 with Streamlit caching and a clean detection API.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

import numpy as np
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
        Class label as defined in config.FOOD_CLASSES (e.g. 'pho_bo')
    display_name : str
        Human-readable Vietnamese name (e.g. 'Phở bò')
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
    ):
        self.food_class = food_class
        self.display_name = config.FOOD_DISPLAY_NAMES.get(food_class, food_class)
        self.emoji = config.FOOD_EMOJIS.get(food_class, "🍽️")
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
        return model
    except Exception as e:
        st.error(f"❌ Không thể tải mô hình YOLOv8: {e}")
        return None


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
        self.is_demo_mode = not Path(self.model_path).exists()

        if self.is_demo_mode:
            st.warning(
                f"Demo Mode: Model not found at `{self.model_path}`. "
                "Using simulated detections. After training, place `best.pt` in `models/weights/`.",
                icon="🤖"
            )

    def _ensure_model(self):
        """Lazy-load the model on first use."""
        if self._model is None and not self.is_demo_mode:
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
                    class_name = self._model.names.get(cls_idx, f"class_{cls_idx}")
                    if class_name not in config.FOOD_CLASSES:
                        continue

                    detections.append(Detection(
                        food_class=class_name,
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                    ))

            # Sort by confidence descending
            detections.sort(key=lambda d: d.confidence, reverse=True)
            return detections

        except Exception as e:
            st.error(f"❌ Lỗi trong quá trình nhận diện: {e}")
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
            import io

            img = image.copy().convert("RGB")
            draw = ImageDraw.Draw(img)

            # Color palette for boxes
            colors = [
                "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
                "#FFEAA7", "#DDA0DD", "#98FB98", "#F0E68C",
                "#87CEEB", "#FFA07A",
            ]

            for i, det in enumerate(detections):
                color = colors[i % len(colors)]
                x1, y1, x2, y2 = det.bbox

                # Draw rectangle
                draw.rectangle([x1, y1, x2, y2], outline=color, width=3)

                # Draw label background
                label = f"{det.emoji} {det.display_name} ({det.confidence:.0%})"
                label_y = max(y1 - 30, 0)
                draw.rectangle(
                    [x1, label_y, x1 + len(label) * 8, label_y + 25],
                    fill=color,
                )
                draw.text((x1 + 4, label_y + 4), label, fill="white")

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
