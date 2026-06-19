import os
import sys
import tqdm

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from hashing.algorithms.Chash import CHash

def ensure_dir(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

def benchmark_own(own_folder):
    pass
    """
    folder_reference = os.path.join(own_folder, "images")
    folder_altered = os.path.join(own_folder, "images_variants")
    csv_path = "../benchmark_results/n_own_benchmarks.csv"
    ensure_dir(csv_path)
    
    print(f"Starting Own Benchmark. Results saved to {csv_path}")
    
    with open(csv_path, "w") as f:
        f.write("image1,image2,transformation,hamming_distance,similarity\n")
        
        # Filter only image files
        ref_files = [img for img in os.listdir(folder_reference) if img.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        
        for reference in tqdm.tqdm(ref_files, desc="Processing Own Dataset"):
            # 1. PRE-HASH the reference image (Speed boost)
            ref_path = os.path.join(folder_reference, reference)
            img1 = CHash(ref_path)
            
            # Identify the folder for variants
            variant_subfolder = os.path.join(folder_altered, os.path.splitext(reference)[0])
            
            if os.path.exists(variant_subfolder):
                for altered in os.listdir(variant_subfolder):
                    if not altered.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                        continue
                        
                    img2 = CHash(os.path.join(variant_subfolder, altered))
                    
                    hamming_distance = img1.hamming_distance(img2)
                    similarity = img1.similarity(img2)
                    
                    f.write(f"{reference},{altered},{altered.split('.')[0]},{hamming_distance},{similarity:.03f}\n")
    """

def benchmark_disc21(disc21_folder):
    folder_queries = os.path.join(disc21_folder, "queries")
    folder_references = os.path.join(disc21_folder, "references")
    csv_ground_truth = os.path.join(disc21_folder, "filtered_ground_truth.csv")
    csv_path = "../benchmark_results/chash_disc21_benchmarks.csv"
    ensure_dir(csv_path)

    # Use a cache to avoid re-hashing the same image multiple times (Massive Speed boost)
    hash_cache = {}

    def get_hash(path):
        if path not in hash_cache:
            hash_cache[path] = CHash(path)
        return hash_cache[path]

    if not os.path.exists(csv_ground_truth):
        print(f"Skipping DISC21: {csv_ground_truth} not found.")
        return

    print(f"Starting DISC21 Benchmark. Results saved to {csv_path}")

    with open(csv_path, "w") as f:
        f.write("Query,Reference,hamming_distance,similarity\n")
        
        with open(csv_ground_truth, "r") as gt:
            lines = gt.readlines()
            # If there's a header, skip it. If no header, remove [1:]
            for line in tqdm.tqdm(lines[1:], desc="Processing DISC21", leave=True):
                parts = line.strip().split(",")
                if len(parts) < 2:
                    continue
                
                reference, query = parts[0], parts[1]
                
                try:
                    img1 = get_hash(os.path.join(folder_queries, query))
                    img2 = get_hash(os.path.join(folder_references, reference))
                    
                    h_dist = img1.hamming_distance(img2)
                    sim = img1.similarity(img2)
                    f.write(f"{query},{reference},{h_dist},{sim:.03f}\n")
                except Exception as e:
                    print(f"Error processing {query} and {reference}: {e}")
                    continue

def main(own_folder, disc21_folder):
    print("Initializing NHash Benchmarking Suite...")
    benchmark_own(own_folder)
    benchmark_disc21(disc21_folder)
    print("Benchmarking Complete.")

if __name__ == "__main__":
    # Base dir of the current script
    BASE = os.path.dirname(os.path.abspath(__file__))
    
    # Adjusting paths to be absolute relative to this script
    OWN = os.path.abspath(os.path.join(BASE, "../data/own/")) + "/"
    DISC = os.path.abspath(os.path.join(BASE, "../data/disc21/")) + "/"
    
    main(OWN, DISC)