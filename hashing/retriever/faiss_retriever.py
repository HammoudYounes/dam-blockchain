import os
import csv
import numpy as np
from tqdm import tqdm
from .embedder import ImageEmbedder
from .index import VectorIndex

class ImageRetriever:
    DEFAULT_MODEL = "small"
    MODEL_SIZES = ["small", "base", "large"]

    def __init__(self, embedder: ImageEmbedder, vector_index: VectorIndex, dataset_dir: str = "."):
        self.embedder = embedder
        self.index = vector_index
        self.dataset_dir = os.path.normpath(dataset_dir)

    def initialize(self):
        self.embedder.initialize()
        if not self.index.load():
            print("No saved index found — indexing from scratch ...")
            csv_path = os.path.join(self.dataset_dir, "filtered_ground_truth.csv")
            if os.path.exists(csv_path):
                self.index_folder(self.dataset_dir)
                self.index.save()
            else:
                print("No dataset CSV found, skipping initial indexing.")

    def index_folder(self, input_folder: str, csv_name: str = "filtered_ground_truth.csv"):
        csv_path = os.path.join(input_folder, csv_name)
        with open(csv_path, "r") as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)
            for row in tqdm(rows, desc="Indexing"):
                reference, query = row
                ref_path = os.path.join(input_folder, "references", reference)
                try:
                    embedding = self.embedder.get_embedding_from_path(ref_path)
                    self.index.add(embedding, reference)
                    self.index.query_references[query] = reference
                except Exception as e:
                    print(f"Error on {reference} / {query}: {e}")

    def index_image(self, image_path: str):
        try:
            embedding = self.embedder.get_embedding_from_path(image_path)
            image_name = os.path.basename(image_path)
            new_id = self.index.add(embedding, image_name)
            return {"success": True, "image_id": new_id, "image_name": image_name}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def index_image_from_bytes(self, image_bytes: bytes, image_name: str):
        try:
            embedding = self.embedder.get_embedding_from_bytes(image_bytes)
            new_id = self.index.add(embedding, image_name)
            return {"success": True, "image_id": new_id, "image_name": image_name}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def remove_image(self, image_id: int):
        if image_id not in self.index.index_ids:
            return False
        self.index.remove_ids(np.array([image_id], dtype=np.int64))
        return True

    def get_similar_images(self, query_image_path: str, k: int = 5):
        embedding = self.embedder.get_embedding_from_path(query_image_path)
        D, I = self.index.search(embedding, k=k)
        return [(self.index.index_ids[int(idx)], float(dist)) for idx, dist in zip(I[0], D[0])]

    def get_similar_images_from_bytes(self, image_bytes: bytes, k: int = 5):
        embedding = self.embedder.get_embedding_from_bytes(image_bytes)
        D, I = self.index.search(embedding, k=k)
        return [(self.index.index_ids[int(idx)], float(dist)) for idx, dist in zip(I[0], D[0])]

    def evaluate(self, input_folder: str, pause_time: float = 1.0, display_results: bool = True, k: int = 5):
        total_topk_matches = 0
        total_match_distances = 0
        queries = self.index.query_references
        
        for query, reference in tqdm(queries.items(), desc="Comparing queries"):
            query_path = os.path.join(input_folder, "queries", query)
            try:
                embedding = self.embedder.get_embedding_from_path(query_path)
                D, I = self.index.search(embedding, k=k)
                is_matched = any(self.index.index_ids[I[0][rank]] == reference for rank in range(k))
                if is_matched:
                    total_topk_matches += 1
                    for rank in range(k):
                        if self.index.index_ids[I[0][rank]] == reference:
                            total_match_distances += D[0][rank]
                            break
            except Exception as e:
                print(f"Error on query {query}: {e}")

        n = len(queries)
        return total_match_distances / n, total_topk_matches / n
