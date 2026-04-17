from datetime import datetime, timezone
from pathlib import Path

STORE_ROOT = Path(__file__).resolve().parent / "stores"
STORE_ROOT.mkdir(parents=True, exist_ok=True)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_question(question: str) -> str:
    return " ".join(question.strip().lower().split())
