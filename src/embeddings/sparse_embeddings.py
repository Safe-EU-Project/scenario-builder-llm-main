"""
Sparse embedding service using FastEmbed BM25.
"""

from typing import Any, Dict, List

import structlog
from fastembed import SparseTextEmbedding
from qdrant_client.models import SparseVector

log = structlog.get_logger()


class SparseEmbeddingService:
    """Service for generating sparse embeddings using BM25"""

    def __init__(self, model_name: str = "Qdrant/bm25"):
        """
        Initialize sparse embedding service

        Args:
            model_name: FastEmbed sparse model name
        """
        try:
            self.model_name = model_name
            self.model = SparseTextEmbedding(model_name=model_name)
            log.info("sparse_embedding_service_initialized", model_name=model_name)
        except Exception as e:
            log.error("sparse_embedding_init_failed", model_name=model_name, error=str(e))
            raise

    def embed_documents(self, texts: List[str]) -> List[SparseVector]:
        """
        Generate sparse embeddings for documents

        Args:
            texts: List of document texts

        Returns:
            List of sparse vectors
        """
        try:
            sparse_embeddings = list(self.model.embed(texts))

            # Convert to Qdrant SparseVector format
            sparse_vectors = []
            for embedding in sparse_embeddings:
                # FastEmbed returns sparse embeddings as dict with indices and values
                indices = embedding.indices.tolist()
                values = embedding.values.tolist()

                sparse_vectors.append(SparseVector(indices=indices, values=values))

            log.debug(
                "sparse_embeddings_generated", count=len(sparse_vectors), model=self.model_name
            )

            return sparse_vectors

        except Exception as e:
            log.error(
                "sparse_embedding_failed",
                texts_count=len(texts),
                model=self.model_name,
                error=str(e),
            )
            raise

    def embed_query(self, text: str) -> SparseVector:
        """
        Generate sparse embedding for a single query

        Args:
            text: Query text

        Returns:
            Sparse vector
        """
        try:
            sparse_vectors = self.embed_documents([text])
            return sparse_vectors[0]

        except Exception as e:
            log.error(
                "sparse_query_embedding_failed",
                text_length=len(text),
                model=self.model_name,
                error=str(e),
            )
            raise

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the sparse embedding model

        Returns:
            Model information dictionary
        """
        return {"model_name": self.model_name, "model_type": "sparse_bm25", "provider": "fastembed"}
