"""
Average hash (aHash): resize to 8x8 grayscale and threshold each pixel at the
block mean.
"""

from algorithms.base import ImageHasher


class AverageHash(ImageHasher):
    HASH_SIZE = 8
    HASH_BITS = HASH_SIZE * HASH_SIZE  # 64

    def compute(self, image_input):
        block = self._load_grayscale(image_input, (self.HASH_SIZE, self.HASH_SIZE))
        return self._to_bitstring(self._binarise(block))
