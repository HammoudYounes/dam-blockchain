"""
Pytest unit tests for the HSVHash algorithm.

Tests the public API: hsv_hash(), hamming(), hash_to_hex(),
rgb_to_hsv(), rgb_to_intensity().
No dataset required — all test images are generated synthetically.

Run from the hashing/ directory:
    pytest tests/test_hsvhash.py -v
"""

import os
import sys

import numpy as np
import pytest
from PIL import Image, ImageEnhance, ImageFilter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from algorithms.HSVHash import hsv_hash, hamming, hash_to_hex, rgb_to_hsv, rgb_to_intensity


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _solid(r, g, b, size=128):
    return np.full((size, size, 3), [r, g, b], dtype=np.uint8)


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES — synthetic test images (as numpy arrays)
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def gradient_arr():
    """128×128 horizontal grayscale gradient — realistic luminance pattern."""
    ramp = np.tile(np.arange(128, dtype=np.uint8), (128, 1))
    return np.stack([ramp, ramp, ramp], axis=-1)


@pytest.fixture(scope="module")
def noise_arr():
    """128×128 random RGB noise — structurally unrelated to gradient."""
    rng = np.random.default_rng(42)
    return rng.integers(0, 256, size=(128, 128, 3), dtype=np.uint8)


@pytest.fixture(scope="module")
def red_arr():
    """128×128 solid red image."""
    return _solid(255, 0, 0)


@pytest.fixture(scope="module")
def blue_arr():
    """128×128 solid blue image."""
    return _solid(0, 0, 255)


@pytest.fixture(scope="module")
def black_arr():
    """128×128 solid black image."""
    return _solid(0, 0, 0)


@pytest.fixture(scope="module")
def white_arr():
    """128×128 solid white image."""
    return _solid(255, 255, 255)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — hsv_hash()
# ══════════════════════════════════════════════════════════════════════════════


class TestHsvHash:
    """Tests for the hsv_hash() function."""

    def test_returns_ndarray(self, gradient_arr):
        assert isinstance(hsv_hash(gradient_arr), np.ndarray)

    def test_default_length_is_42(self, gradient_arr):
        h = hsv_hash(gradient_arr)
        assert len(h) == 42, f"Expected 42 bits (14 bins × 3 binbits), got {len(h)}"

    def test_custom_binbits_changes_length(self, gradient_arr):
        assert len(hsv_hash(gradient_arr, binbits=4)) == 56  # 14 × 4

    def test_contains_only_booleans(self, gradient_arr):
        h = hsv_hash(gradient_arr)
        assert set(h.tolist()).issubset({True, False, 0, 1})

    def test_deterministic(self, gradient_arr):
        assert np.array_equal(hsv_hash(gradient_arr), hsv_hash(gradient_arr))

    def test_accepts_float_input(self, gradient_arr):
        """float [0, 1] and uint8 [0, 255] inputs must produce the same hash."""
        float_arr = gradient_arr.astype(np.float32) / 255.0
        assert np.array_equal(hsv_hash(gradient_arr), hsv_hash(float_arr))

    def test_different_colors_produce_different_hashes(self, red_arr, blue_arr):
        assert not np.array_equal(hsv_hash(red_arr), hsv_hash(blue_arr))

    def test_black_image_saturates_black_bin(self, black_arr):
        """All-black image: every pixel falls into the black bin → first 3 bits = 1."""
        black_bits = hsv_hash(black_arr, binbits=3)[:3]
        assert all(black_bits), f"Expected black bin saturated, got {black_bits}"

    def test_white_image_empties_black_bin(self, white_arr):
        """All-white image: no dark pixels → black bin fraction = 0 → first 3 bits = 0."""
        black_bits = hsv_hash(white_arr, binbits=3)[:3]
        assert not any(black_bits), f"Expected black bin empty, got {black_bits}"


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — hamming()
# ══════════════════════════════════════════════════════════════════════════════


