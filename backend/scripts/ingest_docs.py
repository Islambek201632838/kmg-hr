"""
One-time script: load documents from remote PG -> chunk -> embed -> upsert to Qdrant.
Run: python -m scripts.ingest_docs
"""
import uuid

import psycopg2
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, PayloadSchemaType
from sentence_transformers import SentenceTransformer

from app.config import settings

CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
VECTOR_SIZE = 384


def fetch_documents():
    """Fetch active documents from remote PostgreSQL."""
    conn = psycopg2.connect(settings.remote_db_url.replace("+asyncpg", ""))
    cur = conn.cursor()
    cur.execute(
        "SELECT doc_id, doc_type, title, content, department_scope, keywords "
        "FROM documents WHERE is_active = true"
    )
    rows = cur.fetchall()
    conn.close()
    print(f"Fetched {len(rows)} documents from remote DB")
    return rows


def chunk_documents(rows):
    """Split documents into chunks with metadata."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = []
    for doc_id, doc_type, title, content, dept_scope, keywords in rows:
        if not content or not content.strip():
            continue
        texts = splitter.split_text(content)
        for i, text in enumerate(texts):
            chunks.append({
                "id": str(uuid.uuid4()),
                "text": text,
                "metadata": {
                    "doc_id": str(doc_id),
                    "doc_type": doc_type,
                    "title": title,
                    "department_scope": dept_scope,
                    "keywords": keywords or [],
                    "chunk_index": i,
                },
            })
    print(f"Created {len(chunks)} chunks from {len(rows)} documents")
    return chunks


def embed_and_upsert(chunks):
    """Embed chunks and upsert to Qdrant."""
    print(f"Loading embedding model: {settings.embedding_model}")
    model = SentenceTransformer(settings.embedding_model)

    texts = [c["text"] for c in chunks]
    print("Encoding chunks...")
    vectors = model.encode(texts, show_progress_bar=True, batch_size=64)

    client = QdrantClient(url=settings.qdrant_url)

    # Recreate collection
    collection = settings.qdrant_collection
    if client.collection_exists(collection):
        client.delete_collection(collection)

    client.create_collection(
        collection_name=collection,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )

    # Create payload indexes for filtering
    client.create_payload_index(collection, "doc_type", PayloadSchemaType.KEYWORD)
    client.create_payload_index(collection, "title", PayloadSchemaType.KEYWORD)
    client.create_payload_index(collection, "department_scope", PayloadSchemaType.KEYWORD)

    # Batch upsert
    BATCH = 100
    for i in range(0, len(chunks), BATCH):
        batch_chunks = chunks[i : i + BATCH]
        batch_vectors = vectors[i : i + BATCH]
        points = [
            PointStruct(
                id=c["id"],
                vector=v.tolist(),
                payload={**c["metadata"], "text": c["text"]},
            )
            for c, v in zip(batch_chunks, batch_vectors)
        ]
        client.upsert(collection_name=collection, points=points)

    print(f"Upserted {len(chunks)} points to Qdrant collection '{collection}'")


def main():
    rows = fetch_documents()
    chunks = chunk_documents(rows)
    embed_and_upsert(chunks)
    print("Done!")


if __name__ == "__main__":
    main()
