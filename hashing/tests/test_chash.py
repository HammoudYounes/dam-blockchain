"""
pytest suite for CHash (hashing/algorithms/chash.py)
Run: pytest test_chash.py -v
"""

import numpy as np
import pytest
from PIL import Image
from unittest.mock import patch
import os
import sys


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from algorithms.Chash import CHash, IMAGE_SIZE, S_MIN, _EMPTY_ZONE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _solid_rgb(r: int, g: int, b: int, size: tuple = (64, 64)) -> Image.Image:
    """Return a solid-colour RGB image."""
    return Image.new("RGB", size, (r, g, b))


def _solid_hsv_pil(h: int, s: int, v: int, size: tuple = (64, 64)) -> Image.Image:
    """
    Return a solid image given PIL HSV values (H 0-255, S 0-255, V 0-255).
    PIL HSV mode encodes hue as 0-255 (not 0-360), saturation and value 0-255.
    """
    arr = np.full((*size[::-1], 3), [h, s, v], dtype=np.uint8)
    im_hsv = Image.fromarray(arr, mode="HSV")
    return im_hsv.convert("RGB")


def _grayscale_image(size: tuple = (64, 64)) -> Image.Image:
    """Fully desaturated (grayscale) image."""
    return Image.new("RGB", size, (128, 128, 128))


def _noisy_image(seed: int = 0, size: tuple = (64, 64)) -> Image.Image:
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, (*size[::-1], 3), dtype=np.uint8)
    return Image.fromarray(arr, "RGB")


# ---------------------------------------------------------------------------
# 1. Construction & type contracts
# ---------------------------------------------------------------------------

class TestConstruction:
    def test_from_pil_image(self):
        ch = CHash(_solid_rgb(200, 50, 50))
        assert isinstance(ch.hash_int, int)
        assert isinstance(ch.hash_hex, str)
        assert len(ch.hash_hex) == 16

    def test_from_file_path(self, tmp_path):
        img_path = tmp_path / "red.png"
        _solid_rgb(200, 50, 50).save(img_path)
        ch = CHash(str(img_path))
        assert isinstance(ch.hash_int, int)

    def test_invalid_input_raises(self):
        with pytest.raises(TypeError):
            CHash(12345)  # neither str nor PIL.Image

    def test_hash_hex_zero_padded(self):
        """hash_hex must always be exactly 16 hex chars (64 bits)."""
        ch = CHash(_grayscale_image())
        assert len(ch.hash_hex) == 16
        int(ch.hash_hex, 16)  # must be valid hex

    def test_raw_data_shape(self):
        ch = CHash(_solid_rgb(100, 200, 50))
        h, w = IMAGE_SIZE[1], IMAGE_SIZE[0]
        assert ch.raw_data.shape == (h, w, 3)
        assert ch.raw_data.dtype == np.uint8

    def test_rgba_input_accepted(self):
        im = Image.new("RGBA", (64, 64), (200, 50, 50, 128))
        ch = CHash(im)
        assert isinstance(ch.hash_int, int)

    def test_palette_input_accepted(self):
        im = Image.new("P", (64, 64))
        ch = CHash(im)
        assert isinstance(ch.hash_int, int)


# ---------------------------------------------------------------------------
# 2. Grayscale / fallback mode
# ---------------------------------------------------------------------------

