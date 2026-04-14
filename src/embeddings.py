from typing import List
from .clients import openai_client
from .config import settings

def get_embedding(text: str) -> List[float]:
    text = text.replace("\n", " ")
    resp = openai_client.embeddings.create(
        model=settings.embedding_model,
        input=text,
        dimensions=settings.vector_dim
    )
    return resp.data[0].embedding