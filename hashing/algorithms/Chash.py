from __future__ import annotations
import numpy as np
from PIL import Image

from algorithms.base import ImageHasher

IMAGE_SIZE = (32, 32)
S_MIN = 25
NUM_BINS = 8
BIN_WIDTH = 256 // NUM_BINS

_EMPTY_ZONE = -1


class ColorHash(ImageHasher):
    """
    Spatial color hash.

    Encodes the *relative* dominant hue and mean saturation of each zone
    in a 4×4 grid → 64-bit hash invariant to global channel shifts.

    Falls back to a luminance-zone hash for grayscale / near-grayscale images.
    Returns a 65-character string: a leading mode marker ("C" = color, 
    "F" = grayscale fallback) followed by the 64-bit hash.
    """

    HASH_BITS = 64

    def compute(self, image_input: str | Image.Image) -> str:
        # Load and convert to HSV
        im = self._to_pil(image_input)
        im = im.convert("RGB").resize(IMAGE_SIZE, Image.LANCZOS)
        # PIL HSV: H 0-255 → 0-360°, S 0-255 → 0-100%, V 0-255 → 0-100%
        raw_data = np.array(im.convert("HSV"), dtype=np.uint8)

        h_chan = raw_data[..., 0]
        s_chan = raw_data[..., 1]
        v_chan = raw_data[..., 2]

        mask = s_chan >= S_MIN

        is_fallback = not bool(np.any(mask))
        if is_fallback:
            hash_int = self._compute_fallback_hash(v_chan)
            marker = "F"
        else:
            hash_int = self._compute_color_hash(h_chan, s_chan, mask)
            marker = "C"

        return marker + format(hash_int, "064b")

    def _get_dominant_bin(self, h_channel: np.ndarray, mask: np.ndarray) -> int:
        """Most frequent hue bin (0-7) among unmasked pixels."""
        valid_hues = h_channel[mask]
        if valid_hues.size == 0:
            return _EMPTY_ZONE
        counts = np.bincount(valid_hues // BIN_WIDTH, minlength=NUM_BINS)
        return int(np.argmax(counts))

    def _compute_fallback_hash(self, v_chan: np.ndarray) -> int:
        """Luminance-zone hash: 1 bit per zone, 16 bits total, zero-padded."""
        global_mean_v = v_chan.mean()
        bits = [
            "1" if v_chan[r*8:(r+1)*8, c*8:(c+1)*8].mean() >= global_mean_v else "0"
            for r in range(4)
            for c in range(4)
        ]
        return int("".join(bits).ljust(64, "0"), 2)

    def _compute_color_hash(self, h_chan: np.ndarray, s_chan: np.ndarray, mask: np.ndarray) -> int:
        h_global = self._get_dominant_bin(h_chan, mask)
        global_mean_sat = s_chan[mask].mean()

        bits = []

        for r in range(4):
            for c in range(4):
                sl = np.s_[r*8:(r+1)*8, c*8:(c+1)*8]
                z_h, z_s, z_mask = h_chan[sl], s_chan[sl], mask[sl]

                h_zone = self._get_dominant_bin(z_h, z_mask)

                if h_zone == _EMPTY_ZONE:
                    bits.append("0000")
                    continue

                offset = (h_zone - h_global) % NUM_BINS
                sat_bit = 1 if z_s[z_mask].mean() >= global_mean_sat else 0

                bits.append(format(offset, "03b"))
                bits.append(str(sat_bit))

        return int("".join(bits), 2)

    @staticmethod
    def hamming_distance(hash_a: str, hash_b: str) -> int:
        # First char is the mode marker; differing modes -> max distance.
        if hash_a[0] != hash_b[0]:
            return 64
        return sum(a != b for a, b in zip(hash_a[1:], hash_b[1:]))

    @classmethod
    def similarity(cls, hash_a: str, hash_b: str) -> float:
        return 1.0 - cls.hamming_distance(hash_a, hash_b) / cls.HASH_BITS