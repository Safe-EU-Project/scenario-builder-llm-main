"""
Advanced reranking using cross-encoder models.
"""

from typing import Any, Dict, List

import structlog

try:
    from FlagEmbedding import FlagReranker

    FLAG_EMBEDDING_AVAILABLE = True
except ImportError:
    FLAG_EMBEDDING_AVAILABLE = False
    FlagReranker = None

try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None

from .models import RetrievalResult

log = structlog.get_logger()


class AdvancedReranker:
    """Advanced reranking using cross-encoder models for better relevance scoring"""

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        """
        Initialize advanced reranker

        Args:
            model_name: HuggingFace model name for cross-encoder reranking
        """
        if not FLAG_EMBEDDING_AVAILABLE:
            error_msg = (
                "FlagEmbedding is not available. Install with: pip install FlagEmbedding>=1.2.10"
            )
            log.error("advanced_reranker_unavailable", error=error_msg)
            raise ImportError(error_msg)

        try:
            self.model_name = model_name
            self.reranker = FlagReranker(model_name, use_fp16=True)

            # Check if CUDA is available
            self.device = "cuda" if TORCH_AVAILABLE and torch.cuda.is_available() else "cpu"
            log.info("advanced_reranker_initialized", model_name=model_name, device=self.device)
        except Exception as e:
            log.error("advanced_reranker_init_failed", model_name=model_name, error=str(e))
            raise

    def rerank(
        self, query: str, results: List[RetrievalResult], top_k: int = 20, initial_k: int = 150
    ) -> List[RetrievalResult]:
        """
        Advanced reranking using cross-encoder model

        Pipeline:
        1. Take initial retrieval results (up to initial_k)
        2. Use cross-encoder to score query-document pairs
        3. Return top_k results based on reranking scores

        Args:
            query: Original search query
            results: Initial retrieval results
            top_k: Final number of results to return (default: 20)
            initial_k: Number of initial results to rerank (default: 150)

        Returns:
            Reranked results limited to top_k
        """
        try:
            if not results:
                return []

            # Take top initial_k results for reranking
            candidates = results[:initial_k]

            if len(candidates) <= top_k:
                return candidates

            # Prepare query-document pairs for cross-encoder
            pairs = [(query, result.content) for result in candidates]

            # Get reranking scores from cross-encoder
            rerank_scores = self.reranker.compute_score(pairs)

            # Handle single result case (returns float instead of list)
            if not isinstance(rerank_scores, list):
                rerank_scores = [rerank_scores]

            # Create scored results with new ranking scores
            scored_results = []
            for result, rerank_score in zip(candidates, rerank_scores):
                scored_result = RetrievalResult(
                    content=result.content,
                    score=float(rerank_score),  # Use reranking score
                    source=result.source,
                    project_name=result.project_name,
                    document_name=result.document_name,
                    document_type=result.document_type,
                    chunk_id=result.chunk_id,
                    metadata={
                        **result.metadata,
                        "original_score": result.score,
                        "rerank_score": float(rerank_score),
                    },
                )
                scored_results.append(scored_result)

            # Sort by reranking score (higher is better)
            scored_results.sort(key=lambda x: x.score, reverse=True)

            # Return top_k results
            final_results = scored_results[:top_k]

            log.info(
                "advanced_reranking_completed",
                query_length=len(query),
                input_count=len(results),
                candidates_reranked=len(candidates),
                output_count=len(final_results),
                model=self.model_name,
            )

            return final_results

        except Exception as e:
            log.error(
                "advanced_reranking_error",
                query_length=len(query),
                results_count=len(results),
                model=self.model_name,
                error=str(e),
            )
            # Fallback to original results
            return results[:top_k] if results else []

    def batch_rerank(
        self,
        query: str,
        results_batches: List[List[RetrievalResult]],
        top_k: int = 20,
        initial_k: int = 150,
    ) -> List[RetrievalResult]:
        """
        Rerank multiple batches of results and merge them

        Args:
            query: Search query
            results_batches: List of result batches (e.g., from different retrieval methods)
            top_k: Final number of results
            initial_k: Number of results per batch to consider

        Returns:
            Merged and reranked results
        """
        try:
            # Flatten and deduplicate results by chunk_id
            seen_chunks = set()
            all_results = []

            for batch in results_batches:
                for result in batch[:initial_k]:  # Take initial_k from each batch
                    if result.chunk_id not in seen_chunks:
                        all_results.append(result)
                        seen_chunks.add(result.chunk_id)

            # Rerank combined results
            return self.rerank(query, all_results, top_k, len(all_results))

        except Exception as e:
            log.error("batch_reranking_error", error=str(e))
            # Fallback to first batch
            return results_batches[0][:top_k] if results_batches and results_batches[0] else []

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the reranking model

        Returns:
            Model information dictionary
        """
        return {
            "model_name": self.model_name,
            "model_type": "cross_encoder_reranker",
            "device": self.device,
            "provider": "FlagEmbedding",
        }
