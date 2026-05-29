"""
HSVHash — HSV Color Hashing, matching the NFT-duplication paper.

This reproduces the `colorhash` algorithm (Buchner's imagehash library, ref [37]/[39]):
the image is converted to HSV, every pixel is binned by its color fraction
(black / gray / 6 hue bins for faint colors / 6 hue bins for bright colors),
and each of the 14 fractions is quantized to `binbits` bits.

    total bits = 14 * binbits.  With binbits=3 (the default) -> 42-bit hash.

No spatial blocks are used: the hash describes the color DISTRIBUTION only,
which is what makes it robust to flips/rotations.
"""

import numpy as np


def rgb_to_hsv(rgb):
    """
    Convert an (H, W, 3) RGB array to HSV in Pillow's 0-255 convention.
    Accepts uint8 [0,255] or float [0,1]. Returns uint8 (H, W, 3).
    """
    is_uint8 = rgb.dtype == np.uint8
    rgb = rgb.astype(np.float32)
    if is_uint8:
        rgb = rgb / 255.0

    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    cmax = np.max(rgb, axis=-1)
    cmin = np.min(rgb, axis=-1)
    delta = cmax - cmin

    v = cmax
    s = np.zeros_like(cmax)
    nz = cmax > 0
    s[nz] = delta[nz] / cmax[nz]

    h = np.zeros_like(cmax)
    mask = delta > 0
    d_safe = np.where(delta == 0, 1.0, delta)
    r_max = (cmax == r) & mask
    g_max = (cmax == g) & mask
    b_max = (cmax == b) & mask
    h[r_max] = (((g - b) / d_safe) % 6)[r_max]
    h[g_max] = (((b - r) / d_safe) + 2)[g_max]
    h[b_max] = (((r - g) / d_safe) + 4)[b_max]
    h = h * 60.0
    h[h < 0] += 360.0

    # rescale to Pillow's 0-255 HSV convention
    h = h / 360.0 * 255.0
    s = s * 255.0
    v = v * 255.0
    return np.clip(np.round(np.stack([h, s, v], axis=-1)), 0, 255).astype(np.uint8)


def rgb_to_intensity(rgb):
    """Luminance (L) channel used for the black test: L = 0.299R + 0.587G + 0.114B."""
    is_float = rgb.dtype != np.uint8
    rgb = rgb.astype(np.float32)
    if is_float:
        rgb = rgb * 255.0
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    L = 0.299 * r + 0.587 * g + 0.114 * b
    return np.clip(np.round(L), 0, 255).astype(np.uint8)


def hsv_hash(rgb, binbits=3):
    """
    Compute the HSVHash of an (H, W, 3) RGB array.
    Returns a flat numpy bool array of length 14 * binbits (= 42 when binbits=3).
    """
    intensity = rgb_to_intensity(rgb).flatten()
    hsv = rgb_to_hsv(rgb)
    h = hsv[..., 0].flatten()
    s = hsv[..., 1].flatten()

    # black bin: dark pixels
    mask_black = intensity < 256 // 8
    frac_black = mask_black.mean()

    # gray bin: low saturation, not already black
    mask_gray = s < 256 // 3
    frac_gray = np.logical_and(~mask_black, mask_gray).mean()

    # colorful pixels: not black, not gray -> split into faint / bright saturation
    mask_colors = np.logical_and(~mask_black, ~mask_gray)
    mask_faint = np.logical_and(mask_colors, s < 256 * 2 // 3)
    mask_bright = np.logical_and(mask_colors, s >= 256 * 2 // 3)

    c = max(1, mask_colors.sum())
    hue_bins = np.linspace(0, 255, 6 + 1)
    h_faint = np.histogram(h[mask_faint], bins=hue_bins)[0] if mask_faint.any() else np.zeros(6)
    h_bright = np.histogram(h[mask_bright], bins=hue_bins)[0] if mask_bright.any() else np.zeros(6)

    # 14 fractions -> quantize each to binbits bits
    maxvalue = 2 ** binbits
    values = [min(maxvalue - 1, int(frac_black * maxvalue)),
              min(maxvalue - 1, int(frac_gray * maxvalue))]
    for counts in list(h_faint) + list(h_bright):
        values.append(min(maxvalue - 1, int(counts * maxvalue * 1.0 / c)))

    bitarray = []
    for val in values:
        bitarray += [(val >> (binbits - 1 - i)) & 1 for i in range(binbits)]
    return np.asarray(bitarray)


def hamming(hash1, hash2):
    """Hamming distance between two HSVHash bit arrays."""
    return int(np.count_nonzero(hash1 != hash2))


def hash_to_hex(bits, binbits=3):
    """Render the bit array as a hex string (same format as imagehash)."""
    flat = bits.reshape((-1, binbits))
    return "".join("%0{}x".format((binbits + 3) // 4) % int("".join(str(int(b)) for b in row), 2)
                   for row in flat)
