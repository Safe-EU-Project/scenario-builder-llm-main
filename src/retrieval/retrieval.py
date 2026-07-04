"""
Document retrieval and reranking system.
"""

import time
from typing import Any, Dict, List, Optional

import structlog
from qdrant_client.http.models import (
    FieldCondition,
    Filter,
    Fusion,
    FusionQuery,
    MatchValue,
    Prefetch,
    SparseVector,
)

from ..config.settings import settings
from ..embeddings.embeddings import EmbeddingService
from ..embeddings.sparse_embeddings import SparseEmbeddingService
from ..storage.vector_store import VectorStore
from .advanced_reranker import AdvancedReranker
from .models import RetrievalResult

log = structlog.get_logger()


class DocumentRetriever:
    """Document retrieval system with vector search and reranking"""

    def __init__(self, embedding_service: EmbeddingService, vector_store: VectorStore):
        """
        Initialize retriever

        Args:
            embedding_service: Embedding service instance
            vector_store: Vector store instance
        """
        self.embedding_service = embedding_service
        self.vector_store = vector_store

        log.info("retrieval_system_initialized")

    def retrieve(
        self,
        query: str,
        top_k: int = None,
        project_filter: Optional[str] = None,
        document_type_filter: Optional[str] = None,
        sector_filter: Optional[str] = None,
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant documents using vector search

        Args:
            query: Search query
            top_k: Number of results to return
            project_filter: Filter by project name
            document_type_filter: Filter by document type

        Returns:
            List of retrieval results
        """
        try:
            if top_k is None:
                top_k = settings.default_top_k

            # Validate top_k
            top_k = min(top_k, settings.max_top_k)

            start_time = time.time()

            # Generate query embedding
            query_embedding = self.embedding_service.embed_query(query)

            # Vector search
            search_results = self.vector_store.search_documents(
                query_embedding=query_embedding,
                limit=top_k * 2,  # Get more for potential reranking
                project_filter=project_filter,
                document_type_filter=document_type_filter,
                sector_filter=sector_filter,
            )

            # Convert to RetrievalResult format
            retrieval_results = []
            for result in search_results:
                retrieval_result = RetrievalResult(
                    content=result["content"],
                    score=result["score"],
                    source=f"{result['project_name']}/{result['document_name']}",
                    project_name=result["project_name"],
                    document_name=result["document_name"],
                    document_type=result["document_type"],
                    chunk_id=result["chunk_id"],
                    metadata={
                        "chunk_index": result["chunk_index"],
                        "document_id": result["document_id"],
                    },
                )
                retrieval_results.append(retrieval_result)

            # Return top_k results
            final_results = retrieval_results[:top_k]

            retrieval_time = time.time() - start_time

            log.info(
                "documents_retrieved",
                query_length=len(query),
                results_count=len(final_results),
                retrieval_time=retrieval_time,
                project_filter=project_filter,
                document_type_filter=document_type_filter,
                sector_filter=sector_filter,
            )

            return final_results

        except Exception as e:
            log.error("document_retrieval_error", query_length=len(query), error=str(e))
            return []


class DocumentReranker:
    """Simple reranking system for improving retrieval relevance"""

    def __init__(self):
        """Initialize reranker"""
        log.info("document_reranker_initialized")

    def rerank(
        self, query: str, results: List[RetrievalResult], top_k: int = None
    ) -> List[RetrievalResult]:
        """
        Rerank results based on query relevance

        Args:
            query: Original query
            results: Retrieved results to rerank
            top_k: Number of results to return

        Returns:
            Reranked results
        """
        try:
            if top_k is None:
                top_k = settings.default_top_k

            if len(results) <= top_k:
                return results

            # Simple keyword overlap reranking
            query_terms = set(query.lower().split())

            scored_results = []
            for result in results:
                content_terms = set(result.content.lower().split())
                overlap = len(query_terms.intersection(content_terms))

                # Combine vector score with keyword overlap
                keyword_score = overlap / len(query_terms) if query_terms else 0
                combined_score = result.score * 0.8 + keyword_score * 0.2

                scored_result = RetrievalResult(
                    content=result.content,
                    score=combined_score,
                    source=result.source,
                    project_name=result.project_name,
                    document_name=result.document_name,
                    document_type=result.document_type,
                    chunk_id=result.chunk_id,
                    metadata=result.metadata,
                )
                scored_results.append(scored_result)

            # Sort by combined score
            scored_results.sort(key=lambda x: x.score, reverse=True)

            final_results = scored_results[:top_k]

            log.debug(
                "documents_reranked",
                input_count=len(results),
                output_count=len(final_results),
                query_terms=len(query_terms),
            )

            return final_results

        except Exception as e:
            log.error(
                "document_reranking_error",
                query_length=len(query),
                results_count=len(results),
                error=str(e),
            )
            return results[:top_k] if results else []


class RetrievalSystem:
    """Complete retrieval system combining search and reranking"""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
        sparse_embedding_service: Optional[SparseEmbeddingService] = None,
        use_advanced_reranker: bool = True,
    ):
        """
        Initialize retrieval system

        Args:
            embedding_service: Dense embedding service instance
            vector_store: Vector store instance
            sparse_embedding_service: Optional sparse embedding service for hybrid search
            use_advanced_reranker: Whether to use advanced cross-encoder reranker
        """
        self.retriever = DocumentRetriever(embedding_service, vector_store)
        self.reranker = DocumentReranker()  # Keep simple reranker as fallback

        # Initialize advanced reranker if requested
        self.advanced_reranker = None
        if use_advanced_reranker:
            try:
                self.advanced_reranker = AdvancedReranker()
                log.info("advanced_reranker_initialized")
            except Exception as e:
                log.warning("advanced_reranker_init_failed", error=str(e))

        self.embedding_service = embedding_service
        self.sparse_embedding_service = sparse_embedding_service
        self.vector_store = vector_store

        log.info(
            "retrieval_system_initialized",
            hybrid_enabled=sparse_embedding_service is not None,
            advanced_reranker_enabled=self.advanced_reranker is not None,
        )

    def _hybrid_search(
        self,
        query: str,
        top_k: int,
        project_filter: Optional[str] = None,
        document_type_filter: Optional[str] = None,
        sector_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search using both dense and sparse vectors

        Args:
            query: Search query
            top_k: Number of results to return
            project_filter: Filter by project name
            document_type_filter: Filter by document type

        Returns:
            List of search results
        """
        try:
            # Generate dense embedding
            dense_vector = self.embedding_service.embed_query(query)

            # Generate sparse embedding
            sparse_vector = self.sparse_embedding_service.embed_query(query)

            # Build filter conditions
            must_conditions = []
            if project_filter:
                must_conditions.append(
                    FieldCondition(key="project_name", match=MatchValue(value=project_filter))
                )
            if document_type_filter:
                must_conditions.append(
                    FieldCondition(
                        key="document_type", match=MatchValue(value=document_type_filter)
                    )
                )
            if sector_filter and sector_filter != "general":
                must_conditions.append(
                    FieldCondition(key="sector", match=MatchValue(value=sector_filter))
                )

            filter_condition = None
            if must_conditions:
                filter_condition = Filter(must=must_conditions)

            # Perform hybrid search using Qdrant Prefetch + FusionQuery (RRF)
            prefetch = [
                Prefetch(
                    query=SparseVector(indices=sparse_vector.indices, values=sparse_vector.values),
                    using="sparse",
                    limit=top_k * 4,
                    filter=filter_condition,
                ),
                Prefetch(
                    query=dense_vector,
                    using="dense",
                    limit=top_k * 4,
                    filter=filter_condition,
                ),
            ]

            search_results = self.vector_store.qdrant_client.query_points(
                collection_name=self.vector_store.collection_name,
                prefetch=prefetch,
                query=FusionQuery(fusion=Fusion.RRF),
                query_filter=filter_condition,
                limit=top_k,
                with_payload=True,
            )

            # Convert results to our format
            results = []
            for point in search_results.points:
                # Get content from SQLite using chunk_id
                chunk_id = point.payload.get("chunk_id")
                content = self._get_chunk_content(chunk_id)

                result = {
                    "content": content,
                    "score": point.score,
                    "source": f"{point.payload.get('project_name', 'unknown')}/{point.payload.get('document_name', 'unknown')}",
                    "project_name": point.payload.get("project_name"),
                    "document_name": point.payload.get("document_name"),
                    "document_type": point.payload.get("document_type"),
                    "chunk_id": chunk_id,
                    "metadata": {
                        "chunk_index": point.payload.get("chunk_index"),
                        "document_id": point.payload.get("document_id"),
                    },
                }
                results.append(result)

            return results

        except Exception as e:
            log.error("hybrid_search_error", error=str(e))
            return []

    def _get_chunk_content(self, chunk_id: str) -> str:
        """Get chunk content from SQLite metadata database"""
        try:
            import sqlite3

            with sqlite3.connect(self.vector_store.metadata_db_path) as conn:
                cursor = conn.execute(
                    "SELECT content FROM document_chunks WHERE chunk_id = ?", (chunk_id,)
                )
                result = cursor.fetchone()
                return result[0] if result else ""
        except Exception as e:
            log.error("get_chunk_content_error", chunk_id=chunk_id, error=str(e))
            return ""

    def search(
        self,
        query: str,
        top_k: int = None,
        project_filter: Optional[str] = None,
        document_type_filter: Optional[str] = None,
        sector_filter: Optional[str] = None,
        use_reranking: bool = True,
        use_hybrid: bool = False,
        initial_k: int = 150,
        use_advanced_reranker: bool = True,
    ) -> Dict[str, Any]:
        """
        Search for documents with advanced reranking pipeline

        Pipeline:
        1. Retrieve top initial_k potentially relevant chunks (default: 150)
        2. Apply advanced cross-encoder reranking if available
        3. Return top_k chunks (default: 20) based on relevance scores

        Args:
            query: Search query
            top_k: Final number of results to return (default: 20)
            project_filter: Filter by project name
            document_type_filter: Filter by document type
            use_reranking: Whether to apply reranking
            use_hybrid: Whether to use hybrid search (dense + sparse)
            initial_k: Number of initial results to retrieve for reranking (default: 150)
            use_advanced_reranker: Whether to use cross-encoder reranker (default: True)

        Returns:
            Search results with metadata
        """
        try:
            if top_k is None:
                top_k = settings.default_top_k

            start_time = time.time()

            # Step 1: Retrieve initial_k candidates
            if use_hybrid and self.sparse_embedding_service:
                # Use hybrid search to get initial candidates
                initial_results = self._hybrid_search(
                    query=query,
                    top_k=initial_k,
                    project_filter=project_filter,
                    document_type_filter=document_type_filter,
                    sector_filter=sector_filter,
                )
                # Convert to RetrievalResult objects for reranking
                retrieved_docs = []
                for result in initial_results:
                    retrieved_docs.append(
                        RetrievalResult(
                            content=result["content"],
                            score=result["score"],
                            source=result["source"],
                            project_name=result["project_name"],
                            document_name=result["document_name"],
                            document_type=result["document_type"],
                            chunk_id=result["chunk_id"],
                            metadata=result["metadata"],
                        )
                    )
            else:
                # Use traditional dense vector search for initial retrieval
                retrieved_docs = self.retriever.retrieve(
                    query=query,
                    top_k=initial_k,
                    project_filter=project_filter,
                    document_type_filter=document_type_filter,
                    sector_filter=sector_filter,
                )

            # Step 2: Apply reranking if requested
            if use_reranking and retrieved_docs:
                if use_advanced_reranker and self.advanced_reranker:
                    # Use advanced cross-encoder reranker (150→20 pipeline)
                    final_docs = self.advanced_reranker.rerank(
                        query=query,
                        results=retrieved_docs,
                        top_k=top_k,
                        initial_k=min(len(retrieved_docs), initial_k),
                    )
                else:
                    # Fallback to simple reranker
                    final_docs = self.reranker.rerank(query, retrieved_docs, top_k)
            else:
                # No reranking, just take top_k
                final_docs = retrieved_docs[:top_k]

            # Step 3: Convert to serializable format
            results = []
            for doc in final_docs:
                results.append(
                    {
                        "content": doc.content,
                        "score": doc.score,
                        "source": doc.source,
                        "project_name": doc.project_name,
                        "document_name": doc.document_name,
                        "document_type": doc.document_type,
                        "chunk_id": doc.chunk_id,
                        "metadata": doc.metadata,
                    }
                )

            total_time = time.time() - start_time

            response = {
                "query": query,
                "results": results,
                "total_time": total_time,
                "metadata": {
                    "initial_retrieval_count": len(retrieved_docs),
                    "final_count": len(results),
                    "project_filter": project_filter,
                    "document_type_filter": document_type_filter,
                    "sector_filter": sector_filter,
                    "reranking_applied": use_reranking,
                    "advanced_reranker_used": use_reranking
                    and use_advanced_reranker
                    and self.advanced_reranker is not None,
                    "hybrid_search_used": use_hybrid and self.sparse_embedding_service is not None,
                    "initial_k": initial_k,
                    "target_k": top_k,
                },
            }

            log.info(
                "search_completed",
                query_length=len(query),
                initial_retrieval_count=len(retrieved_docs),
                final_results_count=len(results),
                total_time=total_time,
                reranking_applied=use_reranking,
                advanced_reranker_used=use_reranking
                and use_advanced_reranker
                and self.advanced_reranker is not None,
                hybrid_search_used=use_hybrid and self.sparse_embedding_service is not None,
                pipeline=f"{initial_k}→{top_k}",
            )

            return response

        except Exception as e:
            log.error("search_error", query_length=len(query), error=str(e))

            return {
                "query": query,
                "results": [],
                "total_time": 0.0,
                "metadata": {
                    "error": str(e),
                    "retrieved_count": 0,
                    "final_count": 0,
                    "project_filter": project_filter,
                    "document_type_filter": document_type_filter,
                    "sector_filter": sector_filter,
                    "reranking_applied": use_reranking,
                },
            }
