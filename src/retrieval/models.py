"""
Data models for retrieval system.
"""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class RetrievalResult:
    """Result from document retrieval"""

    content: str
    score: float
    source: str
    project_name: str
    document_name: str
    document_type: str
    chunk_id: str
    metadata: Dict[str, Any]