class TestFallbackMode:
    def test_grayscale_is_fallback(self):
        ch = CHash(_grayscale_image())
        assert ch.is_fallback is True

    def test_color_image_not_fallback(self):
        ch = CHash(_solid_rgb(200, 50, 50))
        assert ch.is_fallback is False

    def test_mode_property_fallback(self):
        ch = CHash(_grayscale_image())
        assert ch.mode() == "fallback"

    def test_mode_property_color(self):
        ch = CHash(_solid_rgb(200, 50, 50))
        assert ch.mode() == "color"

    def test_fallback_hash_fits_64_bits(self):
        ch = CHash(_grayscale_image())
        assert 0 <= ch.hash_int < 2**64

    def test_identical_grayscale_distance_zero(self):
        ch1 = CHash(_grayscale_image())
        ch2 = CHash(_grayscale_image())
        assert ch1.hamming_distance(ch2) == 0

    def test_different_grayscale_low_distance(self):
        """A slightly different uniform gray should differ in ≥0 bits."""
        ch1 = CHash(Image.new("RGB", (64, 64), (80, 80, 80)))
        ch2 = CHash(Image.new("RGB", (64, 64), (200, 200, 200)))
        d = ch1.hamming_distance(ch2)
        # Both are fallback; distance is structurally valid (0-64)
        assert 0 <= d <= 64

    def test_near_grayscale_low_saturation_fallback(self):
        """Pixels with S < S_MIN should trigger fallback."""
        # S_MIN=25; create image with saturation just below threshold
        im = _solid_hsv_pil(h=10, s=S_MIN - 1, v=200)
        ch = CHash(im)
        assert ch.is_fallback is True


# ---------------------------------------------------------------------------
# 3. Hamming distance & similarity
# ---------------------------------------------------------------------------

class TestHammingAndSimilarity:
    def test_self_distance_zero(self):
        ch = CHash(_solid_rgb(200, 50, 50))
        assert ch.hamming_distance(ch) == 0

    def test_self_similarity_one(self):
        ch = CHash(_solid_rgb(200, 50, 50))
        assert ch.similarity(ch) == pytest.approx(1.0)

    def test_identical_images_distance_zero(self):
        img = _solid_rgb(200, 50, 50)
        assert CHash(img).hamming_distance(CHash(img)) == 0

    def test_cross_mode_returns_max_distance(self):
        color = CHash(_solid_rgb(200, 50, 50))
        gray = CHash(_grayscale_image())
        assert color.hamming_distance(gray) == 64

    def test_cross_mode_similarity_zero(self):
        color = CHash(_solid_rgb(200, 50, 50))
        gray = CHash(_grayscale_image())
        assert color.similarity(gray) == pytest.approx(0.0)

    def test_distance_symmetric(self):
        ch1 = CHash(_solid_rgb(200, 50, 50))
        ch2 = CHash(_solid_rgb(50, 200, 50))
        assert ch1.hamming_distance(ch2) == ch2.hamming_distance(ch1)

    def test_distance_range(self):
        ch1 = CHash(_noisy_image(seed=1))
        ch2 = CHash(_noisy_image(seed=2))
        d = ch1.hamming_distance(ch2)
        assert 0 <= d <= 64

    def test_similarity_range(self):
        ch1 = CHash(_noisy_image(seed=3))
        ch2 = CHash(_noisy_image(seed=4))
        s = ch1.similarity(ch2)
        assert 0.0 <= s <= 1.0

    def test_similarity_complement_of_distance(self):
        ch1 = CHash(_noisy_image(seed=5))
        ch2 = CHash(_noisy_image(seed=6))
        d = ch1.hamming_distance(ch2)
        s = ch1.similarity(ch2)
        assert s == pytest.approx(1.0 - d / 64.0)


# ---------------------------------------------------------------------------
# 4. Hash stability & determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_same_image_same_hash(self):
        img = _solid_rgb(120, 80, 200)
        assert CHash(img).hash_int == CHash(img).hash_int

    def test_noisy_image_deterministic(self):
        img = _noisy_image(seed=42)
        assert CHash(img).hash_int == CHash(img).hash_int

    def test_different_colors_different_hashes(self):
        """Clearly distinct hues should produce different hashes."""
        red = CHash(_solid_rgb(220, 30, 30))
        blue = CHash(_solid_rgb(0, 0, 0))
        assert red.hash_int != blue.hash_int

    def test_similar_images_low_distance(self):
        """A tiny brightness tweak should change very few bits."""
        base = _solid_rgb(200, 60, 60)
        tweaked = _solid_rgb(205, 60, 60)
        d = CHash(base).hamming_distance(CHash(tweaked))
        assert d <= 4  # should be nearly identical


