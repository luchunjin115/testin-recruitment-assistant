from typing import Any

import chromadb

from app.core.config import get_settings


def get_chroma_client() -> Any:
    settings = get_settings()
    return chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)


def get_resume_collection() -> Any:
    settings = get_settings()
    client = get_chroma_client()
    return client.get_or_create_collection(settings.CHROMA_COLLECTION_RESUMES)
