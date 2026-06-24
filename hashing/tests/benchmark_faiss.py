"""
Benchmarking Faiss against the brute-force method for nearest neighbor search.
"""

import os
import sys
from time import time

sys.path.insert(0,
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from retriever.faiss_retriever import ImageRetriever

K_VALUES = [1, 3, 5, 10, 20, 50, 100]

def benchmark_faiss(faiss_retriever: ImageRetriever, dataset_folder: str, k_values: list[int], csv_results: str = None):
    """
    Benchmark the Faiss retriever across multiple k values.
    """
    if not faiss_retriever.load():
        print("Building Faiss index...")
        faiss_retriever.index_folder(dataset_folder)
        faiss_retriever.save()

    print(f"Evaluating Faiss retriever ({faiss_retriever.model_size}) for k={k_values}...")

    for k in k_values:
        start_time = time()
        average_distance, match_rate = faiss_retriever.evaluate(
            input_folder=dataset_folder, display_results=False, k=k
        )
        print(f"  k={k}: match_rate={match_rate:.2%}, avg_distance={average_distance:.4f}")

        end_time = time()
        time_taken = end_time - start_time

        if csv_results:
            with open(csv_results, "a") as f:
                f.write(f"{faiss_retriever.model_size},{k},{average_distance:.4f},{match_rate:.2%},{time_taken:.2f}\n")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python benchmark_faiss.py <DATASET_FOLDER>")
        sys.exit(1)

    DATASET_FOLDER = sys.argv[1]
    CSV_RESULTS = os.path.join(os.path.dirname(__file__), "..", "benchmark_results", "faiss_benchmark.csv")

    os.makedirs(os.path.dirname(CSV_RESULTS), exist_ok=True)
    with open(CSV_RESULTS, "w") as f:
        f.write("model_size,k,average_distance,match_rate,time\n")

    for model_size in ImageRetriever.MODEL_SIZES:
        faiss_retriever = ImageRetriever(model_size=model_size, index_dir=DATASET_FOLDER)
        benchmark_faiss(faiss_retriever, DATASET_FOLDER, k_values=K_VALUES, csv_results=CSV_RESULTS)