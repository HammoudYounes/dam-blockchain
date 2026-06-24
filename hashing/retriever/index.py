import json
import os
import numpy as np
import faiss

class VectorIndex:
    def __init__(self, index_file: str, meta_file: str, embedding_dim: int = 384):
        self.index_file = index_file
        self.meta_file = meta_file
        self.embedding_dim = embedding_dim
        self.index_ids: dict[int, str] = {}
        self.query_references: dict[str, str] = {}
        self.next_id = 0
        self._initialize_index()

    def _initialize_index(self):
        hnsw_index = faiss.IndexHNSWFlat(self.embedding_dim, 32)
        hnsw_index.hnsw.efConstruction = 40
        hnsw_index.hnsw.efSearch = 64
        self.index = faiss.IndexIDMap(hnsw_index)

    def add(self, vector: np.ndarray, metadata: str):
        vector_f32 = np.array(vector, dtype="float32")
        new_id = self.next_id
        self.index.add_with_ids(vector_f32, np.array([new_id], dtype=np.int64))
        self.index_ids[new_id] = metadata
        self.next_id += 1
        return new_id

    def search(self, vector: np.ndarray, k: int):
        vector_f32 = np.array(vector, dtype="float32")
        return self.index.search(vector_f32, k=k)

    def save(self):
        os.makedirs(os.path.dirname(self.index_file), exist_ok=True)
        faiss.write_index(self.index, self.index_file)
        with open(self.meta_file, "w") as f:
            json.dump({
                "index_ids": self.index_ids,
                "query_references": self.query_references,
                "next_id": self.next_id,
            }, f)

    def load(self) -> bool:
        if not (os.path.exists(self.index_file) and os.path.exists(self.meta_file)):
            return False
        self.index = faiss.read_index(self.index_file)
        if not isinstance(self.index, faiss.IndexIDMap):
            self.index = faiss.IndexIDMap(self.index)
        with open(self.meta_file, "r") as f:
            meta = json.load(f)
        self.index_ids = {int(k): v for k, v in meta["index_ids"].items()}
        self.query_references = meta["query_references"]
        self.next_id = int(meta.get("next_id", max(self.index_ids.keys(), default=-1) + 1))
        return True

    def remove_ids(self, ids: np.ndarray):
        self.index.remove_ids(ids)
        for id in ids:
            self.index_ids.pop(int(id), None)
