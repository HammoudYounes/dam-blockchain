"""
Add a DINOv2 cosine-distance feature to the pairwise training set.

Reads:
  - hashing/benchmark_results/combined_training_data.csv
      image_a, image_b, transformation, label, + the 6 hash distances

Writes the same rows with one extra column appended:
  - dinov2_dist   cosine distance between the two DINOv2 CLS embeddings

WHY THIS FEATURE EXISTS
    The six perceptual hashes collapse on DISC21. Positive (duplicate) pairs there
    average ~0.45 normalised Hamming on ahash and ~0.51 on phash — barely different
    from a coin flip, because DISC21 edits are semantic (overlays, crops, re-renders)
    rather than the photometric transforms the hashes were tuned for. A learned
    embedding separates exactly those cases, so this column is the one most likely
    to lift the combiner on hard pairs. The summary printed at the end quantifies
    that per feature, so the claim is checkable rather than assumed.

WHAT THE NUMBER IS
    Embeddings are L2-normalised, so cosine similarity is a plain dot product and

        dinov2_dist = 1 - cos_sim        range [0, 2], 0 = identical

    Same orientation as the hash columns (0 = identical, larger = more different),
    which is what lets it drop into the existing feature vector unchanged.

    NOT the same scale as the `ann_distance` FAISS reports, or as
    `verification_candidates.ann_distance` in the backend — those are SQUARED L2
    over unit vectors, i.e. 2*(1 - cos_sim), range [0, 4]. Do not mix the two.

MODEL PARITY
    Loads the model through `retriever.embedder.ImageEmbedder`, the same class the
    live retriever uses, so the training feature matches the serving feature. The
    preprocessing here (open -> RGB -> resize 224 -> processor -> CLS -> normalise)
    mirrors `ImageEmbedder.embed_image` step for step; batching only changes how
    many images ride through the model at once, not the arithmetic per image.

RUN (from hashing/)
    python combine/add_dinov2_distance.py                      # -> *_with_dinov2.csv
    python combine/add_dinov2_distance.py --in-place           # overwrite the input
    python combine/add_dinov2_distance.py --limit 50           # smoke test
    python combine/add_dinov2_distance.py --disc21-root /path/to/filtered_images

REQUIRES
    torch + transformers. Both are listed in requirements-dev.txt but are NOT in
    the checked-in venvs; install before running.
"""

import argparse
import csv
import os
import sys
import time
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

# ── Paths ─────────────────────────────────────────────────────────────────────
HASHING_ROOT = SCRIPT_DIR.parent                    # hashing/
REPO_ROOT    = HASHING_ROOT.parent                  # dam-blockchain/
RESULTS_DIR  = HASHING_ROOT / "benchmark_results"

DEFAULT_INPUT = RESULTS_DIR / "combined_training_data.csv"

# The CSV mixes two datasets whose paths are relative to different roots — the
# own-dataset rows to hashing/data/own, the DISC21 rows to a dataset tree that
# lives OUTSIDE the repo (it is gitignored and multi-GB). Dispatch on the prefix.
DEFAULT_OWN_ROOT    = HASHING_ROOT / "data" / "own"
DEFAULT_DISC21_ROOT = REPO_ROOT.parent.parent / "Dataset" / "disc21" / "filtered_images"

OWN_PREFIXES    = ("images/", "images_variants/")
DISC21_PREFIXES = ("references/", "queries/")

FEATURE_COL = "dinov2_dist"
HASH_COLS = ["ahash_dist", "phash_dist", "dhash_dist",
             "hsvhash_dist", "rhash_dist", "chash_dist"]


# ── Path resolution ───────────────────────────────────────────────────────────
def resolve_path(rel: str, own_root: Path, disc21_root: Path) -> Path | None:
    """Map a CSV path onto disk. Returns None if the prefix is unrecognised."""
    rel = rel.strip().replace("\\", "/")
    if rel.startswith(OWN_PREFIXES):
        return own_root / rel
    if rel.startswith(DISC21_PREFIXES):
        return disc21_root / rel
    return None


# ── Embedding ─────────────────────────────────────────────────────────────────
def load_embedder(model_size: str):
    """Import torch lazily so --help works without the heavy deps installed."""
    try:
        import torch  # noqa: F401
        from retriever.embedder import ImageEmbedder
    except ImportError as e:
        sys.exit(
            f"ERROR: {e}\n\n"
            "torch/transformers are required but not installed in this environment.\n"
            "They are declared in requirements-dev.txt but absent from the venvs:\n\n"
            "    pip install -r requirements-dev.txt\n"
        )
    embedder = ImageEmbedder(model_size=model_size)
    embedder.initialize()
    return embedder


