"""
benchmark_own_summary.py
------------------------
Reads the per-algorithm benchmark CSVs produced by the hashing benchmarking
pipeline and writes a structured summary CSV suitable for inclusion in the
rapport de stage and as a baseline reference before large-dataset testing.

Expected input file layout (relative to RESULTS_DIR):
    {algo}_pair_distances.csv    — one row per image pair
    {algo}_per_transform.csv     — per-transformation accuracy aggregates
    {algo}_threshold_sweep.csv   — metrics at every integer threshold

Output files (written to OUTPUT_DIR):
    benchmark_own_summary.csv        — one row per algorithm, key metrics at best threshold
    own_per_transform_summary.csv    — all algorithms × all transformations, side-by-side
    own_distance_stats_summary.csv   — SIMILAR vs DIFFERENT distance distribution stats
    own_false_cases_summary.csv      — false negatives and false positives at best threshold

Usage:
    python benchmark_own_summary.py
    python benchmark__own_summary.py --results-dir path/to/csvs --output-dir path/to/output
"""

import argparse
import os
import sys
import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ALGORITHMS = ["ahash", "dhash", "hsv", "phash","rhash", "chash"]  

ALGORITHM_LABELS = {
    "ahash": "aHash (Average Hash)",
    "dhash": "dHash (Difference Hash)",
    "hsv":   "HSV Hash",
    "phash": "pHash (Perceptual Hash)",
    "rhash": "rHash (Radial Hash)",
    "chash": "CHash (Spatial Color Hash)",
}

# Transformations that operate in the spatial domain — useful for the paper
SPATIAL_TRANSFORMS = {"cropped_10%", "cropped_20%", "cropped_30%", "covered_30%", "grid_dropout_20%"}
PHOTOMETRIC_TRANSFORMS = {
    "grayscale", "blur_radius_2", "brightened_1.5x", "darkened_0.5x",
    "contrast_1.5x", "channel_shift_1",
}
COMPRESSION_TRANSFORMS = {"quality_20%", "quality_50%", "quality_80%"}
RESIZE_TRANSFORMS = {"resized_50%", "resized_up_200%"}
OTHER_TRANSFORMS = {"altered_20%", "edge_filter"}


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_algorithm_data(results_dir: str, algo: str) -> dict:
    """Load all three CSV files for one algorithm and return them as a dict."""
    paths = {
        "pairs":     os.path.join(results_dir, f"{algo}_pair_distances.csv"),
        "transform": os.path.join(results_dir, f"{algo}_per_transform.csv"),
        "sweep":     os.path.join(results_dir, f"{algo}_threshold_sweep.csv"),
    }
    for key, path in paths.items():
        if not os.path.exists(path):
            print(f"[ERROR] Missing file: {path}", file=sys.stderr)
            sys.exit(1)

    return {
        "pairs":     pd.read_csv(paths["pairs"]),
        "transform": pd.read_csv(paths["transform"]),
        "sweep":     pd.read_csv(paths["sweep"]),
    }


# ---------------------------------------------------------------------------
# Summary 1: best-threshold metrics, one row per algorithm
# ---------------------------------------------------------------------------