class TestHamming:
    """Tests for the hamming() function."""

    def test_identical_returns_zero(self, gradient_arr):
        h = hsv_hash(gradient_arr)
        assert hamming(h, h) == 0

    def test_complement_returns_42(self):
        h1 = np.ones(42, dtype=bool)
        h2 = np.zeros(42, dtype=bool)
        assert hamming(h1, h2) == 42

    def test_single_bit_difference(self):
        h1 = np.zeros(42, dtype=bool)
        h2 = h1.copy()
        h2[0] = True
        assert hamming(h1, h2) == 1

    def test_known_distance(self):
        h1 = np.array([True, False] * 21, dtype=bool)
        h2 = np.array([False, True] * 21, dtype=bool)
        assert hamming(h1, h2) == 42

    def test_symmetric(self, gradient_arr, noise_arr):
        h1 = hsv_hash(gradient_arr)
        h2 = hsv_hash(noise_arr)
        assert hamming(h1, h2) == hamming(h2, h1)

    def test_returns_int(self, gradient_arr):
        h = hsv_hash(gradient_arr)
        assert isinstance(hamming(h, h), int)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — hash_to_hex()
# ══════════════════════════════════════════════════════════════════════════════


class TestHashToHex:
    """Tests for the hash_to_hex() function."""

    def test_returns_string(self, gradient_arr):
        assert isinstance(hash_to_hex(hsv_hash(gradient_arr)), str)

    def test_default_length_is_14_chars(self, gradient_arr):
        # binbits=3: (3+3)//4 = 1 hex char per bin, 14 bins → 14 chars
        assert len(hash_to_hex(hsv_hash(gradient_arr))) == 14

    def test_all_zeros_hash_returns_zero_string(self):
        assert hash_to_hex(np.zeros(42, dtype=bool)) == "0" * 14

    def test_deterministic(self, gradient_arr):
        h = hsv_hash(gradient_arr)
        assert hash_to_hex(h) == hash_to_hex(h)

    def test_different_images_produce_different_hex(self, red_arr, blue_arr):
        assert hash_to_hex(hsv_hash(red_arr)) != hash_to_hex(hsv_hash(blue_arr))


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — rgb_to_hsv()
# ══════════════════════════════════════════════════════════════════════════════


class TestRgbToHsv:
    """Tests for the rgb_to_hsv() conversion."""

    def test_output_shape_matches_input(self):
        out = rgb_to_hsv(np.zeros((64, 64, 3), dtype=np.uint8))
        assert out.shape == (64, 64, 3)

    def test_output_dtype_is_uint8(self):
        assert rgb_to_hsv(np.zeros((64, 64, 3), dtype=np.uint8)).dtype == np.uint8

    def test_pure_red_hue_near_zero(self):
        # Red → hue = 0°; scaled to 0/255 ≈ 0
        hsv = rgb_to_hsv(_solid(255, 0, 0, size=4))
        assert hsv[0, 0, 0] == pytest.approx(0, abs=5)

    def test_pure_green_hue_near_85(self):
        # Green → hue = 120°; scaled: 120/360 × 255 ≈ 85
        hsv = rgb_to_hsv(_solid(0, 255, 0, size=4))
        assert hsv[0, 0, 0] == pytest.approx(85, abs=5)

    def test_pure_blue_hue_near_170(self):
        # Blue → hue = 240°; scaled: 240/360 × 255 ≈ 170
        hsv = rgb_to_hsv(_solid(0, 0, 255, size=4))
        assert hsv[0, 0, 0] == pytest.approx(170, abs=5)

    def test_black_has_zero_saturation_and_value(self):
        hsv = rgb_to_hsv(_solid(0, 0, 0, size=4))
        assert hsv[0, 0, 1] == 0   # saturation
        assert hsv[0, 0, 2] == 0   # value

    def test_white_has_zero_saturation_and_full_value(self):
        hsv = rgb_to_hsv(_solid(255, 255, 255, size=4))
        assert hsv[0, 0, 1] == 0    # saturation
        assert hsv[0, 0, 2] == 255  # value


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — rgb_to_intensity()
# ══════════════════════════════════════════════════════════════════════════════


