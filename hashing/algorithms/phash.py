"""
Perceptual hash (pHash): resize to 32x32 grayscale, take the 2-D DCT, keep the
top-left 8x8 low-frequency block (minus the DC term) and threshold at its mean.
"""

import numpy as np
from scipy.fft import dct

from algorithms.base import ImageHasher


class PerceptualHash(ImageHasher):
    RESIZE_DIM = 32
    HASH_SIZE = 8
    HASH_BITS = HASH_SIZE * HASH_SIZE - 1  # 63 (8x8 block minus the DC term)

    def compute(self, image_input):
        # resample=None keeps Pillow's default filter, matching the original
        # behaviour (resize was called without an explicit resample filter).
        block = self._load_grayscale(
            image_input, (self.RESIZE_DIM, self.RESIZE_DIM), resample=None
        )
        block = self._dct2d(block)
        block = self._extract_low_freq(block)
        return self._to_bitstring(self._binarise(block))

    @staticmethod
    def _dct2d(block):
        result = dct(block, axis=0, norm="ortho")
        result = dct(result, axis=1, norm="ortho")
        return result

    def _extract_low_freq(self, block):
        block = block[: self.HASH_SIZE, : self.HASH_SIZE]
        block = block.flatten()
        return block[1:]  # drop the DC coefficient
