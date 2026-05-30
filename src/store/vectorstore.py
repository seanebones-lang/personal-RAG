import chromadb
from chromadb.config import Settings
from pathlib import Path
from typing import List, Dict
import numpy as np

DB_PATH = Path.home() / ".personalragvault" / "chroma"

def get_client():
    DB_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(DB_PATH),
        settings=Settings(anonymized_telemetry=False)
    )

def get_collection(name: str = "personal_knowledge"):
    client = get_client()
    return client.get_or_create_collection(name=name)

def add_documents(docs: List[Dict]):
    """docs = [{"id": , "text": , "embedding": , "metadata": }]"""
    collection = get_collection()
    ids = [d["id"] for d in docs]
    embeddings = [d["embedding"].tolist() for d in docs]
    texts = [d["text"] for d in docs]
    metadatas = [d.get("metadata", {}) for d in docs]

    collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
    print(f"Added {len(docs)} documents to vector store")

def search(query_embedding: np.ndarray, top_k: int = 5) -> List[Dict]:
    collection = get_collection()
    results = collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )
    return [
        {
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i]
        }
        for i in range(len(results["documents"][0]))
    ]