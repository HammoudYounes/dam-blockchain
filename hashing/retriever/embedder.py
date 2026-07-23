import io
import numpy as np
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModel

class ImageEmbedder:
    def __init__(self, model_size: str):
        self.model_size = model_size
        self.model = None
        self.image_processor = None
        self.device = None

    def initialize(self):
        model_name = f"facebook/dinov2-{self.model_size}"
        print(f"Loading {model_name}...")
        self.image_processor = AutoImageProcessor.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.model.eval()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = self.model.to(self.device)
        print(f"Model loaded on {self.device}")

    def embed_image(self, image: Image.Image) -> np.ndarray:
        inputs = self.image_processor(images=image, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            embedding = outputs.last_hidden_state[:, 0, :]
            embedding = embedding / embedding.norm(dim=-1, keepdim=True)
        return embedding.cpu().numpy()

    def get_embedding_from_path(self, image_path: str) -> np.ndarray:
        try:
            image = Image.open(image_path).convert("RGB").resize((224, 224))
            return self.embed_image(image)
        except Exception as e:
            raise ValueError(f"Cannot open image {image_path}: {e}")

    def get_embedding_from_bytes(self, image_bytes: bytes) -> np.ndarray:
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((224, 224))
            return self.embed_image(image)
        except Exception as e:
            raise ValueError(f"Cannot open image from bytes: {e}")
