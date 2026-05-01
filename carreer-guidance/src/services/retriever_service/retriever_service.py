import logging
import os
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from src.services.retriever_service.bm25_index import BM25Index

RETRIEVER_TOP_K = 20
RETRIEVER_FINAL_K = 10
RRF_K = 60


class RetrieverService:
    """Hybrid ChromaDB + BM25 retriever with Reciprocal Rank Fusion."""

    def __init__(
        self,
        *,
        execution_id: str,
        chroma_host: str = "localhost",
        chroma_port: int = 8000,
        collection_name: str = "career_guidance_chunks",
        chroma_client_mode: str = "http",
        chroma_persist_dir: str = "./chroma_data",
    ) -> None:
        self.execution_id = execution_id
        self.logger = logging.getLogger(f"{__name__}[{execution_id}]")

        self.chroma_host = chroma_host
        self.chroma_port = chroma_port
        self.collection_name = collection_name
        self.chroma_client_mode = (chroma_client_mode or "http").strip().lower()
        self.chroma_persist_dir = chroma_persist_dir

        self._client: Any = None
        self._collection: Any = None
        self._connected = False

        self.bm25_index = BM25Index()
        self._doc_ids: list[str] = []
        self._doc_texts: list[str] = []
        self._doc_metadatas: list[dict] = []

    def connect(self) -> None:
        try:
            os.environ["ANONYMIZED_TELEMETRY"] = "FALSE"
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            settings = ChromaSettings(anonymized_telemetry=False)

            if self.chroma_client_mode == "persistent":
                persist_path = Path(self.chroma_persist_dir).expanduser().resolve()
                persist_path.mkdir(parents=True, exist_ok=True)
                self._client = chromadb.PersistentClient(
                    path=str(persist_path),
                    settings=settings,
                )
                connection_label = str(persist_path)
            else:
                self._client = chromadb.HttpClient(
                    host=self.chroma_host,
                    port=self.chroma_port,
                    settings=settings,
                )
                self._client.heartbeat()
                connection_label = f"{self.chroma_host}:{self.chroma_port}"

            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self._connected = True
            count = self._collection.count()
            self.logger.info(
                "Connected to ChromaDB | mode=%s | endpoint=%s | collection=%s | docs=%d",
                self.chroma_client_mode,
                connection_label,
                self.collection_name,
                count,
            )
            if count > 0:
                self._sync_bm25_from_chroma()
        except Exception as exc:
            self.logger.error("ChromaDB connection failed: %s", exc)
            self._connected = False
            raise ConnectionError(
                f"Cannot connect to ChromaDB at {self.chroma_host}:{self.chroma_port}: {exc}"
            ) from exc

    def _sync_bm25_from_chroma(self) -> None:
        self.logger.info("Syncing BM25 index from ChromaDB...")
        all_data = self._collection.get(include=["documents", "metadatas"])
        self._doc_ids = all_data["ids"]
        self._doc_texts = all_data["documents"]
        self._doc_metadatas = all_data["metadatas"] or [{}] * len(self._doc_ids)
        if self._doc_texts:
            self.bm25_index.build(self._doc_texts)
            self.logger.info("BM25 synced: %d documents", len(self._doc_texts))
        else:
            self.logger.warning("No documents in ChromaDB to build BM25 index.")

    @property
    def is_ready(self) -> bool:
        return self._connected and self._collection is not None

    def search(
        self,
        query: str,
        query_embedding: np.ndarray,
        top_k: int = RETRIEVER_FINAL_K,
        dense_k: int = RETRIEVER_TOP_K,
        sparse_k: int = RETRIEVER_TOP_K,
        where: dict[str, Any] | None = None,
    ) -> List[Dict]:
        if not self.is_ready:
            raise RuntimeError("RetrieverService not connected. Call connect() first.")
        dense_results = self._chroma_search(query_embedding, dense_k, where)
        sparse_results = self._bm25_search(query, sparse_k)
        return self._rrf_fusion(dense_results, sparse_results, top_k)

    def _chroma_search(
        self,
        query_embedding: np.ndarray,
        k: int,
        where: dict[str, Any] | None = None,
    ) -> List[Dict]:
        embedding_list = query_embedding.tolist()
        kwargs: dict[str, Any] = {
            "query_embeddings": [embedding_list],
            "n_results": k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where
        try:
            results = self._collection.query(**kwargs)
        except Exception as exc:
            self.logger.warning(
                "Dense Chroma query failed, fallback to BM25 only for this request: %s",
                exc,
            )
            return []

        docs = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                doc: Dict[str, Any] = {
                    "chunk_id": results["ids"][0][i],
                    "text": results["documents"][0][i] if results["documents"] else "",
                    "distance": (
                        results["distances"][0][i] if results.get("distances") else 0.0
                    ),
                }
                if results.get("metadatas") and results["metadatas"][0]:
                    meta = results["metadatas"][0][i]
                    doc["metadata"] = meta
                    doc["source"] = meta.get("source", meta.get("file_path", "unknown"))
                    doc["title"] = meta.get("title", "")
                docs.append(doc)
        return docs

    def _bm25_search(self, query: str, k: int) -> List[Dict]:
        if not self.bm25_index.is_built or not self._doc_texts:
            return []
        scores, indices = self.bm25_index.search(query, k)
        docs = []
        for idx, score in zip(indices, scores):
            idx_int = int(idx)
            if idx_int < 0 or idx_int >= len(self._doc_texts):
                continue
            docs.append(
                {
                    "chunk_id": self._doc_ids[idx_int],
                    "text": self._doc_texts[idx_int],
                    "bm25_score": float(score),
                    "metadata": self._doc_metadatas[idx_int],
                    "source": self._doc_metadatas[idx_int].get(
                        "source",
                        self._doc_metadatas[idx_int].get("file_path", "unknown"),
                    ),
                    "title": self._doc_metadatas[idx_int].get("title", ""),
                }
            )
        return docs

    def _rrf_fusion(
        self,
        dense_results: List[Dict],
        sparse_results: List[Dict],
        top_k: int,
    ) -> List[Dict]:
        scores: dict[str, float] = {}
        doc_map: dict[str, Dict] = {}
        for rank, doc in enumerate(dense_results):
            cid = doc["chunk_id"]
            scores[cid] = scores.get(cid, 0) + 1.0 / (RRF_K + rank + 1)
            doc_map[cid] = doc
        for rank, doc in enumerate(sparse_results):
            cid = doc["chunk_id"]
            scores[cid] = scores.get(cid, 0) + 1.0 / (RRF_K + rank + 1)
            if cid not in doc_map:
                doc_map[cid] = doc
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[
            :top_k
        ]
        results = []
        for rank, cid in enumerate(sorted_ids):
            doc = doc_map[cid].copy()
            doc["score"] = scores[cid]
            doc["rank"] = rank + 1
            doc["retriever"] = "hybrid_chroma_bm25_rrf"
            results.append(doc)
        return results