def compute_benchmark_summary(data_by_algo: dict) -> pd.DataFrame:
    """
    Build the primary benchmark summary table.
    One row per algorithm, metrics at its best threshold (highest F1).
    Includes distance separability margin and per-category aggregate accuracy.
    """
    rows = []

    for algo, data in data_by_algo.items():
        sweep = data["sweep"]
        pairs = data["pairs"]
        per_tf = data["transform"]

        # --- Best threshold row (highest F1; tie-break by highest accuracy) ---
        best_rows = sweep[sweep["best_f1"] == True]
        if best_rows.empty:
            # Fallback: pick the row with the max F1 manually
            best_rows = sweep[sweep["f1"] == sweep["f1"].max()]
        best = best_rows.sort_values("accuracy", ascending=False).iloc[0]

        threshold    = int(best["threshold"])
        accuracy     = float(best["accuracy"])
        precision    = float(best["precision"])
        recall       = float(best["recall"])
        f1           = float(best["f1"])
        tp           = int(best["tp"])
        tn           = int(best["tn"])
        fp           = int(best["fp"])
        fn           = int(best["fn"])

        total_similar    = tp + fn
        total_different  = tn + fp
        total_pairs      = total_similar + total_different

        # --- Distance distribution stats ---
        sim_dist = pairs[pairs["label"] == 1]["hamming_distance"]
        dif_dist = pairs[pairs["label"] == 0]["hamming_distance"]

        sim_mean   = float(sim_dist.mean())
        sim_median = float(sim_dist.median())
        sim_std    = float(sim_dist.std())
        sim_max    = int(sim_dist.max())

        dif_mean   = float(dif_dist.mean())
        dif_median = float(dif_dist.median())
        dif_std    = float(dif_dist.std())
        dif_min    = int(dif_dist.min())

        # Separability margin at the best threshold:
        # gap between the highest correctly-classified SIMILAR and
        # the lowest correctly-classified DIFFERENT distance.
        sim_below = sim_dist[sim_dist <= threshold]
        dif_above = dif_dist[dif_dist > threshold]
        sep_margin = (
            int(dif_above.min()) - int(sim_below.max())
            if len(sim_below) > 0 and len(dif_above) > 0
            else None
        )

        # --- Per-category aggregate accuracy ---
        def cat_accuracy(category_set):
            subset = per_tf[per_tf["transformation"].isin(category_set)]
            if subset.empty:
                return None
            return round(subset["accuracy_pct"].mean(), 2)

        spatial_acc      = cat_accuracy(SPATIAL_TRANSFORMS)
        photometric_acc  = cat_accuracy(PHOTOMETRIC_TRANSFORMS)
        compression_acc  = cat_accuracy(COMPRESSION_TRANSFORMS)
        resize_acc       = cat_accuracy(RESIZE_TRANSFORMS)

        # Number of transformations with perfect accuracy (100%)
        perfect_transforms = int((per_tf["accuracy_pct"] == 100.0).sum())
        total_transforms   = len(per_tf)

        rows.append({
            "algorithm":               ALGORITHM_LABELS[algo],
            "algo_key":                algo,
            "total_pairs":             total_pairs,
            "total_similar":           total_similar,
            "total_different":         total_different,
            "best_threshold":          threshold,
            "accuracy":                round(accuracy, 6),
            "accuracy_pct":            round(accuracy * 100, 4),
            "precision":               round(precision, 6),
            "recall":                  round(recall, 6),
            "f1_score":                round(f1, 6),
            "true_positives":          tp,
            "true_negatives":          tn,
            "false_positives":         fp,
            "false_negatives":         fn,
            "false_positive_rate":     round(fp / total_different, 6) if total_different > 0 else 0.0,
            "false_negative_rate":     round(fn / total_similar, 6)   if total_similar   > 0 else 0.0,
            "similar_dist_mean":       round(sim_mean, 4),
            "similar_dist_median":     round(sim_median, 4),
            "similar_dist_std":        round(sim_std, 4),
            "similar_dist_max":        sim_max,
            "different_dist_mean":     round(dif_mean, 4),
            "different_dist_median":   round(dif_median, 4),
            "different_dist_std":      round(dif_std, 4),
            "different_dist_min":      dif_min,
            "separability_margin":     sep_margin,
            "spatial_transforms_acc":      spatial_acc,
            "photometric_transforms_acc":  photometric_acc,
            "compression_transforms_acc":  compression_acc,
            "resize_transforms_acc":       resize_acc,
            "perfect_transform_count":     perfect_transforms,
            "total_transform_count":       total_transforms,
            "perfect_transform_pct":   round(perfect_transforms / total_transforms * 100, 2),
        })

    df = pd.DataFrame(rows)
    # Sort by F1 descending so the best algorithm appears first
    df = df.sort_values("f1_score", ascending=False).reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Summary 2: per-transform accuracy, all algorithms side by side
