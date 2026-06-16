"""
Pytest unit tests for the RHash algorithm.

Tests the public API: compute(), hamming_distance(), similarity().
No dataset required — all test images are generated synthetically.

Run from the hashing/ directory:
    pytest tests/test_rhash.py -v
"""

import os
import sys

import numpy as np
import pytest
from PIL import Image, ImageEnhance, ImageFilter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from algorithms.rhash import compute, hamming_distance, similarity


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES — synthetic test images
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def gradient_image(tmp_path_factory):
    """256×256 horizontal gradient — a realistic luminance pattern."""
    path = str(tmp_path_factory.mktemp("images") / "gradient.png")
    arr = np.tile(np.arange(256, dtype=np.uint8), (256, 1))
    Image.fromarray(arr, mode="L").save(path)
    return path


@pytest.fixture(scope="module")
def white_image(tmp_path_factory):
    """256×256 solid white image."""
    path = str(tmp_path_factory.mktemp("images") / "white.png")
    arr = np.full((256, 256), 255, dtype=np.uint8)
    Image.fromarray(arr, mode="L").save(path)
    return path


@pytest.fixture(scope="module")
def noise_image(tmp_path_factory):
    """256×256 random noise — structurally unrelated to gradient."""
    path = str(tmp_path_factory.mktemp("images") / "noise.png")
    rng = np.random.default_rng(42)
    arr = rng.integers(0, 256, size=(256, 256), dtype=np.uint8)
    Image.fromarray(arr, mode="L").save(path)
    return path


@pytest.fixture(scope="module")
def color_image(tmp_path_factory):
    """256×256 RGB image with a diagonal gradient — tests color input."""
    path = str(tmp_path_factory.mktemp("images") / "color.png")
    r = np.tile(np.arange(256, dtype=np.uint8), (256, 1))
    g = np.tile(np.arange(255, -1, -1, dtype=np.uint8), (256, 1))
    b = np.fromfunction(lambda y, x: ((x + y) / 2) % 256, (256, 256)).astype(np.uint8)
    Image.fromarray(np.stack([r, g, b], axis=-1), mode="RGB").save(path)
    return path


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — compute()
# ══════════════════════════════════════════════════════════════════════════════


class TestCompute:
    """Tests for the compute() function."""

    def test_returns_boolean_array(self, gradient_image):
        h = compute(gradient_image)
        assert isinstance(h, np.ndarray)
        assert h.dtype == bool

    def test_hash_length_is_64(self, gradient_image):
        h = compute(gradient_image)
        assert len(h) == 64, f"Expected 64 bits (8 rings × 8 sectors), got {len(h)}"

    def test_only_boolean_values(self, gradient_image):
        h = compute(gradient_image)
        assert all(v in (True, False) for v in h)

    def test_deterministic(self, gradient_image):
        assert np.array_equal(compute(gradient_image), compute(gradient_image))

    def test_accepts_pil_image(self, gradient_image):
        img = Image.open(gradient_image)
        assert np.array_equal(compute(gradient_image), compute(img))

    def test_accepts_rgb_input(self, color_image):
        h = compute(color_image)
        assert len(h) == 64

    def test_different_images_produce_different_hashes(self, gradient_image, noise_image):
        assert not np.array_equal(compute(gradient_image), compute(noise_image))

    def test_invalid_path_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            compute("/nonexistent/path/image.jpg")

    def test_invalid_type_raises_type_error(self):
        with pytest.raises(TypeError):
            compute(42)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — hamming_distance()
# ══════════════════════════════════════════════════════════════════════════════


class TestHammingDistance:
    """Tests for the hamming_distance() function."""

    def test_identical_hashes_return_zero(self):
        h = np.ones(64, dtype=bool)
        assert hamming_distance(h, h) == 0

    def test_completely_opposite_returns_64(self):
        h1 = np.ones(64, dtype=bool)
        h2 = np.zeros(64, dtype=bool)
        assert hamming_distance(h1, h2) == 64

    def test_single_bit_difference(self):
        h1 = np.zeros(64, dtype=bool)
        h2 = np.zeros(64, dtype=bool)
        h2[0] = True
        assert hamming_distance(h1, h2) == 1

    def test_known_distance(self):
        h1 = np.zeros(64, dtype=bool)
        h2 = np.zeros(64, dtype=bool)
        h2[:8] = True
        assert hamming_distance(h1, h2) == 8

    def test_symmetric(self):
        rng = np.random.default_rng(0)
        h1 = rng.integers(0, 2, size=64).astype(bool)
        h2 = rng.integers(0, 2, size=64).astype(bool)
        assert hamming_distance(h1, h2) == hamming_distance(h2, h1)

    def test_returns_integer(self):
        h = np.ones(64, dtype=bool)
        assert isinstance(hamming_distance(h, h), int)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — similarity()
