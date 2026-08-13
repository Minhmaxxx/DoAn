"""Image input tests independent of Streamlit widgets."""

from io import BytesIO

import pytest
from PIL import Image

from utils.images import ImageInputError, load_uploaded_image


def encoded_image(image: Image.Image, image_format: str, *, exif=None) -> BytesIO:
    output = BytesIO()
    save_options = {"exif": exif} if exif is not None else {}
    image.save(output, format=image_format, **save_options)
    output.seek(0)
    return output


@pytest.mark.parametrize("image_format", ["JPEG", "PNG", "WEBP"])
def test_supported_formats_decode_to_rgb(image_format):
    source = encoded_image(Image.new("RGB", (32, 24), "red"), image_format)
    result = load_uploaded_image(source, max_pixels=1_000_000, max_dimension=1000)
    assert result.mode == "RGB"
    assert result.size == (32, 24)


def test_exif_orientation_is_applied():
    exif = Image.Exif()
    exif[274] = 6
    source = encoded_image(Image.new("RGB", (20, 30), "blue"), "JPEG", exif=exif)
    result = load_uploaded_image(source, max_pixels=1_000_000, max_dimension=1000)
    assert result.size == (30, 20)


def test_corrupt_input_returns_stable_user_error():
    with pytest.raises(ImageInputError, match="JPG, PNG hoặc WEBP"):
        load_uploaded_image(
            BytesIO(b"not-an-image"),
            max_pixels=1_000_000,
            max_dimension=1000,
        )


def test_pixel_limit_resizes_before_rgb_output():
    source = encoded_image(Image.new("RGB", (100, 100), "green"), "PNG")
    result = load_uploaded_image(source, max_pixels=2500, max_dimension=500)
    assert result.width * result.height <= 2500
    assert result.size == (50, 50)


def test_dimension_limit_applies_even_when_pixel_count_is_small():
    source = encoded_image(Image.new("RGB", (100, 20), "white"), "PNG")
    result = load_uploaded_image(source, max_pixels=1_000_000, max_dimension=50)
    assert result.size == (50, 10)


def test_invalid_limits_are_rejected():
    source = encoded_image(Image.new("RGB", (10, 10), "white"), "PNG")
    with pytest.raises(ValueError, match="lớn hơn 0"):
        load_uploaded_image(source, max_pixels=0, max_dimension=50)
