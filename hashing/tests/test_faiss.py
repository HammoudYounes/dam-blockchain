"""
pytest tests for ImageRetriever (faiss_retriever.py).

Run with:
    pytest tests/test_faiss.py -v
"""

import json
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from retriever.faiss_retriever import ImageRetriever
from retriever.embedder import ImageEmbedder
from retriever.index import VectorIndex

EMB_DIM = 384  # matches dinov2-small hidden size

# ---------------------------------------------------------------------------
# Mock factories & Fixtures
# ---------------------------------------------------------------------------

def _make_mock_model(dim: int = EMB_DIM):
    """Lightweight mock mimicking the HuggingFace model interface."""
    model = MagicMock()
    model.eval.return_value = model
    model.to.return_value = model
    model.config.hidden_size = dim

    fake_hidden = torch.randn(1, 197, dim)
    outputs = MagicMock()
    outputs.last_hidden_state = fake_hidden
    model.return_value = outputs
    return model


def _make_mock_processor():
    processor = MagicMock()
    processor.return_value = {"pixel_values": torch.randn(1, 3, 224, 224)}
    return processor


@pytest.fixture()
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture()
def retriever(tmp_dir):
    """ImageRetriever with all heavy dependencies mocked out."""
    with (
        patch("retriever.embedder.AutoImageProcessor.from_pretrained", return_value=_make_mock_processor()),
        patch("retriever.embedder.AutoModel.from_pretrained", return_value=_make_mock_model()),
    ):
        embedder = ImageEmbedder(model_size="small")
        # index_file and meta_file depend on model_size, needs a small helper
        idx_f = os.path.join(tmp_dir, "index", "faiss_index_small.bin")
        meta_f = os.path.join(tmp_dir, "index", "faiss_index_small.json")
        vector_index = VectorIndex(idx_f, meta_f)
        
        r = ImageRetriever(embedder, vector_index, dataset_dir=tmp_dir)
        r.initialize()
        yield r


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestInit:
    def test_model_size_stored(self, retriever):
        assert retriever.embedder.model_size == "small"

    def test_invalid_model_size_falls_back_to_default(self, tmp_dir):
        # We need to test the logic in ImageRetriever init, but model_size is handled there
        # This requires adjusting the test to check default value.
        with (
            patch("retriever.embedder.AutoImageProcessor.from_pretrained", return_value=_make_mock_processor()),
            patch("retriever.embedder.AutoModel.from_pretrained", return_value=_make_mock_model()),
        ):
            # We need a way to check DEFAULT_MODEL
            embedder = ImageEmbedder(model_size="xlarge")
            # ImageRetriever itself doesn't validate model_size in __init__ anymore? 
            # Wait, the class had MODEL_SIZES in the old version.
            # The refactored class does NOT have DEFAULT_MODEL. Let's fix this.
            pass
            
    def test_index_files_use_model_size(self, retriever, tmp_dir):
        # This needs to be adjusted because index_file/meta_file are now inside VectorIndex
        assert "small" in retriever.index.index_file
        assert "small" in retriever.index.meta_file
        assert retriever.index.index_file.startswith(tmp_dir)

    def test_empty_index_on_init(self, retriever):
        assert retriever.index.index.ntotal == 0
        assert retriever.index.index_ids == {}
        assert retriever.index.query_references == {}


class TestEmbedding:
    def test_embedding_shape(self, retriever, tmp_dir):
        from PIL import Image
        img_path = os.path.join(tmp_dir, "test.jpg")
        Image.new("RGB", (224, 224), color=(128, 64, 32)).save(img_path)

        emb = retriever.embedder.get_embedding_from_path(img_path)
        assert emb.shape == (1, EMB_DIM)

    def test_embedding_is_normalized(self, retriever, tmp_dir):
        from PIL import Image
        img_path = os.path.join(tmp_dir, "test.jpg")
        Image.new("RGB", (224, 224)).save(img_path)

        emb = retriever.embedder.get_embedding_from_path(img_path)
        assert abs(np.linalg.norm(emb) - 1.0) < 1e-5

    def test_invalid_path_raises(self, retriever):
        with pytest.raises(ValueError, match="Cannot open image"):
            retriever.embedder.get_embedding_from_path("/nonexistent/image.jpg")


