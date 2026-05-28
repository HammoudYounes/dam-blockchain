"""
Pytest unit tests for the sHash (similarity / gradient hash) algorithm.

Tests the public API: compute(), hamming_distance(), similarity().
Synthetic tests run without any dataset; the dataset section uses
the own/ collection to sweep classification thresholds.

Run from the hashing/ directory:
    pytest tests/test_shash.py -v
"""

import csv
import os
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageEnhance, ImageFilter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from algorithms.shash import compute, hamming_distance, similarity


HASH_BITS = 64
BEST_F1_THRESHOLD = 29
DATASET_DIR = Path(__file__).resolve().parents[1] / "data" / "own"
VARIANTS_CSV = DATASET_DIR / "variants.csv"


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES — synthetic test images
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def gradient_image(tmp_path_factory):
    """256x256 horizontal gradient — ideal input for a horizontal-diff hash."""
    path = str(tmp_path_factory.mktemp("images") / "gradient.png")
    arr = np.tile(np.arange(256, dtype=np.uint8), (256, 1))
    Image.fromarray(arr, mode="L").save(path)
    return path


@pytest.fixture(scope="module")
def white_image(tmp_path_factory):
    """256x256 solid white image."""
    path = str(tmp_path_factory.mktemp("images") / "white.png")
    arr = np.full((256, 256), 255, dtype=np.uint8)
    Image.fromarray(arr, mode="L").save(path)
    return path


@pytest.fixture(scope="module")
def noise_image(tmp_path_factory):
    """256x256 random noise — structurally unrelated to gradient."""
    path = str(tmp_path_factory.mktemp("images") / "noise.png")
    rng = np.random.default_rng(42)
    arr = rng.integers(0, 256, size=(256, 256), dtype=np.uint8)
    Image.fromarray(arr, mode="L").save(path)
    return path


@pytest.fixture(scope="module")
def color_image(tmp_path_factory):
    """256x256 RGB image with a diagonal gradient — tests color input."""
    path = str(tmp_path_factory.mktemp("images") / "color.png")
    r = np.tile(np.arange(256, dtype=np.uint8), (256, 1))
    g = np.tile(np.arange(255, -1, -1, dtype=np.uint8), (256, 1))
    b = np.fromfunction(lambda y, x: ((x + y) / 2) % 256, (256, 256)).astype(np.uint8)
    Image.fromarray(np.stack([r, g, b], axis=-1), mode="RGB").save(path)
    return path


# ══════════════════════════════════════════════════════════════════════════════
# Dataset helpers — load own/variants.csv and sweep thresholds
# ══════════════════════════════════════════════════════════════════════════════


def _load_dataset_pairs():
    positives = []
    groups = {}
    with VARIANTS_CSV.open(newline="") as variants_file:
        for row in csv.DictReader(variants_file):
            original = row["original_image"]
            variant = row["variant_image"]
            positives.append((original, variant, row["transformation"]))
            groups.setdefault(original, []).append(variant)

    negatives = []
    for original_a, original_b in combinations(groups.keys(), 2):
        variants_a = groups[original_a]
        variants_b = groups[original_b]
        negatives.append((original_a, original_b, "cross_image"))
        negatives.extend((original_a, variant_b, "cross_image") for variant_b in variants_b)
        negatives.extend((original_b, variant_a, "cross_image") for variant_a in variants_a)

    return positives, negatives


def _dataset_distance(path_a, path_b):
    return hamming_distance(compute(str(DATASET_DIR / path_a)), compute(str(DATASET_DIR / path_b)))


def _evaluate_threshold(distances, labels, threshold):
    predictions = (distances <= threshold).astype(int)
    tp = int(((predictions == 1) & (labels == 1)).sum())
    tn = int(((predictions == 0) & (labels == 0)).sum())
    fp = int(((predictions == 1) & (labels == 0)).sum())
    fn = int(((predictions == 0) & (labels == 1)).sum())
    accuracy = (tp + tn) / len(labels)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "threshold": threshold,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
    }


