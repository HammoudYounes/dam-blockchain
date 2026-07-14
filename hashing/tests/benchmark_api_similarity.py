"""
Benchmark script for the /similarity retrieval + duplicate-detection API.

Features:
  - Concurrent requests (ThreadPoolExecutor) with a pooled/retrying session
  - Correct content-type per file instead of hardcoded image/jpeg
  - Tracks the *rank* of the correct match -> Recall@k, Top-1 accuracy, MRR
  - Uses `duplicateProbability` (the fusion model output) in addition to
    raw FAISS distance, for both matches and misses
  - Per-source accuracy breakdown
  - Per-request latency tracking
  - Threshold sweep (--sweep) over `duplicateProbability` at the
    CANDIDATE level (every returned candidate, not just top-1), to find
    the cutoff that maximizes classification accuracy / F1
    
Usage:
    python benchmark_api_similarity.py <DATASET_FOLDER> \
        [--url http://localhost:8001/similarity] \
        [--k 5] [--workers 8] [--timeout 30] [--prob-threshold 0.5] \
        [--sweep] [--sweep-step 0.01]
"""

import argparse
import csv
import mimetypes
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict, field
from statistics import mean

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm


@dataclass
class QueryResult:
    reference: str
    query_path: str
    source: str
    status: str = "error"          # "match" | "miss" | "error"
    rank: int = -1                 # 1-indexed rank of correct match in top-k, -1 if not found
    match_distance: float = None
    match_probability: float = None
    top1_image: str = None
    top1_distance: float = None
    top1_probability: float = None
    latency_ms: float = None
    error: str = None
    candidates: list = field(default_factory=list, repr=False)  # raw per-candidate data, not written to summary CSV


def build_session(retries: int = 3, backoff: float = 0.5) -> requests.Session:
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["POST"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=32, pool_maxsize=32)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def guess_content_type(path: str) -> str:
    ctype, _ = mimetypes.guess_type(path)
    return ctype or "application/octet-stream"


def query_one(session, request_url, input_folder, row, k, timeout) -> QueryResult:
    reference, query_path, source = row
    full_query_path = os.path.join(input_folder, "queries", query_path)
    ref_filename = os.path.basename(reference)

    result = QueryResult(reference=reference, query_path=query_path, source=source)

    if not os.path.isfile(full_query_path):
        result.error = "file not found"
        return result

    try:
        content_type = guess_content_type(full_query_path)
        t0 = time.perf_counter()
        with open(full_query_path, "rb") as fh:
            files = {"newFile": (os.path.basename(query_path), fh, content_type)}
            response = session.post(request_url, files=files, params={"k": k}, timeout=timeout)
        result.latency_ms = (time.perf_counter() - t0) * 1000

        if response.status_code != 200:
            result.error = f"HTTP {response.status_code}: {response.text[:200]}"
            return result

        data = response.json()
        similar_images = data["data"]["similar_images"]

        if similar_images:
            top1 = similar_images[0]
            result.top1_image = top1["image_name"]
            result.top1_distance = top1["distance"]
            result.top1_probability = top1.get("duplicateProbability")

        matched_rank = None
        for rank, img in enumerate(similar_images, start=1):
            is_match = os.path.basename(img["image_name"]) == ref_filename
            result.candidates.append({
                "rank": rank,
                "image_name": img["image_name"],
                "distance": img["distance"],
                "probability": img.get("duplicateProbability"),
                "is_match": is_match,
            })
            if is_match and matched_rank is None:
                matched_rank = rank
                result.status = "match"
                result.rank = rank
                result.match_distance = img["distance"]
                result.match_probability = img.get("duplicateProbability")

        if matched_rank is None:
            result.status = "miss"

        return result
    except Exception as e:
        result.error = str(e)
        return result


