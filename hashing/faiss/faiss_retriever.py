import numpy as np
import faiss
import torch
from PIL import Image
import csv
import matplotlib.pyplot as plt
from transformers import AutoImageProcessor, AutoModel
import sys
import os
import json


class ImageRetriever:
    DEFAULT_MODEL = "large"
    MODEL_SIZES = ["small", "base", "large"]

    def __init__(self, model_size: str = None, index_dir: str = "."):
        model_size = model_size if model_size in self.MODEL_SIZES else self.DEFAULT_MODEL
        model_name = f"facebook/dinov2-{model_size}"

        self.index_file = os.path.join(
            index_dir, f"faiss_index_{model_size}.bin")
        self.meta_file = os.path.join(
            index_dir, f"faiss_index_{model_size}.json")

        self.index_ids: dict[int, str] = {}
        self.query_references: dict[str, str] = {}
        self._load_model(model_name)

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
        self.index = faiss.IndexFlatL2(d)
        print(f"Model loaded on {self.device} (embedding dim={d})")

    # ------------------------------------------------------------------ #
    #  Embedding                                                         #
    # ------------------------------------------------------------------ #

    def get_image_embedding(self, image_path: str) -> np.ndarray:
        try:
            image = Image.open(image_path).convert("RGB")
        except Exception as e:
            raise ValueError(f"Cannot open image {image_path}: {e}")

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
        faiss.write_index(self.index, self.index_file)
        with open(self.meta_file, "w") as f:
            json.dump({
                "index_ids": self.index_ids,
                "query_references": self.query_references
            }, f)
        print(f"Index saved → {self.index_file} | metadata → {self.meta_file}")

    def load(self) -> bool:
        """Try to load a previously saved index. Returns True on success."""
        if not (os.path.exists(self.index_file) and os.path.exists(self.meta_file)):
            return False

        print(f"Saved index found — loading from {self.index_file} ...")
        self.index = faiss.read_index(self.index_file)

        with open(self.meta_file, "r") as f:
            meta = json.load(f)

        self.index_ids = {int(k): v for k, v in meta["index_ids"].items()}
        self.query_references = meta["query_references"]
        print(f"Index loaded ({self.index.ntotal} vectors)")
        return True

    # ------------------------------------------------------------------ #
    #  Indexing                                                          #
    # ------------------------------------------------------------------ #

    def index_folder(self, input_folder: str, csv_name: str):
        csv_path = os.path.join(input_folder, csv_name)
        with open(csv_path, "r") as f:
            reader = csv.reader(f)
            next(reader)  # skip header

            for i, row in enumerate(reader):
                reference, query = row
                ref_path = os.path.join(input_folder, "references", reference)

                if i % 100 == 0:
                    print(f"Processing {i} ...")

                try:
                    embedding = self.get_image_embedding(ref_path)
                    self.index.add(np.array(embedding, dtype="float32"))
                    self.index_ids[i] = reference
                    self.query_references[query] = reference
                except Exception as e:
                    print(f"  Error on {reference} / {query}: {e}")

    # ------------------------------------------------------------------ #
    #  Evaluation                                                        #
    # ------------------------------------------------------------------ #

    def evaluate(self, input_folder: str, pause_time: float = 1.0, display_results: bool = True):
        total_first_matches = 0
        total_top5_matches = 0

        for i, (query, reference) in enumerate(self.query_references.items()):
            query_path = os.path.join(input_folder, "queries", query)

            try:
                query_embedding = self.get_image_embedding(query_path)
                D, I = self.index.search(
                    np.array(query_embedding, dtype="float32"), k=5)

                if self.index_ids[I[0][0]] == reference:
                    total_first_matches += 1

                is_matched = any(
                    self.index_ids[I[0][rank]] == reference for rank in range(5))
                if is_matched:
                    total_top5_matches += 1

                if display_results and is_matched:
                    self._display(query_path, input_folder,
                                  reference, I, D, pause_time)

                if i % 100 == 0:
                    print(f"Compared {i} queries ...")

            except Exception as e:
                print(f"  Error on query {query}: {e}")

        n = len(self.query_references)
        print(
            f"\nTop-1 accuracy : {total_first_matches / n * 100:.2f}%  ({total_first_matches}/{n})")
        print(
            f"Top-5 accuracy : {total_top5_matches / n * 100:.2f}%  ({total_top5_matches}/{n})")

    def _display(self, query_path: str, input_folder: str, reference: str, I, D, pause_time: float):
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
        input("Press Enter to continue...")
        plt.close(fig)


# ---------------------------------------------------------------------- #
#  Entry point                                                           #
# ---------------------------------------------------------------------- #

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python FAISS.py <DATASET_FOLDER> [small|base|large]")
        sys.exit(1)

    DATASET_FOLDER = sys.argv[1]
    MODEL_SIZE = sys.argv[2] if len(sys.argv) > 2 else "large"
    CSV_NAME = "filtered_ground_truth.csv"

    retriever = ImageRetriever(model_size=MODEL_SIZE, index_dir=DATASET_FOLDER)

    if not retriever.load():
        print("No saved index found — indexing from scratch ...")
        retriever.index_folder(DATASET_FOLDER, CSV_NAME)
        retriever.save()

    retriever.evaluate(DATASET_FOLDER, pause_time=1.0, display_results=False)