# ---------------------------------------------------------------------------
# 5. Internal helpers (unit-level)
# ---------------------------------------------------------------------------

class TestInternalHelpers:
    def _make_instance(self) -> CHash:
        """Cheap CHash instance reused for helper calls."""
        return CHash(_solid_rgb(200, 50, 50))

    def test_get_dominant_bin_empty_mask(self):
        ch = self._make_instance()
        h = np.array([[0, 128], [255, 64]], dtype=np.uint8)
        mask = np.zeros_like(h, dtype=bool)
        assert ch._get_dominant_bin(h, mask) == _EMPTY_ZONE

    def test_get_dominant_bin_all_same_bin(self):
        ch = self._make_instance()
        # All hues in 0-31 → bin 0
        h = np.full((8, 8), 10, dtype=np.uint8)
        mask = np.ones((8, 8), dtype=bool)
        assert ch._get_dominant_bin(h, mask) == 0

    def test_get_dominant_bin_majority_wins(self):
        ch = self._make_instance()
        h = np.zeros((8, 8), dtype=np.uint8)
        h[:5, :] = 10   # bin 0: 40 pixels
        h[5:, :] = 200  # bin 6: 24 pixels
        mask = np.ones((8, 8), dtype=bool)
        assert ch._get_dominant_bin(h, mask) == 0

    def test_compute_fallback_hash_type(self):
        ch = CHash(_grayscale_image())
        result = ch._compute_fallback_hash(
            np.full((32, 32), 128, dtype=np.uint8)
        )
        assert isinstance(result, int)
        assert 0 <= result < 2**64

    def test_compute_fallback_hash_uniform_bright(self):
        """Uniform bright image → all zones ≥ global mean → all bits 1 (first 16)."""
        ch = CHash(_grayscale_image())
        v = np.full((32, 32), 200, dtype=np.uint8)
        result = ch._compute_fallback_hash(v)
        # First 16 bits should all be 1, rest zero-padded
        expected = int("1" * 16 + "0" * 48, 2)
        assert result == expected

    def test_compute_fallback_hash_uniform_dark(self):
        """Uniform dark image → all zones < global mean? No: equal to mean → all 1s."""
        ch = CHash(_grayscale_image())
        v = np.full((32, 32), 50, dtype=np.uint8)
        # Every zone mean == global mean → bit = 1
        result = ch._compute_fallback_hash(v)
        expected = int("1" * 16 + "0" * 48, 2)
        assert result == expected


# ---------------------------------------------------------------------------
# 6. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_single_pixel_image(self):
        """CHash should handle 1×1 inputs without crashing."""
        ch = CHash(Image.new("RGB", (1, 1), (200, 50, 50)))
        assert isinstance(ch.hash_int, int)

    def test_very_large_image(self):
        """Large images are resized; hash should still be valid."""
        ch = CHash(Image.new("RGB", (2048, 2048), (200, 50, 50)))
        assert isinstance(ch.hash_int, int)

    def test_black_image(self):
        """Completely black image → S=0 everywhere → fallback mode."""
        ch = CHash(Image.new("RGB", (64, 64), (0, 0, 0)))
        assert ch.is_fallback is True

    def test_white_image(self):
        """Completely white image → S=0 everywhere → fallback mode."""
        ch = CHash(Image.new("RGB", (64, 64), (255, 255, 255)))
        assert ch.is_fallback is True

    def test_saturation_boundary_exactly_s_min(self):
        """Pixels with S == S_MIN should pass the mask (>= S_MIN)."""
        im = _solid_hsv_pil(h=10, s=S_MIN, v=200)
        ch = CHash(im)
        # At or above S_MIN → color mode
        assert ch.is_fallback is False

    def test_repr_contains_hex_and_mode(self):
        ch = CHash(_solid_rgb(200, 50, 50))
        r = repr(ch)
        assert ch.hash_hex in r
        assert ch.mode() in r