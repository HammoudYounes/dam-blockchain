from algorithms.ahash import AverageHash
from algorithms.phash import PerceptualHash
from algorithms.dhash import DifferenceHash
from algorithms.HSVHash import HSVColorHash
from algorithms.rhash import RadialHash
from algorithms.Chash import ColorHash

# One hasher per algorithm. The dict key is the CSV column prefix; each hasher
# carries its own HASH_BITS used to normalise the Hamming distance.
HASHERS = {
    "ahash":   AverageHash(),
    "phash":   PerceptualHash(),
    "dhash":   DifferenceHash(),
    "hsvhash": HSVColorHash(),
    "rhash":   RadialHash(),
    "chash":   ColorHash(),
}

def get_hash(algo: str, image_input: str | bytes) -> str:
    return HASHERS[algo].compute(image_input)

def compute_features(image_a: str | bytes, image_b: str | bytes) -> dict:
    feats = {}
    for algo, hasher in HASHERS.items():
        dist = hasher.hamming_distance(get_hash(algo, image_a), get_hash(algo, image_b))
        feats[f"{algo}_dist"] = dist / hasher.HASH_BITS
    return feats

def compute_similarities(image_a: str | bytes, image_b: str | bytes) -> dict:
    sims = {}
    for algo, hasher in HASHERS.items():
        sim = hasher.similarity(get_hash(algo, image_a), get_hash(algo, image_b))
        sims[f"{algo}_sim"] = sim
    return sims
