"""
Backfill the rhash_dist / chash_dist columns in combined_training_data.csv.

Why this is needed: the own-dataset rows in combined_training_data.csv were
inherited from training_data.csv, which was generated before rHash/cHash were
implemented. The merge step (collect_disc21_training_data.py) writes blanks for
columns it can't find, so those rows show up as NaN for rhash_dist/chash_dist.
The DISC21 rows already have values.

This script recomputes ONLY rhash_dist and chash_dist for rows where they are
missing, using the own-dataset images under hashing/data/own. Every other value
in the CSV is left exactly as-is.

Run from anywhere:
    python hashing/combine/fill_missing_rhash_chash.py
"""

import csv
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
HASHING_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(HASHING_DIR))

from algorithms.rhash import RadialHash
from algorithms.Chash import ColorHash

DATA_DIR = HASHING_DIR / "data" / "own"
CSV_PATH = HASHING_DIR / "benchmark_results" / "combined_training_data.csv"

# Column prefix -> hasher. Both normalise by HASH_BITS, matching the collectors.
HASHERS = {
    "rhash": RadialHash(),
    "chash": ColorHash(),
}

_caches: dict[str, dict[str, str]] = {name: {} for name in HASHERS}


def get_hash(algo: str, rel_path: str) -> str:
    cache = _caches[algo]
    if rel_path not in cache:
        cache[rel_path] = HASHERS[algo].compute(str(DATA_DIR / rel_path))
    return cache[rel_path]


def is_missing(value: str) -> bool:
    return value is None or value.strip() == "" or value.strip().lower() == "nan"


def main():
    with CSV_PATH.open(newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    for col in ("rhash_dist", "chash_dist"):
        if col not in fieldnames:
            sys.exit(f"ERROR: column {col!r} not in {CSV_PATH}")

    filled = 0
    for row in rows:
        needs = [algo for algo in HASHERS if is_missing(row[f"{algo}_dist"])]
        if not needs:
            continue

        a, b = row["image_a"], row["image_b"]
        for algo in needs:
            hasher = HASHERS[algo]
            dist = hasher.hamming_distance(get_hash(algo, a), get_hash(algo, b))
            row[f"{algo}_dist"] = dist / hasher.HASH_BITS
        filled += 1

    with CSV_PATH.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Backfilled rhash_dist/chash_dist for {filled} rows.")
    print(f"Saved -> {CSV_PATH}")


if __name__ == "__main__":
    main()
