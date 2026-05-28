"""
Implementation of the similarity hash (sHash) algorithm for image hashing.


- Average Hamming distance of non-duplicate images ~ 27.24
- Very good at capturing text, logos, emoji additions (avg Hamming ~ 0.97)
- Relatively bad at colour-swapped, flipped, rotated, or mirrored
  duplicates (avg Hamming distance > 16)

sHash captures the LOCAL GRADIENT STRUCTURE of an image: it compares each
pixel to its right-hand neighbour. Because it encodes edge/gradient direction
rather than absolute brightness, it is highly stable for sharp-edged content
(text, logos, emoji) and for brightness/compression changes, but it is NOT
invariant to spatial transforms (flip/rotate/mirror) or to colour reordering.
"""
import numpy as np
from PIL import Image

#--Constants----------------------------------------------

HASH_SIZE = 8
RESIZE_W = HASH_SIZE + 1          # need one extra column for horizontal diffs
RESIZE_H = HASH_SIZE
HASH_BITS = HASH_SIZE * HASH_SIZE

#--Functions----------------------------------------------

def _load_and_preprocess(image_input):

    if isinstance(image_input, str):
        im = Image.open(image_input)

    elif isinstance(image_input, Image.Image):
        im = image_input

    else:
        raise TypeError("Expected a file path or PIL Image")

    im = im.convert("L")
    im = im.resize((RESIZE_W, RESIZE_H), Image.LANCZOS)

    return np.array(im, dtype=np.int16)


def _horizontal_gradient(block):
    # compare each pixel to its right-hand neighbour
    left = block[:, :-1]
    right = block[:, 1:]
    return left, right


def _binarise(left, right):
    result = (left > right).astype(np.uint8)
    result = result.flatten()
    return result

#--Main Function----------------------------------------

def compute(image_input):
    block = _load_and_preprocess(image_input)
    left, right = _horizontal_gradient(block)
    block = _binarise(left, right)
    block = "".join(str(b) for b in block)
    return block

#--Metrics----------------------------------------------

def hamming_distance(hash_a, hash_b):
    if (len(hash_a) != len(hash_b)):
        raise ValueError
    else:
        distance = sum(a != b for a, b in zip(hash_a, hash_b))
        return distance


def similarity(hash_a, hash_b):
    distance = hamming_distance(hash_a, hash_b)
    score = 1 - (distance / len(hash_a))
    return score