# ---------------------------------------------------------------------------

def compute_per_transform_summary(data_by_algo: dict) -> pd.DataFrame:
    """
    Build a cross-algorithm per-transformation table.
    Rows = transformations. Columns = one accuracy column per algorithm,
    plus the winning algorithm and the spread (max - min).
    """
    frames = []
    for algo, data in data_by_algo.items():
        tf = data["transform"][["transformation", "accuracy_pct", "mean_dist", "max_dist"]].copy()
        tf = tf.rename(columns={
            "accuracy_pct": f"{algo}_accuracy_pct",
            "mean_dist":    f"{algo}_mean_dist",
            "max_dist":     f"{algo}_max_dist",
        })
        frames.append(tf.set_index("transformation"))

    combined = pd.concat(frames, axis=1).reset_index()
    combined = combined.rename(columns={"transformation": "transformation"})

    # Accuracy columns only, for derived stats
    acc_cols = [f"{algo}_accuracy_pct" for algo in ALGORITHMS]

    # Best algorithm per transformation (highest accuracy)
    def best_algo(row):
        vals = {algo: row[f"{algo}_accuracy_pct"] for algo in ALGORITHMS}
        max_acc = max(vals.values())
        winners = [algo for algo, v in vals.items() if v == max_acc]
        return " / ".join(winners)

    combined["best_algorithm"]  = combined.apply(best_algo, axis=1)
    combined["accuracy_spread"] = combined[acc_cols].max(axis=1) - combined[acc_cols].min(axis=1)

    # Assign transformation category
    def categorize(t):
        if t in SPATIAL_TRANSFORMS:      return "spatial"
        if t in PHOTOMETRIC_TRANSFORMS:  return "photometric"
        if t in COMPRESSION_TRANSFORMS:  return "compression"
        if t in RESIZE_TRANSFORMS:       return "resize"
        if t in OTHER_TRANSFORMS:        return "other"
        return "cross_image"

    combined.insert(1, "category", combined["transformation"].apply(categorize))
    combined = combined.sort_values(["category", "transformation"]).reset_index(drop=True)
    return combined


# ---------------------------------------------------------------------------
# Summary 3: distance distribution statistics per algorithm
# ---------------------------------------------------------------------------

def compute_distance_stats(data_by_algo: dict) -> pd.DataFrame:
    """
    Detailed distribution statistics for SIMILAR and DIFFERENT Hamming
    distances, per algorithm. Useful for the rapport de stage analysis section.
    """
    rows = []
    for algo, data in data_by_algo.items():
        pairs = data["pairs"]

        for label_val, label_name in [(1, "similar"), (0, "different")]:
            dist = pairs[pairs["label"] == label_val]["hamming_distance"]
            rows.append({
                "algorithm":  ALGORITHM_LABELS[algo],
                "algo_key":   algo,
                "class":      label_name,
                "n_pairs":    len(dist),
                "mean":       round(float(dist.mean()),   4),
                "median":     round(float(dist.median()), 4),
                "std":        round(float(dist.std()),    4),
                "min":        int(dist.min()),
                "max":        int(dist.max()),
                "p25":        round(float(dist.quantile(0.25)), 4),
                "p75":        round(float(dist.quantile(0.75)), 4),
                "p95":        round(float(dist.quantile(0.95)), 4),
            })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Summary 4: false cases at best threshold
# ---------------------------------------------------------------------------

