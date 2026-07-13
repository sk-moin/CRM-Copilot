from enum import Enum


class DocumentProcessingStatus(str, Enum):
    UPLOADED = "UPLOADED"
    PARSING = "PARSING"
    CHUNKING = "CHUNKING"
    EMBEDDING = "EMBEDDING"
    READY = "READY"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"