def _sweep_dataset_thresholds():
    positives, negatives = _load_dataset_pairs()
    positive_distances = np.array([_dataset_distance(a, b) for a, b, _ in positives])
    negative_distances = np.array([_dataset_distance(a, b) for a, b, _ in negatives])
    distances = np.concatenate([positive_distances, negative_distances])
    labels = np.concatenate(
        [np.ones(len(positive_distances), dtype=int), np.zeros(len(negative_distances), dtype=int)]
    )
    results = [_evaluate_threshold(distances, labels, threshold) for threshold in range(HASH_BITS + 1)]
    return positives, negatives, positive_distances, negative_distances, results


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — compute()
# ══════════════════════════════════════════════════════════════════════════════


class TestCompute:
    """Tests for the compute() function."""

    def test_returns_string(self, gradient_image):
        assert isinstance(compute(gradient_image), str)

    def test_hash_length_is_64(self, gradient_image):
        h = compute(gradient_image)
        assert len(h) == HASH_BITS, f"Expected {HASH_BITS} bits, got {len(h)}"

    def test_only_binary_characters(self, gradient_image):
        h = compute(gradient_image)
        assert all(c in ("0", "1") for c in h)

    def test_deterministic(self, gradient_image):
        assert compute(gradient_image) == compute(gradient_image)

    def test_accepts_pil_image(self, gradient_image):
        img = Image.open(gradient_image)
        assert compute(gradient_image) == compute(img)

    def test_accepts_rgb_input(self, color_image):
        assert len(compute(color_image)) == HASH_BITS

    def test_different_images_produce_different_hashes(self, gradient_image, noise_image):
        assert compute(gradient_image) != compute(noise_image)

    def test_monotonic_gradient_produces_all_zeros(self, gradient_image):
        # sHash flags left>right; a strictly increasing gradient => every bit 0.
        assert compute(gradient_image) == "0" * HASH_BITS

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
        h = "1" * HASH_BITS
        assert hamming_distance(h, h) == 0

    def test_completely_opposite_returns_full_length(self):
        assert hamming_distance("1" * HASH_BITS, "0" * HASH_BITS) == HASH_BITS

    def test_single_bit_difference(self):
        h1 = "0" * HASH_BITS
        h2 = "1" + "0" * (HASH_BITS - 1)
        assert hamming_distance(h1, h2) == 1

    def test_known_distance(self):
        h1 = "11001100" + "0" * 56
        h2 = "00110011" + "0" * 56
        assert hamming_distance(h1, h2) == 8

    def test_symmetric(self):
        h1 = "10101" + "0" * 59
        h2 = "01010" + "0" * 59
        assert hamming_distance(h1, h2) == hamming_distance(h2, h1)

    def test_length_mismatch_raises_value_error(self):
        with pytest.raises(ValueError):
            hamming_distance("101", "10")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — similarity()
# ══════════════════════════════════════════════════════════════════════════════


class TestSimilarity:
    """Tests for the similarity() function."""

    def test_identical_returns_one(self):
        h = "1" * HASH_BITS
        assert similarity(h, h) == 1.0

    def test_opposite_returns_zero(self):
        assert similarity("1" * HASH_BITS, "0" * HASH_BITS) == 0.0

    def test_score_in_range(self, gradient_image, noise_image):
        h1 = compute(gradient_image)
        h2 = compute(noise_image)
        score = similarity(h1, h2)
        assert 0.0 <= score <= 1.0

    def test_score_consistent_with_distance(self):
        h1 = "1" * HASH_BITS
        h2 = "0" * 10 + "1" * 54
        assert similarity(h1, h2) == pytest.approx(1.0 - 10 / HASH_BITS)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Robustness (transformations on synthetic images)
# ══════════════════════════════════════════════════════════════════════════════


