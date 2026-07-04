"""
Vector storage and retrieval using Qdrant and SQLite.
"""

import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    SparseVectorParams,
    VectorParams,
)

from ..config.settings import settings

log = structlog.get_logger()


class VectorStore:
    """Self-contained vector storage using Qdrant and SQLite"""

    def __init__(self):
        """Initialize vector store with configuration"""
        try:
            # Get configuration from settings
            self.qdrant_host = settings.qdrant_host
            self.qdrant_port = settings.qdrant_port
            self.collection_name = settings.collection_name
            self.embedding_dim = settings.embedding_dim
            self.metadata_db_path = settings.metadata_db_path

            # Initialize Qdrant client
            self.qdrant_client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)

            # Create collection if it doesn't exist
            self._ensure_collection()

            # Initialize SQLite database
            self._ensure_metadata_db()

            log.info(
                "vector_store_initialized",
                qdrant_host=self.qdrant_host,
                qdrant_port=self.qdrant_port,
                collection_name=self.collection_name,
                embedding_dim=self.embedding_dim,
            )

        except Exception as e:
            log.error("vector_store_init_failed", error=str(e))
            raise

    def _ensure_collection(self):
        """Ensure Qdrant collection exists with correct configuration"""
        try:
            # Check if collection exists
            collections = self.qdrant_client.get_collections()
            collection_names = [col.name for col in collections.collections]

            if self.collection_name not in collection_names:
                # Create collection with dense vectors first
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config={
                        "dense": VectorParams(size=self.embedding_dim, distance=Distance.COSINE)
                    },
                    sparse_vectors_config={"sparse": SparseVectorParams()},
                )
                log.info("qdrant_collection_created", collection_name=self.collection_name)
            else:
                # Ensure both vector configs exist (add sparse if missing)
                info = self.qdrant_client.get_collection(self.collection_name)
                configured_sparse = getattr(getattr(info, "config", None), "params", None)
                has_sparse = False
                try:
                    # Newer clients expose sparse vector config at params.sparse_vectors
                    sparse_vectors = getattr(configured_sparse, "sparse_vectors", None)
                    has_sparse = isinstance(sparse_vectors, dict) and "sparse" in sparse_vectors
                except Exception:
                    has_sparse = False
                if not has_sparse:
                    try:
                        self.qdrant_client.update_collection(
                            collection_name=self.collection_name,
                            sparse_vectors={"sparse": SparseVectorParams()},
                        )
                        log.info(
                            "qdrant_collection_updated_add_sparse",
                            collection_name=self.collection_name,
                        )
                    except Exception as e:
                        log.warning("qdrant_add_sparse_failed", error=str(e))
                log.debug("qdrant_collection_exists", collection_name=self.collection_name)

        except Exception as e:
            log.error("qdrant_collection_setup_failed", error=str(e))
            raise

    def _ensure_metadata_db(self):
        """Ensure SQLite metadata database exists with correct schema"""
        try:
            import os

            os.makedirs(os.path.dirname(self.metadata_db_path), exist_ok=True)

            # Create tables if they don't exist
            with sqlite3.connect(self.metadata_db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS documents (
                        document_id TEXT PRIMARY KEY,
                        project_name TEXT,
                        document_name TEXT,
                        document_type TEXT,
                        created_at TEXT,
                        updated_at TEXT,
                        chunk_count INTEGER DEFAULT 0,
                        metadata TEXT
                    )
                """
                )

                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS document_chunks (
                        chunk_id TEXT PRIMARY KEY,
                        document_id TEXT,
                        chunk_index INTEGER,
                        content TEXT,
                        created_at TEXT,
                        metadata TEXT,
                        FOREIGN KEY (document_id) REFERENCES documents (document_id)
                    )
                """
                )

                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_documents_project 
                    ON documents (project_name)
                """
                )

                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_chunks_document 
                    ON document_chunks (document_id)
                """
                )

                conn.commit()

            log.debug("metadata_db_initialized", db_path=self.metadata_db_path)

        except Exception as e:
            log.error("metadata_db_setup_failed", error=str(e))
            raise

    def store_document_chunks(
        self,
        chunks: List[Any],
        embeddings: List[List[float]],
        sparse_embeddings: Optional[List[Any]] = None,
    ) -> bool:
        """
        Store document chunks and their embeddings

        Args:
            chunks: List of DocumentChunk objects
            embeddings: List of dense embedding vectors
            sparse_embeddings: Optional list of sparse embedding vectors

        Returns:
            Success status
        """
        try:
            if not chunks or not embeddings:
                log.warning("empty_chunks_or_embeddings")
                return False

            if len(chunks) != len(embeddings):
                log.error(
                    "chunks_embeddings_mismatch",
                    chunks_count=len(chunks),
                    embeddings_count=len(embeddings),
                )
                return False

            document_id = chunks[0].document_id
            project_name = chunks[0].project_name
            document_name = chunks[0].document_name
            document_type = chunks[0].document_type

            # Store document metadata
            self._store_document_metadata(
                document_id=document_id,
                project_name=project_name,
                document_name=document_name,
                document_type=document_type,
                chunk_count=len(chunks),
                metadata=chunks[0].metadata,
            )

            # Prepare points for Qdrant
            points = []
            chunk_metadata = []

            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                point_id = str(uuid.uuid4())

                # Build vector dictionary with dense embedding
                vector_dict = {"dense": embedding}

                # Add sparse embedding if provided
                if sparse_embeddings and i < len(sparse_embeddings):
                    vector_dict["sparse"] = sparse_embeddings[i]

                # Qdrant point
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=vector_dict,
                        payload={
                            "chunk_id": chunk.chunk_id,
                            "document_id": chunk.document_id,
                            "project_name": chunk.project_name,
                            "document_name": chunk.document_name,
                            "document_type": chunk.document_type,
                            "chunk_index": chunk.chunk_index,
                            "sector": getattr(chunk, "sector", "general"),
                        },
                    )
                )

                # SQLite chunk metadata
                chunk_metadata.append(
                    {
                        "chunk_id": chunk.chunk_id,
                        "document_id": chunk.document_id,
                        "chunk_index": chunk.chunk_index,
                        "content": chunk.content,
                        "metadata": str(chunk.metadata),
                    }
                )

            # Store vectors in Qdrant
            self.qdrant_client.upsert(collection_name=self.collection_name, points=points)

            # Store chunk metadata in SQLite
            self._store_chunk_metadata(chunk_metadata)

            log.info("document_chunks_stored", document_id=document_id, chunks_count=len(chunks))

            return True

        except Exception as e:
            log.error("store_document_chunks_error", error=str(e))
            return False

    def add_chunks(
        self,
        chunks: List[Any],
        embeddings: List[List[float]],
        sparse_embeddings: Optional[List[Any]] = None,
    ) -> bool:
        """
        Alias for store_document_chunks for compatibility

        Args:
            chunks: List of DocumentChunk objects
            embeddings: List of dense embedding vectors
            sparse_embeddings: Optional list of sparse embedding vectors

        Returns:
            Success status
        """
        return self.store_document_chunks(chunks, embeddings, sparse_embeddings)

    def search_documents(
        self,
        query_embedding: List[float],
        limit: int = 10,
        project_filter: Optional[str] = None,
        document_type_filter: Optional[str] = None,
        sector_filter: Optional[str] = None,
    ):
        """
        Search for similar documents using vector similarity

        Args:
            query_embedding: Query vector
            limit: Number of results to return
            project_filter: Filter by project name
            document_type_filter: Filter by document type

        Returns:
            List of search results
        """
        try:
            # Build filter conditions
            filter_conditions = []
            if project_filter:
                filter_conditions.append(
                    FieldCondition(key="project_name", match=MatchValue(value=project_filter))
                )
            if document_type_filter:
                filter_conditions.append(
                    FieldCondition(
                        key="document_type", match=MatchValue(value=document_type_filter)
                    )
                )
            if sector_filter and sector_filter != "general":
                filter_conditions.append(
                    FieldCondition(key="sector", match=MatchValue(value=sector_filter))
                )

            # Create filter if conditions exist
            search_filter = None
            if filter_conditions:
                search_filter = Filter(must=filter_conditions)

            # Search in Qdrant using the 'dense' vector
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=("dense", query_embedding),
                query_filter=search_filter,
                limit=limit,
                with_payload=True,
            )

            # Get chunk content from SQLite
            results = []
            for result in search_results:
                chunk_id = result.payload["chunk_id"]
                chunk_content = self._get_chunk_content(chunk_id)

                results.append(
                    {
                        "chunk_id": chunk_id,
                        "document_id": result.payload["document_id"],
                        "project_name": result.payload["project_name"],
                        "document_name": result.payload["document_name"],
                        "document_type": result.payload["document_type"],
                        "chunk_index": result.payload["chunk_index"],
                        "sector": result.payload.get("sector", "general"),
                        "content": chunk_content,
                        "score": result.score,
                    }
                )

            log.debug(
                "document_search_completed",
                query_dimension=len(query_embedding),
                results_count=len(results),
                project_filter=project_filter,
                document_type_filter=document_type_filter,
                sector_filter=sector_filter,
            )

            return results

        except Exception as e:
            log.error("document_search_error", query_dimension=len(query_embedding), error=str(e))
            return []

    def _scroll_points(self, batch_size: int = 256) -> Tuple[List[Any], Optional[str]]:
        """Scroll through points to retrieve ids and payloads in batches."""
        result = self.qdrant_client.scroll(
            collection_name=self.collection_name,
            with_payload=True,
            limit=batch_size,
        )
        return result[0], result[1]

    def backfill_sparse_vectors(self, sparse_service, batch_size: int = 128) -> int:
        """
        Generate and upsert sparse vectors for all existing points based on chunk content.
        Returns number of points updated.
        """
        try:
            total_updated = 0
            next_offset = None
            while True:
                points, next_offset = self.qdrant_client.scroll(
                    collection_name=self.collection_name,
                    with_payload=True,
                    limit=batch_size,
                    offset=next_offset,
                )
                if not points:
                    break
                # Prepare texts per point
                chunk_ids = [p.payload.get("chunk_id") for p in points]
                texts = [self._get_chunk_content(cid) for cid in chunk_ids]
                # Build sparse vectors
                sparse_vectors = sparse_service.embed_documents(texts)
                # Upsert only sparse named vector for each id
                upsert_points = []
                for p, sv in zip(points, sparse_vectors):
                    upsert_points.append(PointStruct(id=p.id, vector={"sparse": sv}))
                self.qdrant_client.upsert(
                    collection_name=self.collection_name,
                    points=upsert_points,
                )
                total_updated += len(upsert_points)
                if not next_offset:
                    break
            log.info("sparse_backfill_completed", updated=total_updated)
            return total_updated
        except Exception as e:
            log.error("sparse_backfill_failed", error=str(e))
            raise

    def delete_document(self, document_id: str) -> bool:
        """
        Delete document and all its chunks

        Args:
            document_id: Document identifier

        Returns:
            Success status
        """
        try:
            # Delete from Qdrant by filtering on document_id
            self.qdrant_client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
                ),
            )

            # Delete from SQLite
            with sqlite3.connect(self.metadata_db_path) as conn:
                conn.execute("DELETE FROM document_chunks WHERE document_id = ?", (document_id,))
                conn.execute("DELETE FROM documents WHERE document_id = ?", (document_id,))
                conn.commit()

            log.info("document_deleted", document_id=document_id)
            return True

        except Exception as e:
            log.error("delete_document_error", document_id=document_id, error=str(e))
            return False

    def get_document_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get document metadata by ID

        Args:
            document_id: Document identifier

        Returns:
            Document metadata or None if not found
        """
        try:
            with sqlite3.connect(self.metadata_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM documents WHERE document_id = ?", (document_id,)
                )
                row = cursor.fetchone()

                if row:
                    metadata = dict(row)
                    log.debug("document_metadata_retrieved", document_id=document_id)
                    return metadata
                else:
                    log.debug("document_metadata_not_found", document_id=document_id)
                    return None

        except Exception as e:
            log.error("get_document_metadata_error", document_id=document_id, error=str(e))
            return None

    def get_documents_by_project(self, project_name: str) -> List[Dict[str, Any]]:
        """
        Get all documents for a project

        Args:
            project_name: Project name

        Returns:
            List of document metadata
        """
        try:
            with sqlite3.connect(self.metadata_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM documents WHERE project_name = ?", (project_name,)
                )
                rows = cursor.fetchall()

                documents = [dict(row) for row in rows]

            log.debug(
                "project_documents_retrieved",
                project_name=project_name,
                document_count=len(documents),
            )

            return documents

        except Exception as e:
            log.error("get_documents_by_project_error", project_name=project_name, error=str(e))
            return []

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            # Get SQLite metadata stats
            with sqlite3.connect(self.metadata_db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM documents")
                total_documents = cursor.fetchone()[0]

                cursor = conn.execute("SELECT COUNT(*) FROM document_chunks")
                total_chunks = cursor.fetchone()[0]

                cursor = conn.execute("SELECT COUNT(DISTINCT project_name) FROM documents")
                total_projects = cursor.fetchone()[0]

            # Get Qdrant stats
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            vector_count = collection_info.points_count

            stats = {
                "metadata": {
                    "total_documents": total_documents,
                    "total_chunks": total_chunks,
                    "total_projects": total_projects,
                },
                "vector": {
                    "total_points": vector_count,
                    "vector_size": self.embedding_dim,
                    "status": collection_info.status,
                },
            }

            log.debug("storage_stats_retrieved")

            return stats

        except Exception as e:
            log.error("get_storage_stats_error", error=str(e))
            return {"error": str(e)}

    def _store_document_metadata(
        self,
        document_id: str,
        project_name: str,
        document_name: str,
        document_type: str,
        chunk_count: int,
        metadata: Dict[str, Any],
    ):
        """Store document metadata in SQLite"""
        now = datetime.now().isoformat()

        with sqlite3.connect(self.metadata_db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO documents 
                (document_id, project_name, document_name, document_type, 
                 created_at, updated_at, chunk_count, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    document_id,
                    project_name,
                    document_name,
                    document_type,
                    now,
                    now,
                    chunk_count,
                    str(metadata),
                ),
            )
            conn.commit()

    def _store_chunk_metadata(self, chunk_metadata: List[Dict[str, Any]]):
        """Store chunk metadata in SQLite"""
        now = datetime.now().isoformat()

        with sqlite3.connect(self.metadata_db_path) as conn:
            for chunk in chunk_metadata:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO document_chunks
                    (chunk_id, document_id, chunk_index, content, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        chunk["chunk_id"],
                        chunk["document_id"],
                        chunk["chunk_index"],
                        chunk["content"],
                        now,
                        chunk["metadata"],
                    ),
                )
            conn.commit()

    def _get_chunk_content(self, chunk_id: str) -> str:
        """Get chunk content from SQLite"""
        try:
            with sqlite3.connect(self.metadata_db_path) as conn:
                cursor = conn.execute(
                    "SELECT content FROM document_chunks WHERE chunk_id = ?", (chunk_id,)
                )
                row = cursor.fetchone()
                return row[0] if row else ""
        except Exception:
            return ""

    def get_document_content(self, document_id: str) -> Optional[str]:
        """
        Get complete document content by concatenating all chunks in order

        Args:
            document_id: Document identifier

        Returns:
            Full document content (all chunks concatenated) or None if not found
        """
        try:
            with sqlite3.connect(self.metadata_db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT content FROM document_chunks
                    WHERE document_id = ?
                    ORDER BY chunk_index ASC
                    """,
                    (document_id,),
                )
                rows = cursor.fetchall()

                if not rows:
                    log.debug("document_not_found", document_id=document_id)
                    return None

                # Concatenate all chunks with newline separator
                content = "\n\n".join([row[0] for row in rows])

                log.info(
                    "document_content_retrieved",
                    document_id=document_id,
                    chunk_count=len(rows),
                    total_length=len(content),
                )

                return content

        except Exception as e:
            log.error("get_document_content_error", document_id=document_id, error=str(e))
            return None