def sweep_thresholds(candidate_records, step=0.01):
    """Sweep duplicateProbability thresholds and score candidate-level classification.

    Each candidate returned by the API (across all queries) is treated as a
    binary classification instance: is_match (ground truth) vs. predicted
    duplicate (probability >= threshold).
    """
    thresholds = [round(i * step, 4) for i in range(int(1 / step) + 1)]
    rows = []
    for th in thresholds:
        tp = fp = tn = fn = 0
        for rec in candidate_records:
            prob = rec["probability"]
            if prob is None:
                continue
            pred = prob >= th
            actual = rec["is_match"]
            if pred and actual:
                tp += 1
            elif pred and not actual:
                fp += 1
            elif not pred and actual:
                fn += 1
            else:
                tn += 1
        total = tp + fp + tn + fn
        if total == 0:
            continue
        accuracy = (tp + tn) / total
        precision = tp / (tp + fp) if (tp + fp) else 0
        recall = tp / (tp + fn) if (tp + fn) else 0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0
        rows.append({
            "threshold": th, "accuracy": accuracy, "precision": precision,
            "recall": recall, "f1": f1, "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        })
    return rows


def main():
    parser = argparse.ArgumentParser(description="Benchmark the /similarity retrieval API.")
    parser.add_argument("input_folder", help="Dataset folder containing filtered_ground_truth.csv and queries/")
    parser.add_argument("--url", default="http://localhost:8001/similarity", help="Similarity endpoint URL")
    parser.add_argument("--k", type=int, default=5, help="top-k to request from the API")
    parser.add_argument("--workers", type=int, default=8, help="Number of concurrent requests")
    parser.add_argument("--timeout", type=float, default=30.0, help="Per-request timeout in seconds")
    parser.add_argument("--prob-threshold", type=float, default=0.5,
                         help="duplicateProbability threshold for the headline precision/recall/F1 (top-1 only)")
    parser.add_argument("--sweep", action="store_true", help="Run a full threshold sweep over all candidates")
    parser.add_argument("--sweep-step", type=float, default=0.01, help="Step size for the threshold sweep")
    parser.add_argument("--target-accuracy", type=float, default=0.95,
                         help="Accuracy target to highlight in the sweep output")
    args = parser.parse_args()

    csv_path = os.path.join(args.input_folder, "filtered_ground_truth.csv")
    with open(csv_path, "r") as f:
        reader = csv.reader(f)
        next(reader)
        rows = list(reader)

    session = build_session()
    results = []

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(query_one, session, args.url, args.input_folder, row, args.k, args.timeout): row
            for row in rows
        }
        for future in tqdm(as_completed(futures), total=len(futures), desc="Benchmarking"):
            results.append(future.result())

    errors = [r for r in results if r.status == "error"]
    scored = [r for r in results if r.status in ("match", "miss")]
    matches = [r for r in scored if r.status == "match"]
    misses = [r for r in scored if r.status == "miss"]
    top1_matches = [r for r in matches if r.rank == 1]

    total = len(scored)
    correct = len(matches)
    accuracy = (correct / total * 100) if total else 0
    top1_accuracy = (len(top1_matches) / total * 100) if total else 0
    mrr = mean((1.0 / r.rank) for r in matches) if matches else 0.0

    avg_match_distance = mean(r.match_distance for r in matches) if matches else 0
    avg_miss_distance = mean(r.top1_distance for r in misses if r.top1_distance is not None) if misses else 0
    avg_match_prob = mean(r.match_probability for r in matches if r.match_probability is not None) if matches else 0
    avg_miss_prob = mean(r.top1_probability for r in misses if r.top1_probability is not None) if misses else 0

    tp = sum(1 for r in scored if r.status == "match" and r.rank == 1 and (r.top1_probability or 0) >= args.prob_threshold)
    fn = sum(1 for r in scored if r.status == "match" and r.rank == 1 and (r.top1_probability or 0) < args.prob_threshold)
    fp = sum(1 for r in scored if r.status == "miss" and (r.top1_probability or 0) >= args.prob_threshold)
    precision = tp / (tp + fp) if (tp + fp) else 0
    recall = tp / (tp + fn) if (tp + fn) else 0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0

    avg_latency = mean(r.latency_ms for r in results if r.latency_ms is not None) if results else 0

    print("\n--- Retrieval (threshold-independent) ---")
    print(f"Recall@{args.k}: {correct}/{total} ({accuracy:.2f}%)   <- hard ceiling, no threshold changes this")
    print(f"Top-1 accuracy: {len(top1_matches)}/{total} ({top1_accuracy:.2f}%)")
    print(f"MRR: {mrr:.4f}")
    print(f"Avg distance (matches): {avg_match_distance:.4f}")
    print(f"Avg distance (misses, top-1): {avg_miss_distance:.4f}")
    print(f"Avg duplicateProbability (matches): {avg_match_prob:.4f}")
    print(f"Avg duplicateProbability (misses, top-1): {avg_miss_prob:.4f}")

    print(f"\n--- Classification @ threshold {args.prob_threshold} (top-1 only) ---")
    print(f"Precision: {precision:.4f}  Recall: {recall:.4f}  F1: {f1:.4f}")

    print("\n--- Performance ---")
    print(f"Avg latency: {avg_latency:.1f} ms")
    print(f"Errors: {len(errors)}/{len(results)}")

    sources = sorted(set(r.source for r in scored))
    if len(sources) > 1:
        print("\n--- By source ---")
        for src in sources:
            src_rows = [r for r in scored if r.source == src]
            src_correct = sum(1 for r in src_rows if r.status == "match")
            print(f"  {src}: {src_correct}/{len(src_rows)} ({src_correct/len(src_rows)*100:.2f}%)")

    if errors:
        print("\nFirst few errors:")
        for r in errors[:5]:
            print(f"  {r.query_path}: {r.error}")

    summary_dir = os.path.join(args.input_folder, "benchmark_results", "summary")
    os.makedirs(summary_dir, exist_ok=True)

    summary_csv = os.path.join(summary_dir, "api_benchmark_summary.csv")
    with open(summary_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        writer.writerow(["correct", correct])
        writer.writerow(["total", total])
        writer.writerow(["accuracy_percent", accuracy])
        writer.writerow(["top1_accuracy_percent", top1_accuracy])
        writer.writerow(["mrr", mrr])
        writer.writerow(["avg_match_distance", avg_match_distance])
        writer.writerow(["avg_miss_distance", avg_miss_distance])
        writer.writerow(["avg_match_probability", avg_match_prob])
        writer.writerow(["avg_miss_probability", avg_miss_prob])
        writer.writerow(["precision_at_threshold", precision])
        writer.writerow(["recall_at_threshold", recall])
        writer.writerow(["f1_at_threshold", f1])
        writer.writerow(["avg_latency_ms", avg_latency])
        writer.writerow(["errors", len(errors)])
    print(f"\nSummary saved to {summary_csv}")

    detail_csv = os.path.join(summary_dir, "api_benchmark_details.csv")
    with open(detail_csv, "w", newline="") as f:
        writer = csv.writer(f)
        field_names = [k for k in asdict(results[0]).keys() if k != "candidates"] if results else []
        writer.writerow(field_names)
        for r in results:
            d = asdict(r)
            writer.writerow([d[k] for k in field_names])
    print(f"Per-query details saved to {detail_csv}")

    if args.sweep:
        candidate_records = [c for r in scored for c in r.candidates]
        sweep_rows = sweep_thresholds(candidate_records, step=args.sweep_step)

        sweep_csv = os.path.join(summary_dir, "threshold_sweep.csv")
        with open(sweep_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["threshold", "accuracy", "precision", "recall", "f1", "tp", "fp", "tn", "fn"])
            for row in sweep_rows:
                writer.writerow([row["threshold"], row["accuracy"], row["precision"],
                                  row["recall"], row["f1"], row["tp"], row["fp"], row["tn"], row["fn"]])
        print(f"Threshold sweep saved to {sweep_csv}")

        if sweep_rows:
            best_acc = max(sweep_rows, key=lambda r: r["accuracy"])
            best_f1 = max(sweep_rows, key=lambda r: r["f1"])
            meeting_target = [r for r in sweep_rows if r["accuracy"] >= args.target_accuracy]

            print(f"\n--- Threshold sweep (candidate-level, {len(candidate_records)} candidates) ---")
            print(f"Best ACCURACY: threshold={best_acc['threshold']:.2f} -> "
                  f"accuracy={best_acc['accuracy']*100:.2f}%, precision={best_acc['precision']:.4f}, "
                  f"recall={best_acc['recall']:.4f}, f1={best_acc['f1']:.4f}")
            print(f"Best F1:       threshold={best_f1['threshold']:.2f} -> "
                  f"accuracy={best_f1['accuracy']*100:.2f}%, precision={best_f1['precision']:.4f}, "
                  f"recall={best_f1['recall']:.4f}, f1={best_f1['f1']:.4f}")

            if meeting_target:
                # Prefer the lowest threshold that clears the target (higher recall side)
                chosen = min(meeting_target, key=lambda r: r["threshold"])
                print(f"\nThreshold(s) reaching >= {args.target_accuracy*100:.0f}% candidate-level accuracy: "
                      f"{len(meeting_target)} found. Lowest such threshold: {chosen['threshold']:.2f} "
                      f"(accuracy={chosen['accuracy']*100:.2f}%, precision={chosen['precision']:.4f}, "
                      f"recall={chosen['recall']:.4f}).")
            else:
                print(f"\nNo threshold reaches {args.target_accuracy*100:.0f}% candidate-level accuracy. "
                      f"Closest: threshold={best_acc['threshold']:.2f} at {best_acc['accuracy']*100:.2f}%.")
                print("Remember: this accuracy is capped below 100% partly because Recall@k "
                      f"is only {accuracy:.2f}% -- queries that never retrieved the true match "
                      "cannot be fixed by any threshold. Improving retrieval (index, k, embedding "
                      "model) is required to raise this further.")


if __name__ == "__main__":
    main()