class TestSyntheticRobustness:
    """
    Verify sHash produces low Hamming distance for transformations
    that preserve horizontal-gradient structure: resize, brightness,
    contrast, blur, JPEG. Spatial transforms (flip/rotate) are
    intentionally not tested — sHash is known to fail those.
    """

    ROBUST_THRESHOLD = 10

    def _transform_and_compare(self, image_path, transform_fn):
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
            gradient_image,
            lambda img: ImageEnhance.Brightness(img.convert("RGB")).enhance(1.5),
        )
        assert dist <= self.ROBUST_THRESHOLD

    def test_brightness_decrease(self, gradient_image):
        dist = self._transform_and_compare(
            gradient_image,
            lambda img: ImageEnhance.Brightness(img.convert("RGB")).enhance(0.5),
        )
        assert dist <= self.ROBUST_THRESHOLD

    def test_contrast_increase(self, gradient_image):
        dist = self._transform_and_compare(
            gradient_image,
            lambda img: ImageEnhance.Contrast(img.convert("RGB")).enhance(1.5),
        )
        assert dist <= self.ROBUST_THRESHOLD

    def test_blur(self, gradient_image):
        dist = self._transform_and_compare(
            gradient_image, lambda img: img.filter(ImageFilter.GaussianBlur(radius=2))
        )
        assert dist <= self.ROBUST_THRESHOLD

    def test_jpeg_compression(self, gradient_image, tmp_path_factory):
        jpeg_path = str(tmp_path_factory.mktemp("jpeg") / "compressed.jpg")
        img = Image.open(gradient_image).convert("RGB")
        img.save(jpeg_path, "JPEG", quality=20)
        h1 = compute(gradient_image)
        h2 = compute(jpeg_path)
        assert hamming_distance(h1, h2) <= self.ROBUST_THRESHOLD

    def test_grayscale_conversion(self, color_image):
        img = Image.open(color_image)
        gray = img.convert("L")
        h1 = compute(img)
        h2 = compute(gray)
        assert hamming_distance(h1, h2) == 0


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Known weaknesses (sHash should FAIL these)
# ══════════════════════════════════════════════════════════════════════════════


class TestKnownWeaknesses:
    """
    sHash encodes only the horizontal gradient sign, so it is NOT invariant
    to horizontal flips. These tests document the limitation and will
    notice if the algorithm is ever changed to fix it.
    """

    def test_horizontal_flip_is_near_bit_inversion(self, gradient_image):
        original = Image.open(gradient_image)
        flipped = original.transpose(Image.FLIP_LEFT_RIGHT)
        # Flipping a monotonic gradient inverts every horizontal diff.
        assert hamming_distance(compute(original), compute(flipped)) == HASH_BITS


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — Dataset sweep (own/variants.csv)
# ══════════════════════════════════════════════════════════════════════════════


class TestDatasetVariants:
    def test_variants_csv_exists(self):
        assert VARIANTS_CSV.exists()

    def test_dataset_has_positive_and_negative_pairs(self):
        positives, negatives = _load_dataset_pairs()
        assert len(positives) == 54
        assert len(negatives) == 111

    def test_best_f1_threshold_was_swept_from_current_dataset(self):
        _, _, _, _, results = _sweep_dataset_thresholds()
        best_f1 = max(results, key=lambda item: (item["f1"], item["accuracy"]))
        best_accuracy = max(results, key=lambda item: (item["accuracy"], item["f1"]))

        assert best_f1["threshold"] == BEST_F1_THRESHOLD
        assert best_accuracy["threshold"] == BEST_F1_THRESHOLD
        assert best_f1["tp"] == 50
        assert best_f1["fp"] == 1
        assert best_f1["recall"] == pytest.approx(50 / 54)
        assert best_f1["precision"] == pytest.approx(50 / 51)

    def test_full_recall_threshold_is_not_the_best_f1_threshold(self):
        _, _, positive_distances, _, results = _sweep_dataset_thresholds()
        full_recall_threshold = int(positive_distances.max())
        full_recall_result = results[full_recall_threshold]
        best_f1_result = results[BEST_F1_THRESHOLD]

        assert full_recall_threshold == 31
        assert full_recall_result["recall"] == 1.0
        assert full_recall_result["fp"] == 6
        assert best_f1_result["f1"] > full_recall_result["f1"]
