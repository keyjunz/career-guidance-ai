from enum import Enum


class DocSyncStatus(str, Enum):
    START = "start"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
