"""
Document processing components for the scenario-builder service.
Handles chunking of extracted text for optimal retrieval.
"""

import hashlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import structlog

from ..config.settings import settings

log = structlog.get_logger()


SECTOR_KEYWORDS: Dict[str, List[str]] = {
    "banking": [
        "bank", "swift", "payment", "financial", "fraud", "atm", "wire transfer",
        "money laundering", "credit card", "fintech", "transaction", "iban",
    ],
    "energy": [
        "energy", "power grid", "electricity", "scada", "ics", "oil", "gas",
        "pipeline", "utilities", "water treatment", "critical infrastructure",
    ],
    "health": [
        "hospital", "healthcare", "medical", "patient", "ehr", "pacs",
        "pharmacy", "clinical", "health record", "diagnostic",
    ],
    "telecom": [
        "telecom", "telco", "5g", "network operator", "isp", "sim", "ss7",
        "roaming", "voip", "mobile network",
    ],
    "lea": [
        "law enforcement", "police", "cert", "csirt", "nca", "interpol",
        "europol", "ministry of interior", "government agency", "gdpr compliance",
    ],
}


def detect_sector(text: str) -> str:
    """
    Detect sector from text (filename, folder path, or query) using keyword matching.
    Returns the best-matching sector, or 'general' if none match.
    """
    text_lower = text.lower()
    scores: Dict[str, int] = {sector: 0 for sector in SECTOR_KEYWORDS}
    for sector, keywords in SECTOR_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                scores[sector] += 1
    best_sector = max(scores, key=lambda s: scores[s])
    return best_sector if scores[best_sector] > 0 else "general"


@dataclass
class DocumentChunk:
    """Represents a chunk of document content"""

    content: str
    chunk_id: str
    document_id: str
    document_name: str
    document_type: str
    chunk_index: int
    metadata: Dict[str, Any]
    project_name: str = "default"  # Project/folder name for organization
    sector: str = "general"        # Domain sector for filtered retrieval


class DocumentChunker:
    """Handles document chunking for optimal retrieval"""

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        separators: Optional[List[str]] = None,
    ):
        """
        Initialize chunker with configuration

        Args:
            chunk_size: Target size for chunks (in characters)
            chunk_overlap: Overlap between chunks (in characters)
            separators: List of separators to split on (in order of preference)
        """
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.separators = separators or [
            "\n\n",  # Paragraph breaks
            "\n",  # Line breaks
            ". ",  # Sentence ends
            "! ",  # Exclamation sentences
            "? ",  # Question sentences
            "; ",  # Semicolon
            ", ",  # Comma
            " ",  # Spaces
            "",  # Character level (last resort)
        ]

        log.info(
            "document_chunker_initialized",
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

    def chunk_document(self, text: str, document_metadata: Dict[str, Any]) -> List[DocumentChunk]:
        """
        Split document into chunks

        Args:
            text: Document text content
            document_metadata: Metadata about the document

        Returns:
            List of DocumentChunk objects
        """
        if not text.strip():
            return []

        # Split text into chunks
        chunks = self._split_text_recursive(text, self.separators)

        # Create DocumentChunk objects
        document_chunks = []
        for i, chunk_text in enumerate(chunks):
            if chunk_text.strip():  # Skip empty chunks
                chunk = DocumentChunk(
                    content=chunk_text.strip(),
                    chunk_id=f"{document_metadata['document_id']}_chunk_{i}",
                    document_id=document_metadata["document_id"],
                    document_name=document_metadata.get("file_name", "unknown"),
                    document_type=document_metadata.get("file_type", "unknown"),
                    chunk_index=i,
                    project_name=document_metadata.get("project_name", "default"),
                    sector=document_metadata.get("sector", "general"),
                    metadata={
                        "file_path": document_metadata.get("file_path", ""),
                        "file_size": document_metadata.get("file_size", 0),
                        "chunk_size": len(chunk_text),
                        "total_chunks": len(chunks),
                    },
                )
                document_chunks.append(chunk)

        log.info(
            "document_chunked",
            document_id=document_metadata["document_id"],
            total_chunks=len(document_chunks),
            avg_chunk_size=sum(len(c.content) for c in document_chunks) // len(document_chunks)
            if document_chunks
            else 0,
        )

        return document_chunks

    def _split_text_recursive(self, text: str, separators: List[str]) -> List[str]:
        """Recursively split text using different separators"""
        if len(text) <= self.chunk_size:
            return [text]

        # Try each separator
        for separator in separators:
            if separator in text:
                splits = text.split(separator)
                if len(splits) > 1:
                    return self._merge_splits(splits, separator)

        # If no separator found, force split
        return [
            text[i : i + self.chunk_size]
            for i in range(0, len(text), self.chunk_size - self.chunk_overlap)
        ]

    def _merge_splits(self, splits: List[str], separator: str) -> List[str]:
        """Merge splits into chunks of appropriate size"""
        chunks = []
        current_chunk = ""

        for split in splits:
            test_chunk = current_chunk + (separator if current_chunk else "") + split

            if len(test_chunk) <= self.chunk_size:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk)

                # If single split is too large, recursively split it
                if len(split) > self.chunk_size:
                    sub_chunks = self._split_text_recursive(split, self.separators[1:])
                    chunks.extend(sub_chunks[:-1])
                    current_chunk = sub_chunks[-1] if sub_chunks else ""
                else:
                    current_chunk = split

        if current_chunk:
            chunks.append(current_chunk)

        return chunks


class DocumentProcessor:
    """Main document processor for the scenario-builder service"""

    def __init__(self):
        """Initialize document processor"""
        self.chunker = DocumentChunker()

        log.info("document_processor_initialized")

    def process_extracted_document(self, extracted_data: Dict[str, Any]) -> List[DocumentChunk]:
        """
        Process extracted document data into chunks

        Args:
            extracted_data: Document data from extraction

        Returns:
            List of document chunks
        """
        try:
            extracted_text = extracted_data.get("extracted_text", "")
            file_name = extracted_data.get("file_name", "unknown")
            file_path = extracted_data.get("file_path", "")

            if not extracted_text.strip():
                log.warning("empty_extracted_text", file_name=file_name)
                return []

            # Generate document ID from file path
            document_id = self._generate_document_id(file_path)

            # Auto-detect sector from file path + name (override with explicit metadata if set)
            sector = extracted_data.get("sector") or detect_sector(f"{file_path} {file_name}")

            # Prepare metadata
            metadata = {
                "document_id": document_id,
                "file_name": file_name,
                "file_path": file_path,
                "file_type": extracted_data.get("file_type", "unknown"),
                "file_size": extracted_data.get("file_size", 0),
                "sector": sector,
            }

            # Chunk the document
            chunks = self.chunker.chunk_document(extracted_text, metadata)

            log.info(
                "document_processed",
                document_id=document_id,
                file_name=file_name,
                chunks_created=len(chunks),
                text_length=len(extracted_text),
            )

            return chunks

        except Exception as e:
            log.error(
                "document_processing_error",
                file_name=extracted_data.get("file_name", "unknown"),
                error=str(e),
            )
            return []

    def _generate_document_id(self, file_path: str) -> str:
        """
        Generate a unique document ID from file path

        Args:
            file_path: Path to the document

        Returns:
            Unique document ID
        """
        return hashlib.md5(file_path.encode()).hexdigest()
