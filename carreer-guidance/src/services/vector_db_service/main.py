"""Vector database service implementation."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class VectorDBService:
    """Persist chunks to archive that can later be loaded into a real vector DB."""

    def __init__(self, execution_id: str, archive_file: str | None = None) -> None:
        self.execution_id = execution_id
        self.archive_file = archive_file

    def upsert_chunks(
        self,
        ingestion_job_id: str,
        user_id: str,
        chunks: list[dict],
    ) -> int:
        if not chunks:
            return 0

        archive_path = self._resolve_archive_path()
        archive_path.parent.mkdir(parents=True, exist_ok=True)

        written = 0
        with archive_path.open("a", encoding="utf-8") as fp:
            for chunk in chunks:
                payload = {
                    "ingestion_job_id": ingestion_job_id,
                    "user_id": user_id,
                    "execution_id": self.execution_id,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "chunk": chunk,
                }
                fp.write(json.dumps(payload, ensure_ascii=False) + "\n")
                written += 1

        logger.info(
            "upsert_chunks archived: ingestion_job_id=%s count=%s path=%s",
            ingestion_job_id,
            written,
            archive_path,
        )
        return written

    def _resolve_archive_path(self) -> Path:
        if self.archive_file:
            return Path(self.archive_file).expanduser().resolve()

        project_root = Path(__file__).resolve().parents[3]
        return project_root / "assets" / "openapi_examples" / "jds_vector_archive.jsonl"
