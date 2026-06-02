import numpy as np
from PIL import Image

HASH_SIZE = 8
HASH_BITS = HASH_SIZE * HASH_SIZE


def _load_and_preprocess(image_input):
    if isinstance(image_input, str):
        im = Image.open(image_input)
    elif isinstance(image_input, Image.Image):
        im = image_input
    else:
        raise TypeError("Expected a file path or PIL Image")

    im = im.convert("L")
    im = im.resize((HASH_SIZE, HASH_SIZE), Image.LANCZOS)
    return np.array(im, dtype=np.float64)


def _binarise(block):
    mean = block.mean()
    return (block > mean).astype(np.uint8)


def compute(image_input):
    block = _load_and_preprocess(image_input)
    block = _binarise(block)
    block = block.flatten()
    return "".join(str(b) for b in block)


def hamming_distance(hash_a, hash_b):
    if len(hash_a) != len(hash_b):
        raise ValueError
    return sum(a != b for a, b in zip(hash_a, hash_b))


def similarity(hash_a, hash_b):
    distance = hamming_distance(hash_a, hash_b)
    return 1 - (distance / len(hash_a))