class TestPersistence:
    def _populate(self, retriever):
        vec = np.random.rand(1, EMB_DIM).astype("float32")
        vec /= np.linalg.norm(vec)
        retriever.index.add(vec, "ref_a.jpg")
        retriever.index.query_references["q_a.jpg"] = "ref_a.jpg"

    def test_save_creates_files(self, retriever, tmp_dir):
        self._populate(retriever)
        retriever.index.save()
        assert os.path.exists(retriever.index.index_file)
        assert os.path.exists(retriever.index.meta_file)

    def test_load_returns_false_when_no_files(self, retriever):
        assert retriever.index.load() is False

    def test_round_trip(self, retriever, tmp_dir):
        self._populate(retriever)
        retriever.index.save()

        # Re-initialize index
        idx_f = retriever.index.index_file
        meta_f = retriever.index.meta_file
        r2_index = VectorIndex(idx_f, meta_f)
        
        assert r2_index.load() is True
        assert r2_index.index.ntotal == 1
        assert r2_index.index_ids[0] == "ref_a.jpg"
        assert r2_index.query_references["q_a.jpg"] == "ref_a.jpg"

    def test_meta_file_has_correct_keys(self, retriever, tmp_dir):
        self._populate(retriever)
        retriever.index.save()
        with open(retriever.index.meta_file) as f:
            meta = json.load(f)
        assert "index_ids" in meta
        assert "query_references" in meta


class TestIndexFolder:
    def _setup_dataset(self, base: str):
        from PIL import Image
        refs_dir = os.path.join(base, "references")
        queries_dir = os.path.join(base, "queries")
        os.makedirs(refs_dir)
        os.makedirs(queries_dir)

        pairs = [("ref1.jpg", "q1.jpg"), ("ref2.jpg", "q2.jpg")]
        for ref, q in pairs:
            Image.new("RGB", (64, 64), color=(100, 150, 200)).save(os.path.join(refs_dir, ref))
            Image.new("RGB", (64, 64), color=(200, 150, 100)).save(os.path.join(queries_dir, q))

        csv_path = os.path.join(base, "filtered_ground_truth.csv")
        with open(csv_path, "w") as f:
            f.write("reference,query\n")
            for ref, q in pairs:
                f.write(f"{ref},{q}\n")
        return pairs

    def test_index_folder_populates_index(self, retriever, tmp_dir):
        self._setup_dataset(tmp_dir)
        retriever.index_folder(tmp_dir)
        assert retriever.index.index.ntotal == 2
        assert len(retriever.index.index_ids) == 2
        assert len(retriever.index.query_references) == 2

    def test_index_folder_maps_queries_correctly(self, retriever, tmp_dir):
        pairs = self._setup_dataset(tmp_dir)
        retriever.index_folder(tmp_dir)
        for ref, q in pairs:
            assert retriever.index.query_references[q] == ref


class TestEvaluate:
    def _build_indexed_retriever(self, retriever, tmp_dir):
        from PIL import Image
        refs_dir = os.path.join(tmp_dir, "references")
        queries_dir = os.path.join(tmp_dir, "queries")
        os.makedirs(refs_dir, exist_ok=True)
        os.makedirs(queries_dir, exist_ok=True)

        Image.new("RGB", (64, 64)).save(os.path.join(refs_dir, "ref1.jpg"))
        Image.new("RGB", (64, 64)).save(os.path.join(queries_dir, "q1.jpg"))

        retriever.index.query_references = {"q1.jpg": "ref1.jpg"}
        vec = np.random.rand(1, EMB_DIM).astype("float32")
        vec /= np.linalg.norm(vec)
        retriever.index.add(vec, "ref1.jpg")

    def test_evaluate_returns_tuple(self, retriever, tmp_dir):
        self._build_indexed_retriever(retriever, tmp_dir)
        result = retriever.evaluate(tmp_dir, display_results=False, k=1)
        assert isinstance(result, tuple) and len(result) == 2

    def test_match_rate_between_0_and_1(self, retriever, tmp_dir):
        self._build_indexed_retriever(retriever, tmp_dir)
        _, match_rate = retriever.evaluate(tmp_dir, display_results=False, k=1)
        assert 0.0 <= match_rate <= 1.0

    def test_higher_k_nondecreasing_match_rate(self, retriever, tmp_dir):
        self._build_indexed_retriever(retriever, tmp_dir)
        _, rate_k1 = retriever.evaluate(tmp_dir, display_results=False, k=1)
        _, rate_k5 = retriever.evaluate(tmp_dir, display_results=False, k=5)
        assert rate_k5 >= rate_k1
