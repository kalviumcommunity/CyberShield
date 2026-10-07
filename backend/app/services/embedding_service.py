import json
from typing import List, Optional
from sentence_transformers import SentenceTransformer

# Model configuration
MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384

# Global singleton model instance to ensure efficient loading
_model_instance: Optional[SentenceTransformer] = None


def get_embedding_model() -> SentenceTransformer:
    """
    Lazy-loads and returns the singleton SentenceTransformer model instance.
    Ensures model is loaded efficiently only once per process.
    """
    global _model_instance
    if _model_instance is None:
        print(f"Loading SentenceTransformer model '{MODEL_NAME}'...")
        _model_instance = SentenceTransformer(MODEL_NAME)
        print(f"SentenceTransformer model '{MODEL_NAME}' loaded successfully.")
    return _model_instance


def generate_embedding(text: str) -> List[float]:
    """
    Generates a 384-dimensional dense vector embedding for a single text string.
    """
    if not text or not text.strip():
        return [0.0] * EMBEDDING_DIMENSION

    model = get_embedding_model()
    vector = model.encode(text, convert_to_numpy=True)
    return vector.tolist()


def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Generates 384-dimensional dense vector embeddings for a list of text strings in batch.
    """
    if not texts:
        return []

    cleaned_texts = [t.strip() if t and t.strip() else " " for t in texts]
    model = get_embedding_model()
    vectors = model.encode(cleaned_texts, batch_size=32, convert_to_numpy=True)
    return [vec.tolist() for vec in vectors]


def serialize_embedding(embedding_vector: List[float]) -> str:
    """
    Serializes a float vector list into a JSON string for database storage.
    """
    return json.dumps(embedding_vector)


def deserialize_embedding(embedding_str: str) -> List[float]:
    """
    Deserializes a JSON string back into a float vector list.
    """
    if not embedding_str:
        return []
    return json.loads(embedding_str)