# ══════════════════════════════════════════════════════════════════════════════


class TestSimilarity:
    """Tests for the similarity() function."""

    def test_identical_returns_one(self):
        h = np.ones(64, dtype=bool)
        assert similarity(h, h) == 1.0

    def test_opposite_returns_zero(self):
        h1 = np.ones(64, dtype=bool)
        h2 = np.zeros(64, dtype=bool)
        assert similarity(h1, h2) == 0.0

    def test_score_in_range(self, gradient_image, noise_image):
        h1 = compute(gradient_image)
        h2 = compute(noise_image)
        score = similarity(h1, h2)
        assert 0.0 <= score <= 1.0

    def test_score_consistent_with_distance(self):
        h1 = np.ones(64, dtype=bool)
        h2 = np.ones(64, dtype=bool)
        h2[:10] = False
        assert similarity(h1, h2) == pytest.approx(1.0 - 10 / 64)

    def test_returns_float(self):
        h = np.ones(64, dtype=bool)
        assert isinstance(similarity(h, h), float)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Robustness (transformations on synthetic images)
# ══════════════════════════════════════════════════════════════════════════════


class TestRobustness:
    """
    Verify that RHash produces low Hamming distance for common
    transformations applied to the same image. Uses synthetic images
    so no external dataset is needed.
    """

    ROBUST_THRESHOLD = 10

    def _transform_and_compare(self, image_path, transform_fn):
        """Apply a transform via PIL, compute both hashes, return distance."""
        original = Image.open(image_path)
        transformed = transform_fn(original)
        h1 = compute(original)
        h2 = compute(transformed)
        return hamming_distance(h1, h2)

    def test_resize_down(self, gradient_image):
        dist = self._transform_and_compare(
            gradient_image, lambda img: img.resize((128, 128), Image.LANCZOS)
        )
        assert dist <= self.ROBUST_THRESHOLD

    def test_resize_up(self, gradient_image):
        dist = self._transform_and_compare(
            gradient_image, lambda img: img.resize((512, 512), Image.LANCZOS)
        )
        assert dist <= self.ROBUST_THRESHOLD

    def test_brightness_increase(self, gradient_image):
        dist = self._transform_and_compare(
            gradient_image, lambda img: ImageEnhance.Brightness(img.convert("RGB")).enhance(1.5)
        )
        assert dist <= self.ROBUST_THRESHOLD

    def test_brightness_decrease(self, gradient_image):
        dist = self._transform_and_compare(
            gradient_image, lambda img: ImageEnhance.Brightness(img.convert("RGB")).enhance(0.5)
        )
        assert dist <= self.ROBUST_THRESHOLD

    def test_contrast_increase(self, gradient_image):
        dist = self._transform_and_compare(
            gradient_image, lambda img: ImageEnhance.Contrast(img.convert("RGB")).enhance(1.5)
        )
        assert dist <= self.ROBUST_THRESHOLD

    def test_blur(self, gradient_image):
        dist = self._transform_and_compare(
            gradient_image, lambda img: img.filter(ImageFilter.GaussianBlur(radius=2))
        )
        assert dist <= self.ROBUST_THRESHOLD

    def test_jpeg_compression(self, gradient_image, tmp_path_factory):
        """Save as low-quality JPEG, reload, compare."""
        jpeg_path = str(tmp_path_factory.mktemp("jpeg") / "compressed.jpg")
        img = Image.open(gradient_image).convert("RGB")
        img.save(jpeg_path, "JPEG", quality=20)
        h1 = compute(gradient_image)
        h2 = compute(jpeg_path)
        assert hamming_distance(h1, h2) <= self.ROBUST_THRESHOLD

    def test_grayscale_conversion(self, color_image):
        """Converting an RGB image to grayscale should not change its hash."""
        img = Image.open(color_image)
        gray = img.convert("L")
        h1 = compute(img)
        h2 = compute(gray)
        assert hamming_distance(h1, h2) == 0