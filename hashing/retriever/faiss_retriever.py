import io
import numpy as np
import faiss
import torch
from PIL import Image
import csv
#import matplotlib.pyplot as plt
from transformers import AutoImageProcessor, AutoModel
import sys
import os
import json
from tqdm import tqdm


class ImageRetriever:
    DEFAULT_MODEL = "small"
    MODEL_SIZES = ["small", "base", "large"]

    def __init__(self, model_size: str = None, dataset_dir: str = "."):
        model_size = model_size if model_size in self.MODEL_SIZES else self.DEFAULT_MODEL
        self.model_size = model_size
        model_name = f"facebook/dinov2-{model_size}"

        if not os.path.isabs(dataset_dir):
            package_root = os.path.abspath(
                os.path.join(os.path.dirname(__file__), ".."))
            dataset_dir = os.path.join(package_root, dataset_dir)

        self.dataset_dir = os.path.normpath(dataset_dir)
        self.index_file = os.path.join(
            self.dataset_dir, "index", f"faiss_index_{model_size}.bin")
        self.meta_file = os.path.join(
            self.dataset_dir, "index", f"faiss_index_{model_size}.json")

        self.index_ids: dict[int, str] = {}
        self.query_references: dict[str, str] = {}
        self.next_id = 0
        self._load_model(model_name)
        
        if not self.load():
            print("No saved index found — indexing from scratch ...")
            self.index_folder(self.dataset_dir)
            self.save()

    # ------------------------------------------------------------------ #
    #  Model                                                             #
    # ------------------------------------------------------------------ #

    def _load_model(self, model_name: str):
        print(f"Loading {model_name}...")
        self.image_processor = AutoImageProcessor.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.model.eval()
        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu")
        self.model = self.model.to(self.device)

        d = self.model.config.hidden_size
        hnsw_index = faiss.IndexHNSWFlat(d, 32)
        hnsw_index.hnsw.efConstruction = 40
        hnsw_index.hnsw.efSearch = 64
        self.index = faiss.IndexIDMap(hnsw_index)
        print(f"Model loaded on {self.device} (embedding dim={d}, HNSW M=32)")

    # ------------------------------------------------------------------ #
    #  Embedding                                                         #
    # ------------------------------------------------------------------ #

    def get_image_embedding(self, image_path: str) -> np.ndarray:
        try:
            image = Image.open(image_path).convert("RGB").resize((224, 224))
        except Exception as e:
            raise ValueError(f"Cannot open image {image_path}: {e}")

        return self._embed_image(image)

    def get_image_embedding_from_bytes(self, image_bytes: bytes) -> np.ndarray:
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((224, 224))
        except Exception as e:
            raise ValueError(f"Cannot open image from bytes: {e}")

        return self._embed_image(image)

    def _embed_image(self, image: Image.Image) -> np.ndarray:
        inputs = self.image_processor(images=image, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            embedding = outputs.last_hidden_state[:, 0, :]
            embedding = embedding / embedding.norm(dim=-1, keepdim=True)

        return embedding.cpu().numpy()

    # ------------------------------------------------------------------ #
    #  Index persistence                                                 #
    # ------------------------------------------------------------------ #

    def save(self):
        os.makedirs(os.path.dirname(self.index_file), exist_ok=True)
        faiss.write_index(self.index, self.index_file)
        with open(self.meta_file, "w") as f:
            json.dump({
                "index_ids": self.index_ids,
                "query_references": self.query_references,
                "next_id": self.next_id,
            }, f)
        print(f"Index saved → {self.index_file} | metadata → {self.meta_file}")

    def load(self) -> bool:
        """Try to load a previously saved index. Returns True on success."""
        if not (os.path.exists(self.index_file) and os.path.exists(self.meta_file)):
            return False

        print(f"Saved index found — loading from {self.index_file} ...")
        self.index = faiss.read_index(self.index_file)
        if not isinstance(self.index, faiss.IndexIDMap):
            self.index = faiss.IndexIDMap(self.index)

        with open(self.meta_file, "r") as f:
            meta = json.load(f)

        self.index_ids = {int(k): v for k, v in meta["index_ids"].items()}
        self.query_references = meta["query_references"]
        self.next_id = int(meta.get("next_id", max(self.index_ids.keys(), default=-1) + 1))
        print(f"Index loaded ({self.index.ntotal} vectors)")
        return True

    # ------------------------------------------------------------------ #
    #  Indexing                                                          #
    # ------------------------------------------------------------------ #

    def index_folder(self, input_folder: str, csv_name: str = "filtered_ground_truth.csv"):
        csv_path = os.path.join(input_folder, csv_name)
        with open(csv_path, "r") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            rows = list(reader)

            for i, row in enumerate(tqdm(rows, desc="Indexing", total=len(rows))):
                reference, query = row
                ref_path = os.path.join(input_folder, "references", reference)

                try:
                    embedding = self.get_image_embedding(ref_path)
                    vector = np.array(embedding, dtype="float32")
                    self.index.add_with_ids(vector, np.array([self.next_id], dtype=np.int64))
                    self.index_ids[self.next_id] = reference
                    self.query_references[query] = reference
                    self.next_id += 1
                except Exception as e:
                    print(f"  Error on {reference} / {query}: {e}")
    
    def index_image(self, image_path: str):
        try:
            embedding = self.get_image_embedding(image_path)
            vector = np.array(embedding, dtype="float32")
            new_id = self.next_id
            self.index.add_with_ids(vector, np.array([new_id], dtype=np.int64))
            self.index_ids[new_id] = os.path.basename(image_path)
            self.next_id += 1
            print(f"Image indexed: {image_path} (ID: {new_id})")
            return {"success": True, "image_id": new_id, "image_name": os.path.basename(image_path)}
        except Exception as e:
            print(f"Error indexing image {image_path}: {e}")
            return {"success": False, "error": str(e)}   

    def index_image_from_bytes(self, image_bytes: bytes, image_name: str):
        try:
            embedding = self.get_image_embedding_from_bytes(image_bytes)
            vector = np.array(embedding, dtype="float32")
            new_id = self.next_id
            self.index.add_with_ids(vector, np.array([new_id], dtype=np.int64))
            self.index_ids[new_id] = image_name
            self.next_id += 1
            print(f"Image indexed from bytes: {image_name} (ID: {new_id})")
            return {"success": True, "image_id": new_id, "image_name": image_name}
        except Exception as e:
            print(f"Error indexing image from bytes {image_name}: {e}")
            return {"success": False, "error": str(e)}   

    def remove_image(self, image_id: int):
        if image_id not in self.index_ids:
            print(f"Image ID {image_id} not found in index.")
            return False

        self.index.remove_ids(np.array([image_id], dtype=np.int64))
        removed_image = self.index_ids.pop(image_id)
        print(f"Image removed: {removed_image} (ID: {image_id})")
        return True

    # ------------------------------------------------------------------ #
    #  Evaluation                                                        #
    # ------------------------------------------------------------------ #

    def evaluate(self, input_folder: str, pause_time: float = 1.0, display_results: bool = True, k: int = 5):
        total_topk_matches = 0
        total_match_disances = 0

        for _, (query, reference) in enumerate(tqdm(self.query_references.items(), desc="Comparing queries", total=len(self.query_references))):
            query_path = os.path.join(input_folder, "queries", query)

            try:
                query_embedding = self.get_image_embedding(query_path)
                D, I = self.index.search(
                    np.array(query_embedding, dtype="float32"), k=k)

                is_matched = any(
                    self.index_ids[I[0][rank]] == reference for rank in range(k))
                if is_matched:
                    total_topk_matches += 1
                    for rank in range(k):
                        if self.index_ids[I[0][rank]] == reference:
                            total_match_disances += D[0][rank]
                            break

                if display_results and is_matched:
                    self._display(query_path, input_folder,
                                  reference, I, D, pause_time)

            except Exception as e:
                print(f"  Error on query {query}: {e}")

        n = len(self.query_references)
        average_distance = total_match_disances / n 
        match_rate = total_topk_matches / n
        if display_results:
            print(f"\nEvaluation completed: {total_topk_matches}/{n} matches (Top-{k} match rate: {match_rate:.2%})")
            print(f"Average distance: {average_distance:.4f}")
        return average_distance, match_rate

    def _display(self, query_path: str, input_folder: str, reference: str, I, D, pause_time: float):
        pass
        """
        retrieved_ref = self.index_ids[I[0][0]]
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))

        for ax, img_path, title in zip(axes, [
            query_path,
            os.path.join(input_folder, "references", retrieved_ref),
            os.path.join(input_folder, "references", reference),
        ], ["Query", f"Retrieved: {retrieved_ref}", f"Ground Truth: {reference}"]):
            ax.imshow(Image.open(img_path))
            ax.set_title(title)
            ax.axis("off")

        match_label = "MATCH" if retrieved_ref == reference else "MISMATCH"
        plt.suptitle(f"Distance: {D[0][0]:.4f} — {match_label}", fontsize=16)
        plt.tight_layout()
        plt.show(block=False)
        plt.pause(pause_time)
        plt.close(fig)
        """

    def get_similar_images(self, query_image_path: str, k: int = 5):
        query_embedding = self.get_image_embedding(query_image_path)
        D, I = self.index.search(np.array(query_embedding, dtype="float32"), k=k)
        similar_images = [
            (self.index_ids[int(I[0][rank])], float(D[0][rank]))
            for rank in range(k)]
        return similar_images

    def get_similar_images_from_bytes(self, image_bytes: bytes, k: int = 5):
        query_embedding = self.get_image_embedding_from_bytes(image_bytes)
        D, I = self.index.search(np.array(query_embedding, dtype="float32"), k=k)
        similar_images = [
            (self.index_ids[int(I[0][rank])], float(D[0][rank]))
            for rank in range(k)]
        return similar_images

# ---------------------------------------------------------------------- #
#  Entry point                                                           #
# ---------------------------------------------------------------------- #

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python FAISS.py <DATASET_FOLDER> [small|base|large]")
        sys.exit(1)

    DATASET_FOLDER = sys.argv[1]
    MODEL_SIZE = sys.argv[2] if len(sys.argv) > 2 else "large"

    retriever = ImageRetriever(model_size=MODEL_SIZE, dataset_dir=DATASET_FOLDER)

    retriever.evaluate(DATASET_FOLDER, pause_time=1.0, display_results=False)
