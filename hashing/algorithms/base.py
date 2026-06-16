from abc import ABC, abstractmethod
import numpy as np
from PIL import Image

class ImageHasher(ABC):
    HASH_BITS = 64  # subclass override

    @staticmethod
    def _to_pil(image_input):
        """Accept a file path or a PIL image and return a PIL image."""
        if isinstance(image_input, str):
            return Image.open(image_input)
        if isinstance(image_input, Image.Image):
            return image_input
        raise TypeError("Expected a file path or PIL Image")

    def _load_grayscale(self, image_input, size, resample=Image.LANCZOS):
        """Load, grayscale and resize to ``size`` (width, height).

        Pass ``resample=None`` to use Pillow's default resampling filter.
        """
        im = self._to_pil(image_input).convert("L").resize(size, resample)
        return np.array(im, dtype=np.float64)

    @staticmethod
    def _binarise(block):
        return (block > block.mean()).astype(np.uint8)

    @staticmethod
    def _to_bitstring(bits):
        # int(b) handles both uint8 (0/1) and bool (True/False) arrays.
        return "".join(str(int(b)) for b in np.asarray(bits).flatten())

    @abstractmethod
    def compute(self, image_input) -> str: ...

    @staticmethod
    def hamming_distance(hash_a, hash_b):
        if len(hash_a) != len(hash_b):
            raise ValueError("Hashes must be of equal length")
        return sum(a != b for a, b in zip(hash_a, hash_b))

    @classmethod
    def similarity(cls, hash_a, hash_b):
        return 1 - cls.hamming_distance(hash_a, hash_b) / len(hash_a)