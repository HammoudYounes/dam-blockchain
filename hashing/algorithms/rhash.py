import numpy as np
from PIL import Image

from algorithms.base import ImageHasher

HASH_SIZE = 64      # total bits — R * A
RINGS = 8           # radial shells
SECTORS = 8         # angular slices
IMG_SIZE = 64


def _load_and_preprocess(image_input: str):

    if isinstance(image_input, str):
        im= Image.open(image_input)
    
    elif isinstance(image_input, Image.Image):
        im = image_input
        
    else:
        raise TypeError("Expected a file path or PIL Image")
    
    im = im.convert("L")
    im = im.resize((IMG_SIZE,IMG_SIZE), Image.LANCZOS)

    return np.array(im, dtype=np.float32)



def _compute_centroid(pixels: np.ndarray):
    rows, cols = np.indices(pixels.shape)   
    total = pixels.sum()
    cy = (rows * pixels).sum() / total      # intensity-weighted mean row
    cx = (cols * pixels).sum() / total      # intensity-weighted mean col
    return (cx + 0.5, cy + 0.5)


def _get_inscribed_radius(cx: float, cy: float, img_size: int):
    return min(cx, img_size - cx, cy, img_size - cy) * 0.92


def _compute_bin_means(pixels: np.ndarray, cx: float, cy: float, max_r: float, rings: int, sectors: int):
    rows, cols = np.indices(pixels.shape)
    px= cols + 0.5
    py = rows + 0.5
    dist = np.sqrt((px - cx)**2 + (py - cy)**2)
    angle = (np.arctan2(py - cy, px - cx) + 2*np.pi) % (2*np.pi)
    mask = dist < max_r
    ring_idx = np.floor(dist / (max_r / rings)).astype(int).clip(0, rings-1)
    sector_idx = np.floor(angle / (2*np.pi / sectors)).astype(int).clip(0, sectors-1)
    bin_means = np.zeros((rings, sectors), dtype=np.float32)

    for ri in range(rings):
        for ai in range(sectors):
            bin_mask = mask & (ring_idx == ri) & (sector_idx == ai)
            vals = pixels[bin_mask]
            if len(vals) > 0:
                bin_means[ri, ai] = vals.mean()
            else:
                bin_means[ri, ai] = 0.0

    return bin_means.flatten()


def _binarise(bin_means: np.ndarray):
    return bin_means > bin_means.mean()


def _radial_bits(image_input) -> np.ndarray:
    pixels = _load_and_preprocess(image_input)
    cx, cy = _compute_centroid(pixels)
    max_r = _get_inscribed_radius(cx, cy, IMG_SIZE)
    bin_means = _compute_bin_means(pixels, cx, cy, max_r, RINGS, SECTORS)
    return _binarise(bin_means)


def compute(image_path: str):
    return _radial_bits(image_path)

def hamming_distance(hash_a: np.ndarray, hash_b: np.ndarray):
    return int(np.sum(hash_a != hash_b))

def similarity(hash_a: np.ndarray, hash_b: np.ndarray):
    return 1.0 - hamming_distance(hash_a, hash_b) / HASH_SIZE


class RadialHash(ImageHasher):
    """
    Radial/sector luminance hash exposed through the common ImageHasher
    interface (compute -> bitstring, inherited hamming_distance / similarity).

    The grayscale image is binned into RINGS radial shells × SECTORS angular
    slices around its intensity-weighted centroid; each bin's mean is
    thresholded against the global mean to give one bit (64 bits total).
    Centring on the centroid is what makes the hash robust to translation and
    mild cropping.

    The module-level ``compute`` / ``hamming_distance`` / ``similarity`` helpers
    (operating on numpy bool arrays) remain available for existing callers.
    """

    HASH_BITS = HASH_SIZE  # 64
    RINGS = RINGS
    SECTORS = SECTORS
    IMG_SIZE = IMG_SIZE

    def compute(self, image_input) -> str:
        return self._to_bitstring(_radial_bits(image_input))