def embed_paths(embedder, paths: list[Path], batch_size: int) -> dict[Path, np.ndarray]:
    """
    Embed each unique image once. Returns {path: unit-norm CLS vector}.

    Caching by unique path is what makes this affordable: the own-dataset rows
    reuse ~57 images across ~165 pairs, so the pair count is a bad proxy for work.
    """
    import torch
    from PIL import Image

    out: dict[Path, np.ndarray] = {}
    failed: list[tuple[Path, str]] = []
    total = len(paths)
    started = time.time()

    for start in range(0, total, batch_size):
        chunk = paths[start:start + batch_size]

        images, kept = [], []
        for p in chunk:
            try:
                # Mirrors ImageEmbedder.get_embedding_from_path exactly.
                images.append(Image.open(p).convert("RGB").resize((224, 224)))
                kept.append(p)
            except Exception as e:                      # noqa: BLE001
                failed.append((p, str(e)))

        if images:
            inputs = embedder.image_processor(images=images, return_tensors="pt")
            inputs = {k: v.to(embedder.device) for k, v in inputs.items()}
            with torch.no_grad():
                hidden = embedder.model(**inputs).last_hidden_state[:, 0, :]
                hidden = hidden / hidden.norm(dim=-1, keepdim=True)
            for p, vec in zip(kept, hidden.cpu().numpy()):
                out[p] = vec

        done = min(start + batch_size, total)
        if done % (batch_size * 10) < batch_size or done == total:
            rate = done / max(time.time() - started, 1e-6)
            eta = (total - done) / max(rate, 1e-6)
            print(f"  {done}/{total} images embedded  ({rate:.1f}/s, ETA {eta:.0f}s)")

    if failed:
        print(f"\nWARNING: {len(failed)} image(s) could not be read:")
        for p, err in failed[:5]:
            print(f"  {p}: {err}")
        if len(failed) > 5:
            print(f"  ... and {len(failed) - 5} more")

    return out


