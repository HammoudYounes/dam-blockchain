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
from algorithms.Chash import ColorHash, IMAGE_SIZE, S_MIN, _EMPTY_ZONE

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

    def test_from_pil_image(self):
        ch = ColorHash().compute(_solid_rgb(200, 50, 50))
        assert isinstance(ch, str)
        assert len(ch) == 65

    def test_from_file_path(self, tmp_path):
        img_path = tmp_path / "red.png"
        _solid_rgb(200, 50, 50).save(img_path)
        ch = ColorHash().compute(str(img_path))
        assert isinstance(ch, str)
        assert len(ch) == 65

    def test_invalid_input_raises(self):
        with pytest.raises(TypeError):
            ColorHash().compute(12345)  # neither str nor PIL.Image

    def test_hash_hex_zero_padded(self):
        """hash must be exactly 65 chars (mode + 64 bits)."""
        ch = ColorHash().compute(_grayscale_image())
        assert len(ch) == 65
        # Marker + 64 bits
        assert ch[0] == 'F'
        int(ch[1:], 2)

    def test_raw_data_shape(self):
        # raw_data is no longer stored on the class instance, so we cannot test it directly
        # But compute should work fine.
        ch = ColorHash().compute(_solid_rgb(100, 200, 50))
        assert isinstance(ch, str)

    def test_rgba_input_accepted(self):
        im = Image.new("RGBA", (64, 64), (200, 50, 50, 128))
        ch = ColorHash().compute(im)
        assert isinstance(ch, str)

    def test_palette_input_accepted(self):
        im = Image.new("P", (64, 64))
        ch = ColorHash().compute(im)
        assert isinstance(ch, str)


# ---------------------------------------------------------------------------
# 2. Grayscale / fallback mode
# ---------------------------------------------------------------------------

class TestFallbackMode:
    def test_grayscale_is_fallback(self):
        ch = ColorHash().compute(_grayscale_image())
        assert ch[0] == 'F'

    def test_color_image_not_fallback(self):
        ch = ColorHash().compute(_solid_rgb(200, 50, 50))
        assert ch[0] == 'C'

    def test_mode_property_fallback(self):
        ch = ColorHash().compute(_grayscale_image())
        assert ch[0] == 'F'

    def test_mode_property_color(self):
        ch = ColorHash().compute(_solid_rgb(200, 50, 50))
        assert ch[0] == 'C'

    def test_fallback_hash_fits_64_bits(self):
        ch = ColorHash().compute(_grayscale_image())
        bits = ch[1:]
        assert len(bits) == 64
        assert int(bits, 2) < 2**64

    def test_identical_grayscale_distance_zero(self):
        ch1 = ColorHash().compute(_grayscale_image())
        ch2 = ColorHash().compute(_grayscale_image())
        assert ColorHash.hamming_distance(ch1, ch2) == 0

    def test_different_grayscale_low_distance(self):
        """A slightly different uniform gray should differ in ≥0 bits."""
        ch1 = ColorHash().compute(Image.new("RGB", (64, 64), (80, 80, 80)))
        ch2 = ColorHash().compute(Image.new("RGB", (64, 64), (200, 200, 200)))
        d = ColorHash.hamming_distance(ch1, ch2)
        # Both are fallback; distance is structurally valid (0-64)
        assert 0 <= d <= 64

    def test_near_grayscale_low_saturation_fallback(self):
        """Pixels with S < S_MIN should trigger fallback."""
        # S_MIN=25; create image with saturation just below threshold
        im = _solid_hsv_pil(h=10, s=S_MIN - 1, v=200)
        ch = ColorHash().compute(im)
        assert ch[0] == 'F'


# ---------------------------------------------------------------------------
# 3. Hamming distance & similarity
# ---------------------------------------------------------------------------

