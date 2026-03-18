"""
Build Vector Database — Tạo FAISS index và Chroma collection từ chunked data.
Cache embeddings bằng pickle để tránh tính toán lại.
"""

import json
import pickle
import time
import numpy as np
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))
from config import DATA_DIR, INDEX_DIR, CACHE_DIR, DEFAULT_EMBEDDING, EMBEDDING_MODELS
from models.embedding import EmbeddingModel
from models.retriever import HybridRetriever


def build_faiss_index(
    chunks_file: str = None,
    embedding_model_key: str = DEFAULT_EMBEDDING,
    batch_size: int = 64,
    force_recompute: bool = False,
):
    """
    Build FAISS index + BM25 index từ chunked data.
    Cache embeddings bằng pickle.
    """
    if chunks_file is None:
        chunks_file = str(DATA_DIR / "chunks.json")

    print("=" * 60)
    print("  BUILD VECTOR DATABASE")
    print("=" * 60)

    # Load chunks
    with open(chunks_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"Loaded {len(chunks)} chunks from {chunks_file}")

    # Load embedding model
    emb_model = EmbeddingModel(model_key=embedding_model_key)
    dim = emb_model.dim

    # Check cache
    cache_file = CACHE_DIR / f"passage_embeddings_{embedding_model_key}.pkl"

    if cache_file.exists() and not force_recompute:
        print(f"Loading cached embeddings from {cache_file}...")
        with open(cache_file, "rb") as f:
            embeddings = pickle.load(f)
        print(f"Loaded embeddings shape: {embeddings.shape}")

        # Verify size match
        if embeddings.shape[0] != len(chunks):
            print(f"Cache size mismatch ({embeddings.shape[0]} != {len(chunks)}). Recomputing...")
            force_recompute = True

    if not cache_file.exists() or force_recompute:
        print(f"Computing embeddings for {len(chunks)} chunks...")
        texts = [c["text"] for c in chunks]

        start = time.perf_counter()
        embeddings = emb_model.encode_passages(texts, batch_size=batch_size, show_progress=True)
        elapsed = time.perf_counter() - start

        print(f"Embedding time: {elapsed:.1f}s ({len(chunks) / elapsed:.0f} chunks/s)")
        print(f"Embeddings shape: {embeddings.shape}")

        # Cache embeddings
        with open(cache_file, "wb") as f:
            pickle.dump(embeddings, f)
        print(f"Cached embeddings to {cache_file}")

    # Build hybrid retriever index
    retriever = HybridRetriever(dim=dim)
    retriever.build_index(chunks, embeddings)
    retriever.save(prefix="retriever")

    print("\n[Done] Vector database built and saved!")
    print(f"  FAISS index: {INDEX_DIR / 'retriever_faiss.index'}")
    print(f"  BM25 index:  {INDEX_DIR / 'retriever_bm25.pkl'}")
    print(f"  Documents:   {INDEX_DIR / 'retriever_docs.json'}")

    return retriever


def build_chroma_index(
    chunks_file: str = None,
    embedding_model_key: str = DEFAULT_EMBEDDING,
    batch_size: int = 64,
):
    """Build Chroma collection từ chunked data (tùy chọn)."""
    try:
        import chromadb
    except ImportError:
        print("[Chroma] chromadb not installed. pip install chromadb")
        return None

    if chunks_file is None:
        chunks_file = str(DATA_DIR / "chunks.json")

    with open(chunks_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"[Chroma] Building from {len(chunks)} chunks...")

    # Load embedding model
    emb_model = EmbeddingModel(model_key=embedding_model_key)

    # Load cached embeddings if available
    cache_file = CACHE_DIR / f"passage_embeddings_{embedding_model_key}.pkl"
    if cache_file.exists():
        with open(cache_file, "rb") as f:
            embeddings = pickle.load(f)
    else:
        texts = [c["text"] for c in chunks]
        embeddings = emb_model.encode_passages(texts, batch_size=batch_size, show_progress=True)

    # Create Chroma client
    client = chromadb.PersistentClient(path=str(INDEX_DIR / "chroma_db"))
    
    # Delete existing collection if it exists
    try:
        client.delete_collection("ai_cs_knowledge")
    except Exception:
        pass
    
    collection = client.create_collection(
        name="ai_cs_knowledge",
        metadata={"description": "AI/CS knowledge base for RAG chatbot"},
    )

    # Add in batches (Chroma has limit per batch)
    chroma_batch_size = 500
    for i in range(0, len(chunks), chroma_batch_size):
        batch_end = min(i + chroma_batch_size, len(chunks))
        batch_chunks = chunks[i:batch_end]
        batch_embeddings = embeddings[i:batch_end]

        collection.add(
            ids=[str(c["chunk_id"]) for c in batch_chunks],
            embeddings=batch_embeddings.tolist(),
            documents=[c["text"] for c in batch_chunks],
            metadatas=[
                {"source": c["source"], "title": c.get("title", ""), "url": c.get("url", "")}
                for c in batch_chunks
            ],
        )

    print(f"[Chroma] Created collection with {collection.count()} documents")
    return collection


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build Vector Database")
    parser.add_argument("--chunks-file", type=str, default=None)
    parser.add_argument("--embedding", type=str, default=DEFAULT_EMBEDDING)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--force-recompute", action="store_true")
    parser.add_argument("--backend", type=str, default="faiss", choices=["faiss", "chroma", "both"])
    args = parser.parse_args()

    if args.backend in ("faiss", "both"):
        build_faiss_index(
            chunks_file=args.chunks_file,
            embedding_model_key=args.embedding,
            batch_size=args.batch_size,
            force_recompute=args.force_recompute,
        )

    if args.backend in ("chroma", "both"):
        build_chroma_index(
            chunks_file=args.chunks_file,
            embedding_model_key=args.embedding,
            batch_size=args.batch_size,
        )
