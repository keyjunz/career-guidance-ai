import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class VectorDBService:
    """Ingest chunks into ChromaDB with semantic embeddings."""

    def __init__(
        self,
        execution_id: str,
        embedding_service: Any | None = None,
        chroma_client: Any | None = None,
    ) -> None:
        self.execution_id = execution_id
        self.embedding_service = embedding_service
        self.chroma_client = chroma_client
        self.collection = None

        # ChromaDB configuration
        self.chroma_host = os.getenv("CHROMA_HOST", "localhost")
        self.chroma_port = int(os.getenv("CHROMA_PORT", "8001"))
        self.collection_name = os.getenv(
            "CHROMA_COLLECTION_NAME", "career_guidance_documents"
        )
        self.persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
        self.client_mode = os.getenv("CHROMA_CLIENT_MODE", "persistent").strip().lower()

        self._initialize_chroma()

    def _silence_chroma_telemetry_logs(self) -> None:
        """Silence noisy telemetry warnings from Chroma/PostHog integration."""
        for logger_name in [
            "chromadb.telemetry.product.posthog",
            "chromadb.telemetry.product",
            "posthog",
        ]:
            telemetry_logger = logging.getLogger(logger_name)
            telemetry_logger.setLevel(logging.CRITICAL)

    def _is_legacy_topic_column_error(self, exc: Exception) -> bool:
        message = str(exc)
        return "no such column:" in message and ".topic" in message

    def _repair_legacy_topic_columns_in_place(self) -> bool:
        """Repair legacy Chroma SQLite schema in-place for single DB mode."""
        if self.client_mode == "http":
            return False

        persist_path = Path(self.persist_dir).expanduser().resolve()
        sqlite_path = persist_path / "chroma.sqlite3"
        if not sqlite_path.exists():
            return False

        logger.warning(
            "Detected legacy Chroma schema in %s. Applying in-place topic-column repair.",
            sqlite_path,
        )

        table_columns_to_add = {
            "collections": ["topic"],
            "segments": ["topic"],
        }

        repaired = False
        with sqlite3.connect(str(sqlite_path)) as conn:
            cursor = conn.cursor()
            for table_name, columns in table_columns_to_add.items():
                cursor.execute(f"PRAGMA table_info({table_name})")
                existing_columns = {row[1] for row in cursor.fetchall()}
                for column_name in columns:
                    if column_name not in existing_columns:
                        cursor.execute(
                            f"ALTER TABLE {table_name} ADD COLUMN {column_name} TEXT"
                        )
                        repaired = True
            if repaired:
                conn.commit()

        if repaired:
            logger.warning("Chroma schema repaired in-place at %s.", sqlite_path)
        return repaired

    def _initialize_chroma(self) -> None:
        """Initialize ChromaDB client and collection."""
        try:
            if self.chroma_client is None:
                os.environ["ANONYMIZED_TELEMETRY"] = "FALSE"
                self._silence_chroma_telemetry_logs()

                # Compatibility shim for libraries expecting np.float_ on NumPy >= 2.0.
                try:
                    import numpy as np

                    if not hasattr(np, "float_"):
                        np.float_ = np.float64  # type: ignore[attr-defined]
                except Exception:
                    pass

                import chromadb
                from chromadb.config import Settings as ChromaSettings

                chroma_settings = ChromaSettings(anonymized_telemetry=False)

                persist_path = Path(self.persist_dir).expanduser().resolve()

                if self.client_mode == "http":
                    self.chroma_client = chromadb.HttpClient(
                        host=self.chroma_host,
                        port=self.chroma_port,
                        settings=chroma_settings,
                    )
                    self.chroma_client.heartbeat()
                else:
                    persist_path.mkdir(parents=True, exist_ok=True)
                    self.chroma_client = chromadb.PersistentClient(
                        path=str(persist_path),
                        settings=chroma_settings,
                    )

            # Get or create collection with embedding function
            try:
                self.collection = self.chroma_client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception as collection_exc:
                if self._is_legacy_topic_column_error(collection_exc):
                    repaired = self._repair_legacy_topic_columns_in_place()
                    if repaired:
                        self.collection = self.chroma_client.get_or_create_collection(
                            name=self.collection_name,
                            metadata={"hnsw:space": "cosine"},
                        )
                        return

                raise RuntimeError(
                    "Failed to initialize configured Chroma collection "
                    f"'{self.collection_name}': {collection_exc}"
                ) from collection_exc

            logger.info(
                "ChromaDB initialized: collection=%s, host=%s, port=%s",
                self.collection_name,
                self.chroma_host,
                self.chroma_port,
            )
        except Exception as exc:
            logger.warning(
                "ChromaDB initialization failed: %s (will skip vector DB ingestion)",
                exc,
            )
            self.collection = None

    def upsert_chunks(
        self,
        ingestion_job_id: str,
        user_id: str,
        chunks: list[dict],
    ) -> int:
        """Ingest chunks into ChromaDB with embeddings."""
        if not chunks:
            return 0

        if self.collection is None:
            logger.warning("ChromaDB collection not available, skipping ingestion")
            return 0

        try:
            documents = []
            ids = []
            metadatas = []
            embeddings = []

            for chunk in chunks:
                chunk_id = chunk.get("chunk_id", "")
                text = chunk.get("text", "")
                metadata = chunk.get("metadata", {})

                if not text:
                    continue

                # Get embedding from service
                embedding = None
                if self.embedding_service:
                    try:
                        embedding = self.embedding_service.get_embedding(text)
                    except Exception as exc:
                        logger.warning(
                            "Failed to get embedding for chunk %s: %s", chunk_id, exc
                        )

                documents.append(text)
                ids.append(chunk_id)

                # Add ingestion metadata
                metadata.update(
                    {
                        "ingestion_job_id": ingestion_job_id,
                        "user_id": user_id,
                        "execution_id": self.execution_id,
                    }
                )
                metadatas.append(metadata)

                if embedding:
                    embeddings.append(embedding)

            def _execute_upsert() -> None:
                # Upsert to ChromaDB
                if embeddings and len(embeddings) == len(documents):
                    self.collection.upsert(
                        ids=ids,
                        documents=documents,
                        embeddings=embeddings,
                        metadatas=metadatas,
                    )
                else:
                    # Upsert without pre-computed embeddings (ChromaDB will compute them)
                    self.collection.upsert(
                        ids=ids,
                        documents=documents,
                        metadatas=metadatas,
                    )

            try:
                _execute_upsert()
            except Exception as upsert_exc:
                if self._is_legacy_topic_column_error(upsert_exc):
                    repaired = self._repair_legacy_topic_columns_in_place()
                    if repaired:
                        _execute_upsert()
                    else:
                        raise
                else:
                    raise

            logger.info(
                "Ingested to ChromaDB: ingestion_job_id=%s, count=%d, collection=%s",
                ingestion_job_id,
                len(documents),
                self.collection_name,
            )
            return len(documents)

        except Exception as exc:
            logger.error(
                "ChromaDB upsert failed: ingestion_job_id=%s error=%s",
                ingestion_job_id,
                exc,
            )
            return 0

    def query_similar(
        self,
        query_text: str,
        user_id: str | None = None,
        top_k: int = 5,
    ) -> list[dict]:
        """Query similar chunks from ChromaDB."""
        if self.collection is None:
            logger.warning("ChromaDB collection not available, cannot query")
            return []

        try:
            # Build filter for user_id if provided
            where_filter = None
            if user_id:
                where_filter = {"user_id": {"$eq": user_id}}

            results = self.collection.query(
                query_texts=[query_text],
                n_results=top_k,
                where=where_filter,
            )

            # Format results
            formatted_results = []
            if results and results.get("documents"):
                for i, doc in enumerate(results["documents"][0]):
                    formatted_results.append(
                        {
                            "chunk_id": (
                                results["ids"][0][i] if results["ids"] else None
                            ),
                            "text": doc,
                            "distance": (
                                results["distances"][0][i]
                                if results["distances"]
                                else None
                            ),
                            "metadata": (
                                results["metadatas"][0][i]
                                if results["metadatas"]
                                else {}
                            ),
                        }
                    )

            return formatted_results

        except Exception as exc:
            logger.error("ChromaDB query failed: query=%s error=%s", query_text, exc)
            return []
