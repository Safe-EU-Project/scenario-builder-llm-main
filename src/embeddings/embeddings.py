"""
Embedding service for generating vector embeddings from text.
"""

import time
from typing import Any, Dict, List

import numpy as np
import structlog
import torch
from sentence_transformers import SentenceTransformer

from ..config.settings import settings

log = structlog.get_logger()


class EmbeddingService:
    """Self-contained embedding service using sentence-transformers"""

    def __init__(self):
        """Initialize embedding service with configuration"""
        try:
            # Get model configuration from settings
            self.model_name = settings.embedding_model
            self.device = settings.embedding_device
            self.batch_size = settings.embedding_batch_size

            # Load the sentence transformer model
            log.info("loading_embedding_model", model=self.model_name, device=self.device)

            self.model = SentenceTransformer(self.model_name)

            # Move model to specified device
            if self.device == "cuda" and torch.cuda.is_available():
                self.model = self.model.to("cuda")
                log.info("model_moved_to_cuda")
            elif self.device == "cpu":
                self.model = self.model.to("cpu")
                log.info("model_using_cpu")
            else:
                # Fallback to CPU if CUDA not available
                self.model = self.model.to("cpu")
                log.warning("cuda_not_available_fallback_to_cpu")

            # Get embedding dimension
            self.dimension = self.model.get_sentence_embedding_dimension()

            log.info(
                "embedding_service_initialized",
                model=self.model_name,
                dimension=self.dimension,
                device=self.device,
                batch_size=self.batch_size,
            )

        except Exception as e:
            log.error("embedding_service_init_failed", error=str(e))
            raise

    def embed_chunks(self, chunks: List[Any]) -> List[List[float]]:
        """
        Generate embeddings for document chunks

        Args:
            chunks: List of DocumentChunk objects

        Returns:
            List of embedding vectors
        """
        try:
            if not chunks:
                return []

            start_time = time.time()

            # Extract text content from chunks
            texts = [chunk.content for chunk in chunks]

            # Generate embeddings using sentence transformers
            embeddings = self._embed_texts_batch(texts)

            processing_time = time.time() - start_time

            log.info(
                "chunks_embedded",
                chunk_count=len(chunks),
                embedding_dimension=self.dimension,
                processing_time=processing_time,
            )

            return embeddings

        except Exception as e:
            log.error("chunk_embedding_failed", chunk_count=len(chunks), error=str(e))
            raise

    def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a single query

        Args:
            query: Query text

        Returns:
            Query embedding vector
        """
        try:
            start_time = time.time()

            # Generate embedding for single query
            embedding = self.model.encode(
                [query], convert_to_tensor=False, show_progress_bar=False
            )[0]
            embedding_list = embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)

            processing_time = time.time() - start_time

            log.debug(
                "query_embedded",
                query_length=len(query),
                embedding_dimension=len(embedding_list),
                processing_time=processing_time,
            )

            return embedding_list

        except Exception as e:
            log.error("query_embedding_failed", query_length=len(query), error=str(e))
            raise

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts

        Args:
            texts: List of text strings

        Returns:
            List of embedding vectors
        """
        try:
            if not texts:
                return []

            start_time = time.time()

            # Generate embeddings with batching
            embeddings = self._embed_texts_batch(texts)

            processing_time = time.time() - start_time

            log.info(
                "texts_embedded",
                text_count=len(texts),
                embedding_dimension=self.dimension,
                processing_time=processing_time,
            )

            return embeddings

        except Exception as e:
            log.error("text_embedding_failed", text_count=len(texts), error=str(e))
            raise

    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        """
        Alias for embed_texts for compatibility

        Args:
            documents: List of document text strings

        Returns:
            List of embedding vectors
        """
        return self.embed_texts(documents)

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        return {
            "model_name": self.model_name,
            "dimension": self.dimension,
            "device": self.device,
            "batch_size": self.batch_size,
            "provider_type": "SentenceTransformerProvider",
        }

    def get_dimension(self) -> int:
        """Get embedding dimension"""
        return self.dimension

    def get_model_name(self) -> str:
        """Get model name"""
        return self.model_name

    def _embed_texts_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings with batching for efficient processing

        Args:
            texts: List of text strings

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        embeddings = []

        # Process texts in batches
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i : i + self.batch_size]

            # Generate embeddings for batch
            batch_embeddings = self.model.encode(
                batch_texts,
                convert_to_tensor=False,
                show_progress_bar=False,
                batch_size=len(batch_texts),
            )

            # Convert to list format
            if isinstance(batch_embeddings, np.ndarray):
                batch_embeddings_list = batch_embeddings.tolist()
            else:
                batch_embeddings_list = [
                    emb.tolist() if hasattr(emb, "tolist") else list(emb)
                    for emb in batch_embeddings
                ]

            embeddings.extend(batch_embeddings_list)

        return embeddings