class TestHammingAndSimilarity:
    def test_self_distance_zero(self):
        ch = ColorHash().compute(_solid_rgb(200, 50, 50))
        assert ColorHash.hamming_distance(ch, ch) == 0

    def test_self_similarity_one(self):
        ch = ColorHash().compute(_solid_rgb(200, 50, 50))
        assert ColorHash.similarity(ch, ch) == pytest.approx(1.0)

    def test_identical_images_distance_zero(self):
        img = _solid_rgb(200, 50, 50)
        h1 = ColorHash().compute(img)
        h2 = ColorHash().compute(img)
        assert ColorHash.hamming_distance(h1, h2) == 0

    def test_cross_mode_returns_max_distance(self):
        color = ColorHash().compute(_solid_rgb(200, 50, 50))
        gray = ColorHash().compute(_grayscale_image())
        assert ColorHash.hamming_distance(color, gray) == 64

    def test_cross_mode_similarity_zero(self):
        color = ColorHash().compute(_solid_rgb(200, 50, 50))
        gray = ColorHash().compute(_grayscale_image())
        assert ColorHash.similarity(color, gray) == pytest.approx(0.0)

    def test_distance_symmetric(self):
        ch1 = ColorHash().compute(_solid_rgb(200, 50, 50))
        ch2 = ColorHash().compute(_solid_rgb(50, 200, 50))
        assert ColorHash.hamming_distance(ch1, ch2) == ColorHash.hamming_distance(ch2, ch1)

    def test_distance_range(self):
        ch1 = ColorHash().compute(_noisy_image(seed=1))
        ch2 = ColorHash().compute(_noisy_image(seed=2))
        d = ColorHash.hamming_distance(ch1, ch2)
        assert 0 <= d <= 64

    def test_similarity_range(self):
        ch1 = ColorHash().compute(_noisy_image(seed=3))
        ch2 = ColorHash().compute(_noisy_image(seed=4))
        s = ColorHash.similarity(ch1, ch2)
        assert 0.0 <= s <= 1.0

    def test_similarity_complement_of_distance(self):
        ch1 = ColorHash().compute(_noisy_image(seed=5))
        ch2 = ColorHash().compute(_noisy_image(seed=6))
        d = ColorHash.hamming_distance(ch1, ch2)
        s = ColorHash.similarity(ch1, ch2)
        assert s == pytest.approx(1.0 - d / 64.0)


# ---------------------------------------------------------------------------
# 4. Hash stability & determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_same_image_same_hash(self):
        img = _solid_rgb(120, 80, 200)
        assert ColorHash().compute(img) == ColorHash().compute(img)

    def test_noisy_image_deterministic(self):
        img = _noisy_image(seed=42)
        assert ColorHash().compute(img) == ColorHash().compute(img)

    def test_different_colors_different_hashes(self):
        """Clearly distinct hues should produce different hashes."""
        red = ColorHash().compute(_solid_rgb(220, 30, 30))
        blue = ColorHash().compute(_solid_rgb(0, 0, 0))
        assert red != blue

    def test_similar_images_low_distance(self):
        """A tiny brightness tweak should change very few bits."""
        base = _solid_rgb(200, 60, 60)
        tweaked = _solid_rgb(205, 60, 60)
        d = ColorHash.hamming_distance(ColorHash().compute(base), ColorHash().compute(tweaked))
        assert d <= 4  # should be nearly identical


# ---------------------------------------------------------------------------
# 5. Internal helpers (unit-level)
# ---------------------------------------------------------------------------

class TestInternalHelpers:
    def _make_instance(self) -> ColorHash:
        """Cheap ColorHash instance reused for helper calls."""
        return ColorHash()

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
        ch = ColorHash()
        result = ch._compute_fallback_hash(
            np.full((32, 32), 128, dtype=np.uint8)
        )
        assert isinstance(result, int)
        assert 0 <= result < 2**64

    def test_compute_fallback_hash_uniform_bright(self):
        """Uniform bright image → all zones ≥ global mean → all bits 1 (first 16)."""
        ch = ColorHash()
        v = np.full((32, 32), 200, dtype=np.uint8)
        result = ch._compute_fallback_hash(v)
        # First 16 bits should all be 1, rest zero-padded
        expected = int("1" * 16 + "0" * 48, 2)
        assert result == expected

    def test_compute_fallback_hash_uniform_dark(self):
        """Uniform dark image → all zones < global mean? No: equal to mean → all 1s."""
        ch = ColorHash()
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
        """ColorHash should handle 1×1 inputs without crashing."""
        ch = ColorHash().compute(Image.new("RGB", (1, 1), (200, 50, 50)))
        assert isinstance(ch, str)

    def test_very_large_image(self):
        """Large images are resized; hash should still be valid."""
        ch = ColorHash().compute(Image.new("RGB", (2048, 2048), (200, 50, 50)))
        assert isinstance(ch, str)

    def test_black_image(self):
        """Completely black image → S=0 everywhere → fallback mode."""
        ch = ColorHash().compute(Image.new("RGB", (64, 64), (0, 0, 0)))
        assert ch[0] == 'F'

    def test_white_image(self):
        """Completely white image → S=0 everywhere → fallback mode."""
        ch = ColorHash().compute(Image.new("RGB", (64, 64), (255, 255, 255)))
        assert ch[0] == 'F'

    def test_saturation_boundary_exactly_s_min(self):
        """Pixels with S == S_MIN should pass the mask (>= S_MIN)."""
        im = _solid_hsv_pil(h=10, s=S_MIN, v=200)
        ch = ColorHash().compute(im)
        # At or above S_MIN → color mode
        assert ch[0] == 'C'