"""Vector DB service adapter."""

from __future__ import annotations


class VectorDBService:
    """Service for writing chunks/embeddings into vector DB."""

    def upsert_chunks(
        self,
        *,
        ingestion_job_id: str,
        user_id: str,
        chunks: list[dict[str, str]],
        execution_id: str,
    ) -> int:
        # Placeholder upsert behavior; replace with actual vector DB client.
        _ = ingestion_job_id, user_id, execution_id
        return len(chunks)
