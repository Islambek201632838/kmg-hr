"""
Delete Qdrant collection and re-ingest with Gemini embeddings.
Run: docker compose exec hr-api python -m scripts.reset_qdrant
"""
from qdrant_client import QdrantClient
from app.config import settings
from scripts.ingest_docs import fetch_documents, chunk_documents, embed_and_upsert


def main():
    client = QdrantClient(url=settings.qdrant_url)
    collection = settings.qdrant_collection

    # Step 1: Delete old collection
    if client.collection_exists(collection):
        client.delete_collection(collection)
        print(f"Deleted collection '{collection}'")
    else:
        print(f"Collection '{collection}' does not exist, creating fresh")

    # Step 2: Re-ingest with Gemini embeddings
    rows = fetch_documents()
    chunks = chunk_documents(rows)
    embed_and_upsert(chunks)
    print("Done! Qdrant re-indexed with Gemini gemini-embedding-001 (3072d)")


if __name__ == "__main__":
    main()