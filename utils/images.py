"""Image decoding and size validation used by the analysis page."""

from __future__ import annotations

import math

from PIL import Image, ImageOps, UnidentifiedImageError


class ImageInputError(ValueError):
    """Raised when an uploaded image cannot be decoded safely."""


def load_uploaded_image(
    source,
    *,
    max_pixels: int,
    max_dimension: int,
) -> Image.Image:
    """Decode an upload, apply EXIF orientation, resize, and return RGB pixels."""
    if max_pixels <= 0 or max_dimension <= 0:
        raise ValueError("Giới hạn ảnh phải lớn hơn 0")

    try:
        with Image.open(source) as source_image:
            image = ImageOps.exif_transpose(source_image)
            pixel_count = image.width * image.height
            scale = min(
                1.0,
                max_dimension / max(image.width, 1),
                max_dimension / max(image.height, 1),
                math.sqrt(max_pixels / max(pixel_count, 1)),
            )
            if scale < 1.0:
                target_size = (
                    max(1, int(image.width * scale)),
                    max(1, int(image.height * scale)),
                )
                image.thumbnail(target_size, Image.Resampling.LANCZOS)
            return image.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as error:
        raise ImageInputError(
            "Không thể đọc ảnh. Hãy chọn file JPG, PNG hoặc WEBP hợp lệ."
        ) from error