# ── Reporting ─────────────────────────────────────────────────────────────────
def summarise(rows: list[dict]) -> None:
    """Per-class means for every feature, so the new column can be judged, not assumed."""
    def col(rs, name):
        vals = []
        for r in rs:
            v = r.get(name, "")
            if v != "":
                try:
                    vals.append(float(v))
                except ValueError:
                    pass
        return np.array(vals)

    pos = [r for r in rows if str(r.get("label", "")).strip() == "1"]
    neg = [r for r in rows if str(r.get("label", "")).strip() == "0"]

    print("\nMean distance by class — positive (duplicate) vs negative")
    print(f"{'Feature':<14} {'Positive':>10} {'Negative':>10} {'Gap':>10}")
    print("-" * 48)
    for name in HASH_COLS + [FEATURE_COL]:
        p, n = col(pos, name), col(neg, name)
        if p.size == 0 or n.size == 0:
            continue
        marker = "  <-- new" if name == FEATURE_COL else ""
        print(f"{name:<14} {p.mean():>10.4f} {n.mean():>10.4f} "
              f"{n.mean() - p.mean():>10.4f}{marker}")
    print("\nGap = negative mean - positive mean. Larger is better separation.")

    # DISC21 is where the hashes fail, so break it out — an aggregate gap can look
    # healthy while the hard subset is at chance.
    disc = [r for r in rows if str(r.get("transformation", "")).startswith("disc21")]
    if disc:
        dp = [r for r in disc if str(r.get("label", "")).strip() == "1"]
        dn = [r for r in disc if str(r.get("label", "")).strip() == "0"]
        if dp and dn:
            print(f"\nDISC21 subset only ({len(dp)} pos / {len(dn)} neg)")
            print(f"{'Feature':<14} {'Positive':>10} {'Negative':>10} {'Gap':>10}")
            print("-" * 48)
            for name in HASH_COLS + [FEATURE_COL]:
                p, n = col(dp, name), col(dn, name)
                if p.size == 0 or n.size == 0:
                    continue
                print(f"{name:<14} {p.mean():>10.4f} {n.mean():>10.4f} "
                      f"{n.mean() - p.mean():>10.4f}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--output", type=Path, default=None,
                    help="default: <input>_with_dinov2.csv")
    ap.add_argument("--in-place", action="store_true",
                    help="overwrite --input instead of writing a sibling file")
    ap.add_argument("--model-size", default=os.getenv("MODEL_SIZE", "small"),
                    choices=["small", "base", "large", "giant"],
                    help="facebook/dinov2-<size>; must match the retriever's MODEL_SIZE")
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--own-root", type=Path, default=DEFAULT_OWN_ROOT)
    ap.add_argument("--disc21-root", type=Path, default=DEFAULT_DISC21_ROOT)
    ap.add_argument("--limit", type=int, default=None,
                    help="only process the first N rows (smoke test)")
    ap.add_argument("--strict", action="store_true",
                    help="abort if any image is missing or unreadable")
    args = ap.parse_args()

    if args.output and args.in_place:
        sys.exit("ERROR: pass either --output or --in-place, not both")
    out_path = (args.input if args.in_place else
                args.output or args.input.with_name(f"{args.input.stem}_with_dinov2.csv"))

    print("=" * 70)
    print("DINOv2 cosine distance -> pairwise training data")
    print(f"Input       : {args.input}")
    print(f"Output      : {out_path}")
    print(f"Model       : facebook/dinov2-{args.model_size}")
    print(f"Own root    : {args.own_root}")
    print(f"DISC21 root : {args.disc21_root}")
    print("=" * 70)

    if not args.input.exists():
        sys.exit(f"ERROR: input CSV not found at {args.input}")

    with args.input.open(newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    if args.limit:
        rows = rows[:args.limit]
    print(f"\nRows: {len(rows)}")

    for required in ("image_a", "image_b"):
        if required not in fieldnames:
            sys.exit(f"ERROR: input CSV has no '{required}' column")

    # ── Resolve every referenced image up front ───────────────────────────────
    resolved: dict[str, Path] = {}
    unresolved: list[str] = []
    missing: list[Path] = []

    for row in rows:
        for key in ("image_a", "image_b"):
            rel = row[key]
            if rel in resolved or rel in unresolved:
                continue
            p = resolve_path(rel, args.own_root, args.disc21_root)
            if p is None:
                unresolved.append(rel)
            elif not p.exists():
                missing.append(p)
                unresolved.append(rel)
            else:
                resolved[rel] = p

    print(f"Unique images referenced : {len(resolved) + len(unresolved)}")
    print(f"  resolved on disk       : {len(resolved)}")
    if unresolved:
        print(f"  MISSING / unrecognised : {len(unresolved)}")
        for rel in unresolved[:5]:
            print(f"    {rel}")
        if len(unresolved) > 5:
            print(f"    ... and {len(unresolved) - 5} more")
        if missing:
            print(f"\n  Hint: {len(missing)} path(s) resolved but do not exist. If the "
                  f"DISC21\n  dataset lives elsewhere, pass --disc21-root.")
        if args.strict:
            sys.exit("\nERROR: --strict set and some images are unavailable")
    if not resolved:
        sys.exit("\nERROR: no images could be resolved — check --own-root/--disc21-root")

    # ── Embed ─────────────────────────────────────────────────────────────────
    embedder = load_embedder(args.model_size)
    unique_paths = sorted(set(resolved.values()))
    print(f"\nEmbedding {len(unique_paths)} unique images "
          f"(batch size {args.batch_size})...")
    vectors = embed_paths(embedder, unique_paths, args.batch_size)

    # ── Cosine distance per pair ──────────────────────────────────────────────
    print("\nComputing pairwise cosine distances...")
    skipped = 0
    for row in rows:
        pa, pb = resolved.get(row["image_a"]), resolved.get(row["image_b"])
        va = vectors.get(pa) if pa else None
        vb = vectors.get(pb) if pb else None
        if va is None or vb is None:
            row[FEATURE_COL] = ""          # left blank, never silently zero
            skipped += 1
            continue
        # Vectors are unit-norm, so the dot product IS the cosine similarity.
        # Clip absorbs float drift that would otherwise push |cos| just past 1.
        cos_sim = float(np.clip(np.dot(va, vb), -1.0, 1.0))
        row[FEATURE_COL] = f"{1.0 - cos_sim:.6f}"

    filled = len(rows) - skipped
    print(f"  {filled}/{len(rows)} rows filled")
    if skipped:
        print(f"  {skipped} row(s) left BLANK — drop or impute these before training")

    # ── Write ─────────────────────────────────────────────────────────────────
    if FEATURE_COL not in fieldnames:
        fieldnames.append(FEATURE_COL)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nSaved {len(rows)} rows to: {out_path}")

    summarise(rows)

    if skipped == 0 and not args.limit:
        print(f"\nNext: add '{FEATURE_COL}' to FEATURES_ORDER in api/similarity.py and "
              f"retrain.\nThe deployed logreg takes 6 features — it will not use this "
              f"column until it is\nretrained on 7, and feeding it 7 will raise.")


if __name__ == "__main__":
    main()
