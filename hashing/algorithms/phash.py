"""
Implementation of the perceptual hash (pHash) algorithm for image hashing.

"""
import numpy as np
from scipy.fft import dct
from PIL import Image

#--Constants----------------------------------------------

RESIZE_DIM = 32
HASH_SIZE = 8
HASH_BITS = HASH_SIZE * HASH_SIZE

#--Functions----------------------------------------------

def _load_and_preprocess(image_input):

    if isinstance(image_input, str):
        im= Image.open(image_input)
    
    elif isinstance(image_input, Image.Image):
        im = image_input
        
    else:
        raise TypeError("Expected a file path or PIL Image")
    
    im = im.convert("L")
    im = im.resize((RESIZE_DIM,RESIZE_DIM))

    return np.array(im)


def _dct2d(block):
    result = dct(block,axis=0,norm="ortho")
    result = dct(result,axis=1,norm="ortho")
    return result

def _extract_low_freq(block):
    block = block[:HASH_SIZE, :HASH_SIZE]
    block = block.flatten()
    block = block[1:]
    return block

def _binarise(block):
    mean = block.mean()
    result = (block > mean).astype(np.uint8)
    return result

#--Main Function----------------------------------------

def compute(image_input):
    block = _load_and_preprocess(image_input)
    block = _dct2d(block)
    block = _extract_low_freq(block)
    block = _binarise(block)
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