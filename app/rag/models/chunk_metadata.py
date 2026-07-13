from dataclasses import dataclass


@dataclass(slots=True)
class ChunkMetadata:
    """Metadata for a chunk of text.

    Attributes:
        chunk_index: Index of the chunk in the document.
        start_char: Starting character index of the chunk.
        end_char: Ending character index of the chunk.
        token_count: Number of tokens in the chunk.
    """

    chunk_index: int
    start_char: int
    end_char: int
    token_count: int