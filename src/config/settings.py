"""
Configuration settings for Scenario Builder Service.

Manages all environment-based configuration.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def _env_int(name: str, default: int) -> int:
    """Get integer from environment variable with default."""
    value = os.getenv(name)
    return int(value) if value is not None else default


def _env_float(name: str, default: float) -> float:
    """Get float from environment variable with default."""
    value = os.getenv(name)
    return float(value) if value is not None else default


def _env_bool(name: str, default: bool) -> bool:
    """Get boolean from environment variable with default."""
    value = os.getenv(name, "").lower()
    if value in ("true", "1", "yes", "on"):
        return True
    elif value in ("false", "0", "no", "off"):
        return False
    return default


def _env_path(name: str, default: str) -> Path:
    """Get Path from environment variable with default."""
    return Path(os.getenv(name, default))


@dataclass(frozen=True)
class Settings:
    """Configuration settings for Scenario Builder Service"""

    # Service configuration
    service_name: str = "Scenario Builder Service"
    service_port: int = _env_int("SERVICE_PORT", 8002)
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Data folder configuration
    data_folder: Path = _env_path("DATA_FOLDER", "./data")

    # Qdrant Configuration
    qdrant_host: str = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port: int = _env_int("QDRANT_PORT", 6333)
    collection_name: str = os.getenv("COLLECTION_NAME", "scenarios")
    embedding_dim: int = _env_int("EMBEDDING_DIM", 384)

    # Storage Configuration
    metadata_db_path: Path = _env_path("METADATA_DB_PATH", "./data/scenario_metadata.db")

    # Embedding Configuration
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "sentence_transformer")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    embedding_device: str = os.getenv("EMBEDDING_DEVICE", "cpu")
    embedding_batch_size: int = _env_int("EMBEDDING_BATCH_SIZE", 32)

    # Document Processing Configuration
    chunk_size: int = _env_int("CHUNK_SIZE", 1000)
    chunk_overlap: int = _env_int("CHUNK_OVERLAP", 200)
    max_chunk_size: int = _env_int("MAX_CHUNK_SIZE", 2000)

    # Retrieval Configuration
    default_top_k: int = _env_int("DEFAULT_TOP_K", 5)
    max_top_k: int = _env_int("MAX_TOP_K", 20)
    retrieval_alpha: float = _env_float("RETRIEVAL_ALPHA", 0.7)

    # LLM Configuration
    llm_api_url: str = os.getenv("LLM_API_URL", "http://localhost:11434/v1/chat/completions")
    llm_model: str = os.getenv("LLM_MODEL", "llama2")
    llm_temperature: float = _env_float("LLM_TEMPERATURE", 0.7)
    llm_seed: int = _env_int("LLM_SEED", 42)
    llm_stream: bool = _env_bool("LLM_STREAM", False)

    def get_embedding_config(self) -> Dict[str, Any]:
        """Get embedding configuration as dictionary"""
        return {
            "provider_type": self.embedding_provider,
            "model_name": self.embedding_model,
            "device": self.embedding_device,
            "batch_size": self.embedding_batch_size,
        }

    def get_storage_config(self) -> Dict[str, Any]:
        """Get storage configuration as dictionary"""
        return {
            "metadata_db_path": str(self.metadata_db_path),
            "qdrant_host": self.qdrant_host,
            "qdrant_port": self.qdrant_port,
            "collection_name": self.collection_name,
            "embedding_dim": self.embedding_dim,
        }

    def get_chunking_config(self) -> Dict[str, Any]:
        """Get chunking configuration as dictionary"""
        return {
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "max_chunk_size": self.max_chunk_size,
        }

    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration as dictionary"""
        return {
            "api_url": self.llm_api_url,
            "model": self.llm_model,
            "temperature": self.llm_temperature,
            "seed": self.llm_seed,
            "stream": self.llm_stream,
        }


# Global settings instance
settings = Settings()