class TestRgbToIntensity:
    """Tests for the rgb_to_intensity() function."""

    def test_output_shape_is_2d(self):
        assert rgb_to_intensity(np.zeros((64, 64, 3), dtype=np.uint8)).shape == (64, 64)

    def test_output_dtype_is_uint8(self):
        assert rgb_to_intensity(np.zeros((64, 64, 3), dtype=np.uint8)).dtype == np.uint8

    def test_black_returns_zero(self):
        assert rgb_to_intensity(_solid(0, 0, 0, size=4)).max() == 0

    def test_white_returns_255(self):
        assert rgb_to_intensity(_solid(255, 255, 255, size=4)).min() == 255

    def test_bt601_luminance_formula(self):
        # L = 0.299×R + 0.587×G + 0.114×B
        # For (100, 150, 200): L = 29.9 + 88.05 + 22.8 = 140.75 → 141
        arr = np.full((1, 1, 3), [100, 150, 200], dtype=np.uint8)
        expected = round(0.299 * 100 + 0.587 * 150 + 0.114 * 200)
        assert rgb_to_intensity(arr)[0, 0] == pytest.approx(expected, abs=1)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — Robustness (color-distribution preservation)
# ══════════════════════════════════════════════════════════════════════════════


class TestRobustness:
    """
    Verify that HSVHash produces low Hamming distance for common
    transformations applied to the same image. Uses synthetic images
    so no external dataset is needed.

    HSVHash encodes color distribution only (no spatial info), so
    resize and blur must not change the hash at all. Color-altering
    transforms are allowed up to ROBUST_THRESHOLD bits of difference.
    """

    ROBUST_THRESHOLD = 8  # max acceptable distance (out of 42 bits)

    def _transform_and_compare(self, original_arr, transform_fn):
        """Apply a PIL transform, convert back to numpy, return Hamming distance."""
        pil = Image.fromarray(original_arr, mode="RGB")
        transformed_arr = np.asarray(transform_fn(pil).convert("RGB"))
        return hamming(hsv_hash(original_arr), hsv_hash(transformed_arr))

    def test_resize_down(self, gradient_arr):
        dist = self._transform_and_compare(
            gradient_arr, lambda img: img.resize((64, 64), Image.LANCZOS)
        )
        assert dist == 0

    def test_resize_up(self, gradient_arr):
        dist = self._transform_and_compare(
            gradient_arr, lambda img: img.resize((256, 256), Image.LANCZOS)
        )
        assert dist == 0

    def test_blur(self, gradient_arr):
        dist = self._transform_and_compare(
            gradient_arr, lambda img: img.filter(ImageFilter.GaussianBlur(radius=2))
        )
        assert dist == 0

    def test_brightness_increase(self, gradient_arr):
        dist = self._transform_and_compare(
            gradient_arr, lambda img: ImageEnhance.Brightness(img).enhance(1.5)
        )
        assert dist <= self.ROBUST_THRESHOLD

    def test_brightness_decrease(self, gradient_arr):
        dist = self._transform_and_compare(
            gradient_arr, lambda img: ImageEnhance.Brightness(img).enhance(0.5)
        )
        assert dist <= self.ROBUST_THRESHOLD

    def test_contrast_increase(self, gradient_arr):
        dist = self._transform_and_compare(
            gradient_arr, lambda img: ImageEnhance.Contrast(img).enhance(1.5)
        )
        assert dist <= self.ROBUST_THRESHOLD

    def test_center_crop(self, gradient_arr):
        dist = self._transform_and_compare(
            gradient_arr, lambda img: img.crop((16, 16, 112, 112))
        )
        assert dist <= self.ROBUST_THRESHOLD

    def test_jpeg_compression(self, gradient_arr, tmp_path_factory):
        """Low-quality JPEG recompression must not exceed the robust threshold."""
        jpeg_path = str(tmp_path_factory.mktemp("jpeg") / "compressed.jpg")
        Image.fromarray(gradient_arr, mode="RGB").save(jpeg_path, "JPEG", quality=20)
        h2 = hsv_hash(np.asarray(Image.open(jpeg_path).convert("RGB")))
        assert hamming(hsv_hash(gradient_arr), h2) <= self.ROBUST_THRESHOLD

    def test_lossless_roundtrip_is_identical(self, gradient_arr, tmp_path_factory):
        """PNG save/reload must reproduce the exact same hash."""
        png_path = tmp_path_factory.mktemp("png") / "copy.png"
        Image.fromarray(gradient_arr, mode="RGB").save(png_path)
        h2 = hsv_hash(np.asarray(Image.open(png_path).convert("RGB")))
        assert hamming(hsv_hash(gradient_arr), h2) == 0