def compute_false_cases(data_by_algo: dict) -> pd.DataFrame:
    """
    List every false negative and false positive at each algorithm's best
    threshold. Useful for identifying which specific transformations or image
    pairs are responsible for misclassifications.
    """
    rows = []

    for algo, data in data_by_algo.items():
        sweep = data["sweep"]
        pairs = data["pairs"]

        best_rows = sweep[sweep["best_f1"] == True]
        if best_rows.empty:
            best_rows = sweep[sweep["f1"] == sweep["f1"].max()]
        threshold = int(best_rows.sort_values("accuracy", ascending=False).iloc[0]["threshold"])

        sim = pairs[pairs["label"] == 1]
        dif = pairs[pairs["label"] == 0]

        # False negatives: SIMILAR pairs classified as DIFFERENT
        fn_pairs = sim[sim["hamming_distance"] > threshold].copy()
        fn_pairs["case_type"] = "false_negative"

        # False positives: DIFFERENT pairs classified as SIMILAR
        fp_pairs = dif[dif["hamming_distance"] <= threshold].copy()
        fp_pairs["case_type"] = "false_positive"

        for _, row in pd.concat([fn_pairs, fp_pairs]).iterrows():
            rows.append({
                "algorithm":       ALGORITHM_LABELS[algo],
                "algo_key":        algo,
                "best_threshold":  threshold,
                "case_type":       row["case_type"],
                "image_a":         row["image_a"],
                "image_b":         row["image_b"],
                "transformation":  row["transformation"],
                "hamming_distance": int(row["hamming_distance"]),
                "label":           int(row["label"]),
            })

    return pd.DataFrame(rows).sort_values(
        ["algo_key", "case_type", "transformation"]
    ).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------

def write_csv(df: pd.DataFrame, path: str, description: str) -> None:
    df.to_csv(path, index=False)
    print(f"  [OK] {description}")
    print(f"       -> {path}  ({len(df)} rows x {len(df.columns)} columns)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-dir",
        default="hashing/benchmark_results",
        help="Directory containing the {algo}_*.csv benchmark files (default: current dir)"
    )
    parser.add_argument(
        "--output-dir",
        default="hashing/benchmark_results/summary",
        help="Directory where summary CSVs will be written (default: current dir)"
    )
    args = parser.parse_args()

    results_dir = os.path.abspath(args.results_dir)
    output_dir  = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    print(f"\nBenchmark Summary Generator")
    print(f"  Results dir : {results_dir}")
    print(f"  Output dir  : {output_dir}")
    print(f"  Algorithms  : {', '.join(ALGORITHMS)}\n")

    # Load all data
    print("Loading benchmark CSVs...")
    data_by_algo = {algo: load_algorithm_data(results_dir, algo) for algo in ALGORITHMS}
    total_pairs = len(next(iter(data_by_algo.values()))["pairs"])
    print(f"  Loaded {len(ALGORITHMS)} algorithms, {total_pairs} pairs each.\n")

    # Compute and write all summaries
    print("Writing summary files...")

    benchmark_df = compute_benchmark_summary(data_by_algo)
    write_csv(
        benchmark_df,
        os.path.join(output_dir, "benchmark_summary.csv"),
        "Primary benchmark summary (one row per algorithm, best-threshold metrics)"
    )

    per_transform_df = compute_per_transform_summary(data_by_algo)
    write_csv(
        per_transform_df,
        os.path.join(output_dir, "per_transform_summary.csv"),
        "Per-transformation accuracy, all algorithms side by side"
    )

    distance_df = compute_distance_stats(data_by_algo)
    write_csv(
        distance_df,
        os.path.join(output_dir, "distance_stats_summary.csv"),
        "Hamming distance distribution stats (SIMILAR vs DIFFERENT per algorithm)"
    )

    false_cases_df = compute_false_cases(data_by_algo)
    write_csv(
        false_cases_df,
        os.path.join(output_dir, "false_cases_summary.csv"),
        "False negatives and false positives at each algorithm's best threshold"
    )

    # Print a quick console digest
    print("\n--- Quick digest ---")
    digest_cols = ["algorithm", "best_threshold", "accuracy_pct", "precision", "recall", "f1_score",
                   "false_positives", "false_negatives", "separability_margin"]
    print(benchmark_df[digest_cols].to_string(index=False))
    print()


if __name__ == "__main__":
    main()