"""
Text Chunker - Split text into optimal chunks for embedding
"""
import re
from typing import List, Dict, Optional


class TextChunker:
    """Split text into overlapping chunks for RAG retrieval."""

    def __init__(
        self,
        chunk_size: int = 500,
        overlap: int = 50,
        min_chunk_length: int = 100
    ):
        """
        Initialize TextChunker.

        Args:
            chunk_size: Target size of each chunk (in characters)
            overlap: Number of characters to overlap between chunks
            min_chunk_length: Minimum length to consider as valid chunk
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_chunk_length = min_chunk_length

    def chunk_text(
        self,
        text: str,
        source: str = "",
        metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Split text into chunks with metadata.

        Args:
            text: Text to split
            source: Source document name
            metadata: Additional metadata for the chunk

        Returns:
            List of chunk dictionaries
        """
        if not text or len(text.strip()) < self.min_chunk_length:
            return []

        # Clean text
        text = self._clean_text(text)

        chunks = []
        start = 0
        chunk_num = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end]

            # Don't cut in the middle of a word
            if end < len(text) and text[end] not in ' \n\t':
                # Find last space
                last_space = chunk_text.rfind(' ')
                if last_space > self.chunk_size // 2:
                    chunk_text = chunk_text[:last_space]
                    end = start + last_space

            chunk = {
                "chunk_id": f"{source}_{chunk_num}" if source else f"chunk_{chunk_num}",
                "text": chunk_text.strip(),
                "start_pos": start,
                "end_pos": end,
                "source": source,
                "metadata": metadata or {}
            }
            chunks.append(chunk)

            chunk_num += 1
            start = end - self.overlap

        return [c for c in chunks if len(c["text"]) >= self.min_chunk_length]

    def chunk_by_paragraph(
        self,
        text: str,
        source: str = "",
        metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Split text by paragraphs first, then merge small ones.

        Args:
            text: Text to split
            source: Source document name
            metadata: Additional metadata

        Returns:
            List of chunk dictionaries
        """
        # Split by paragraph breaks
        paragraphs = re.split(r'\n\s*\n', text)

        chunks = []
        current_chunk = []
        current_length = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_len = len(para)

            # If single paragraph exceeds chunk_size, chunk it directly
            if para_len > self.chunk_size:
                if current_chunk:
                    chunks.extend(self._create_chunks(current_chunk, source, chunks, metadata))
                    current_chunk = []
                    current_length = 0

                # Split long paragraph
                chunks.extend(self.chunk_text(para, source, metadata))
                continue

            # Check if adding this paragraph exceeds chunk_size
            if current_length + para_len + 1 > self.chunk_size and current_chunk:
                chunks.extend(self._create_chunks(current_chunk, source, chunks, metadata))
                current_chunk = []
                current_length = 0

            current_chunk.append(para)
            current_length += para_len + 1

        # Don't forget the last chunk
        if current_chunk:
            chunks.extend(self._create_chunks(current_chunk, source, chunks, metadata))

        return [c for c in chunks if len(c["text"]) >= self.min_chunk_length]

    def _create_chunks(
        self,
        paragraphs: List[str],
        source: str,
        existing_chunks: List[Dict],
        metadata: Optional[Dict]
    ) -> List[Dict]:
        """Create chunks from paragraphs."""
        text = '\n\n'.join(paragraphs)
        chunk_num = len(existing_chunks)

        return [{
            "chunk_id": f"{source}_{chunk_num}" if source else f"chunk_{chunk_num}",
            "text": text.strip(),
            "start_pos": 0,
            "end_pos": len(text),
            "source": source,
            "metadata": metadata or {}
        }]

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove excessive whitespace
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

        # Remove special characters but keep Chinese and important punctuation
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', '', text)

        return text.strip()

    def get_chunk_preview(self, chunk: Dict, max_length: int = 100) -> str:
        """Get a preview of a chunk."""
        text = chunk.get("text", "")
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."