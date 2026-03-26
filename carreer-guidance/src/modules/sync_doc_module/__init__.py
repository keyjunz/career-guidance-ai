"""Sync document module exports."""

from src.modules.sync_doc_module.interface import SyncDocumentModule
from src.modules.sync_doc_module.main import SyncDocumentModuleImpl

__all__ = [
    "SyncDocumentModule",
    "SyncDocumentModuleImpl",
]
