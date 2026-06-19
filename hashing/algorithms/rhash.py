import numpy as np
from PIL import Image

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


def compute(image_path: str):
    pixels = _load_and_preprocess(image_path)
    cx, cy = _compute_centroid(pixels)
    max_r = _get_inscribed_radius(cx, cy, IMG_SIZE)
    bin_means = _compute_bin_means(pixels, cx, cy, max_r, RINGS, SECTORS)
    return _binarise(bin_means)

def hamming_distance(hash_a: np.ndarray, hash_b: np.ndarray):
    return int(np.sum(hash_a != hash_b))

def similarity(hash_a: np.ndarray, hash_b: np.ndarray):
    return 1.0 - hamming_distance(hash_a, hash_b) / HASH_SIZE
