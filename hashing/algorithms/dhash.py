"""
Difference hash (dHash): resize to 9x8 grayscale and encode the sign of the
horizontal gradient between adjacent pixels.
"""

import numpy as np

from algorithms.base import ImageHasher


class DifferenceHash(ImageHasher):
    HASH_WIDTH = 9
    HASH_HEIGHT = 8
    # Kept at 9*8=72 to preserve the existing distance normalisation used by
    # the training-data collectors. The hash itself is (9-1)*8 = 64 bits.
    HASH_BITS = HASH_WIDTH * HASH_HEIGHT  # 72

    def compute(self, image_input):
        block = self._load_grayscale(image_input, (self.HASH_WIDTH, self.HASH_HEIGHT))
        return self._to_bitstring(self._compute_gradients(block))

    @staticmethod
    def _compute_gradients(block):
        return (block[:, :-1] > block[:, 1:]).astype(np.uint8)
