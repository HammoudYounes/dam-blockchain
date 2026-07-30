import numpy as np
from PIL import Image
from .base import ImageHasher

class RadialHash(ImageHasher):
    """
    Radial/sector luminance hash.
    """

    HASH_BITS = 64
    RINGS = 8
    SECTORS = 8
    IMG_SIZE = 64

    def __init__(self, multiplier: float = 1.12):
        self.multiplier = multiplier

    def _compute_centroid(self, pixels: np.ndarray):
        rows, cols = np.indices(pixels.shape)
        total = pixels.sum()
        if total == 0:
            return (self.IMG_SIZE / 2, self.IMG_SIZE / 2)
        cy = (rows * pixels).sum() / total
        cx = (cols * pixels).sum() / total
        return (cx + 0.5, cy + 0.5)

    def _get_inscribed_radius(self, cx: float, cy: float):
        return min(cx, self.IMG_SIZE - cx, cy, self.IMG_SIZE - cy) * self.multiplier

    def _compute_bin_means(self, pixels: np.ndarray, cx: float, cy: float, max_r: float):
        rows, cols = np.indices(pixels.shape)
        px = cols + 0.5
        py = rows + 0.5
        dist = np.sqrt((px - cx)**2 + (py - cy)**2)
        angle = (np.arctan2(py - cy, px - cx) + 2 * np.pi) % (2 * np.pi)
        mask = dist < max_r
        ring_idx = np.floor(dist / (max_r / self.RINGS)).astype(int).clip(0, self.RINGS - 1)
        sector_idx = np.floor(angle / (2 * np.pi / self.SECTORS)).astype(int).clip(0, self.SECTORS - 1)
        bin_means = np.zeros((self.RINGS, self.SECTORS), dtype=np.float64)

        for ri in range(self.RINGS):
            for ai in range(self.SECTORS):
                bin_mask = mask & (ring_idx == ri) & (sector_idx == ai)
                vals = pixels[bin_mask]
                if len(vals) > 0:
                    bin_means[ri, ai] = vals.mean()
                else:
                    bin_means[ri, ai] = 0.0

        return bin_means.flatten()

    def compute(self, image_input) -> str:
        pixels = self._load_grayscale(image_input, (self.IMG_SIZE, self.IMG_SIZE))
        cx, cy = self._compute_centroid(pixels)
        max_r = self._get_inscribed_radius(cx, cy)
        bin_means = self._compute_bin_means(pixels, cx, cy, max_r)
        bits = self._binarise(bin_means)
        return self._to_bitstring(bits)
