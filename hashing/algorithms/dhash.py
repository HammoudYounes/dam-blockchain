"""
Implementation of the difference hash (dHash) algorithm for image hashing.

"""


import numpy as np
from PIL import Image

#--Constraints---------------------------------

HASH_WIDTH = 9
HASH_HEIGHT = 8
HASH_BITS = HASH_WIDTH * HASH_HEIGHT

#--Functions-----------------------------------

def _load_and_preprocess(image_input):

    if isinstance(image_input,str):
        im = Image.open(image_input)
    elif isinstance(image_input,Image.Image):
        im = image_input
        
    else:
        raise TypeError("Expected a file path or PIL Image")

    im = im.convert("L")
    im = im.resize((HASH_WIDTH, HASH_HEIGHT), Image.LANCZOS)
    return np.array(im, dtype=np.float64)

def _compute_gradients(block):
    im = block[:, :-1] > block[:, 1:]
    im = im.astype(np.uint8)
    return im


#--Main Function----------------------------------------


def compute(image_input):
    block = _load_and_preprocess(image_input)
    block = _compute_gradients(block)
    block = block.flatten()
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
    score = 1 - (distance/len(hash_a)) 
    return score