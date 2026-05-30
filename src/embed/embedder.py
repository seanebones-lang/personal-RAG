from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model = None

def get_model():
    global _model
    if _model is None:
        print(f"Loading embedding model: {MODEL_NAME}")
        _model = SentenceTransformer(MODEL_NAME, device="cpu")
    return _model

def embed_texts(texts: List[str]) -> np.ndarray:
    model = get_model()
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    return embeddings

def embed_query(text: str) -> np.ndarray:
    model = get_model()
    return model.encode([text], convert_to_numpy=True)[0]