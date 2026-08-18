"""Image decoding and size validation used by the analysis page."""

from __future__ import annotations

import math
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError


class ImageInputError(ValueError):
    """Raised when an uploaded image cannot be decoded safely."""


def load_uploaded_image(
    source,
    *,
    max_pixels: int,
    max_dimension: int,
    max_source_pixels: int | None = None,
    max_source_dimension: int | None = None,
) -> Image.Image:
    """Validate dimensions, decode, resize, and return bounded RGB pixels."""
    if max_pixels <= 0 or max_dimension <= 0:
        raise ValueError("Giới hạn ảnh phải lớn hơn 0")
    if max_source_pixels is not None and max_source_pixels <= 0:
        raise ValueError("Giới hạn ảnh nguồn phải lớn hơn 0")
    if max_source_dimension is not None and max_source_dimension <= 0:
        raise ValueError("Giới hạn ảnh nguồn phải lớn hơn 0")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            source_image = Image.open(source)
        with source_image:
            source_pixels = source_image.width * source_image.height
            source_too_large = (
                max_source_pixels is not None and source_pixels > max_source_pixels
            )
            source_too_wide = (
                max_source_dimension is not None
                and max(source_image.width, source_image.height) > max_source_dimension
            )
            if source_too_large or source_too_wide:
                raise ImageInputError(
                    "Ảnh có độ phân giải quá lớn. Hãy dùng chế độ chụp thường "
                    "hoặc giảm độ phân giải ảnh rồi thử lại."
                )

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
    except ImageInputError:
        raise
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as error:
        raise ImageInputError(
            "Không thể đọc ảnh. Hãy chọn file JPG, PNG hoặc WEBP hợp lệ."
        ) from error
