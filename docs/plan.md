# Refactoring Plan: Remove SQLite and Store Chunks in Qdrant

**Status**: Planning
**Date Created**: 2025-10-23
**Objective**: Simplify architecture by eliminating SQLite and storing all chunk data (including content) directly in Qdrant payloads.

---

## Table of Contents
1. [Current Architecture](#current-architecture)
2. [Motivation](#motivation)
3. [Proposed Architecture](#proposed-architecture)
4. [Detailed Changes](#detailed-changes)
5. [Implementation Steps](#implementation-steps)
6. [Migration Strategy](#migration-strategy)
7. [Testing Plan](#testing-plan)
8. [Benefits & Trade-offs](#benefits--trade-offs)

---

## Current Architecture

### Storage System (Dual Storage)

**Qdrant** (Vector Database):
- Stores dense embeddings (384-dim vectors)
- Stores sparse embeddings (BM25-based)
- Stores minimal payload metadata:
  - `chunk_id`: Unique identifier
  - `document_id`: Parent document ID
  - `project_name`: Project/folder organization
  - `document_name`: Original file name
  - `document_type`: File extension
  - `chunk_index`: Position in document

**SQLite** (Metadata Database):
- `documents` table: Document-level metadata
  - `document_id` (PK)
  - `project_name`
  - `document_name`
  - `document_type`
  - `created_at`, `updated_at`
  - `chunk_count`
  - `metadata` (JSON string)

- `document_chunks` table: **Chunk content storage**
  - `chunk_id` (PK)
  - `document_id` (FK)
  - `chunk_index`
  - **`content`** (the actual text - this is what we want in Qdrant)
  - `created_at`
  - `metadata` (JSON string)

### Current Data Flow

```
Document → Chunking → Embeddings → Dual Write:
                                    ├─ Qdrant: vectors + minimal payload
                                    └─ SQLite: content + metadata

Query → Qdrant (vector search) → Get chunk_ids → SQLite lookup for content → Return results
```

### Problems with Current Approach

1. **Complexity**: Two storage systems to maintain
2. **Consistency**: Must keep Qdrant and SQLite in sync
3. **Lookups**: Requires secondary SQLite query to get chunk content
4. **Dependencies**: Additional aiosqlite dependency
5. **Deployment**: Must manage SQLite file alongside Qdrant
6. **Performance**: Extra I/O for content retrieval

---

## Motivation

### Why Remove SQLite?

1. **Simplification**: Single source of truth (Qdrant)
2. **Performance**: Eliminate extra database lookup
3. **Consistency**: No sync issues between stores
4. **Deployment**: One less component to manage
5. **Atomic Operations**: All data in one transactional system
6. **Qdrant Capability**: Qdrant payloads can store arbitrary JSON data

### Qdrant Payload Capabilities

Qdrant points support rich payloads with nested JSON structures:
- Strings (unlimited length for text content)
- Numbers, booleans
- Nested objects and arrays
- Indexed fields for filtering

**Perfect for storing chunk content alongside metadata!**

---

## Proposed Architecture

### Single Storage (Qdrant Only)

**Qdrant** (Vector + Metadata Database):
- Stores dense embeddings (384-dim vectors)
- Stores sparse embeddings (BM25-based)
- **NEW**: Stores complete payload including content:
  - `chunk_id`: Unique identifier
  - `document_id`: Parent document ID
  - `project_name`: Project organization
  - `document_name`: Original file name
  - `document_type`: File extension
  - `chunk_index`: Position in document
  - **`content`**: The actual chunk text (NEW!)
  - `metadata`: Additional metadata (JSON object)
  - `created_at`: Timestamp
  - `document_metadata`: Document-level info (NEW!)

### New Data Flow

```
Document → Chunking → Embeddings → Single Write:
                                    └─ Qdrant: vectors + complete payload (including content)

Query → Qdrant (vector search) → Return results with content → Done! (no second lookup)
```

---

## Detailed Changes

### 1. File: `src/storage/vector_store.py`

#### Changes Summary
- Remove all SQLite imports and code
- Store content in Qdrant payload
- Retrieve content from Qdrant payload
- Implement document-level operations using Qdrant scroll

#### Specific Modifications

**Remove Imports:**
```python
# DELETE these imports:
import sqlite3
import aiosqlite
import asyncio
```

**Update `__init__()` method:**
```python
def __init__(self):
    # ... existing code ...

    # DELETE this line:
    # self.metadata_db_path = settings.metadata_db_path

    # ... existing Qdrant setup ...

    # DELETE this line:
    # self._ensure_metadata_db()
```

**DELETE entire method:**
- `_ensure_metadata_db()` (lines 107-156)

**Update `store_document_chunks()` method:**
```python
# In the payload building section (around line 217), ADD content:
points.append(PointStruct(
    id=point_id,
    vector=vector_dict,
    payload={
        "chunk_id": chunk.chunk_id,
        "document_id": chunk.document_id,
        "project_name": chunk.project_name,
        "document_name": chunk.document_name,
        "document_type": chunk.document_type,
        "chunk_index": chunk.chunk_index,
        "content": chunk.content,  # NEW: Store content here!
        "metadata": chunk.metadata,  # Store as object, not string
        "created_at": datetime.now().isoformat()
    }
))

# DELETE the chunk_metadata list building (lines 227-234)
# DELETE the SQLite storage calls:
# - self._store_document_metadata(...)
# - self._store_chunk_metadata(chunk_metadata)
```

**Simplify `search_documents()` method:**
```python
# Around line 318-319, REPLACE:
# chunk_content = self._get_chunk_content(chunk_id)

# WITH:
# Content is now in the payload!
results.append({
    "chunk_id": chunk_id,
    "document_id": result.payload["document_id"],
    "project_name": result.payload["project_name"],
    "document_name": result.payload["document_name"],
    "document_type": result.payload["document_type"],
    "chunk_index": result.payload["chunk_index"],
    "content": result.payload.get("content", ""),  # Get from payload
    "score": result.score
})
```

**Update `backfill_sparse_vectors()` method:**
```python
# Around line 374, REPLACE:
# texts = [self._get_chunk_content(cid) for cid in chunk_ids]

# WITH:
# Get content from payload
texts = [p.payload.get("content", "") for p in points]
```

**Simplify `delete_document()` method:**
```python
def delete_document(self, document_id: str) -> bool:
    """Delete document and all its chunks"""
    try:
        # Only delete from Qdrant
        self.qdrant_client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
            )
        )

        log.info("document_deleted", document_id=document_id)
        return True

    except Exception as e:
        log.error("delete_document_error",
                 document_id=document_id,
                 error=str(e))
        return False
```

**Replace `get_document_metadata()` method:**
```python
def get_document_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
    """Get document metadata by ID using Qdrant scroll"""
    try:
        # Scroll to find any chunk with this document_id
        result = self.qdrant_client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
            ),
            limit=1,
            with_payload=True
        )

        points, _ = result
        if points:
            payload = points[0].payload
            return {
                "document_id": document_id,
                "project_name": payload.get("project_name"),
                "document_name": payload.get("document_name"),
                "document_type": payload.get("document_type"),
                "created_at": payload.get("created_at")
            }
        return None

    except Exception as e:
        log.error("get_document_metadata_error", document_id=document_id, error=str(e))
        return None
```

**Replace `get_documents_by_project()` method:**
```python
def get_documents_by_project(self, project_name: str) -> List[Dict[str, Any]]:
    """Get all documents for a project using Qdrant scroll"""
    try:
        documents = {}
        offset = None

        while True:
            result = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[FieldCondition(key="project_name", match=MatchValue(value=project_name))]
                ),
                limit=100,
                offset=offset,
                with_payload=True
            )

            points, offset = result

            for point in points:
                doc_id = point.payload.get("document_id")
                if doc_id not in documents:
                    documents[doc_id] = {
                        "document_id": doc_id,
                        "project_name": point.payload.get("project_name"),
                        "document_name": point.payload.get("document_name"),
                        "document_type": point.payload.get("document_type"),
                        "created_at": point.payload.get("created_at")
                    }

            if not offset:
                break

        return list(documents.values())

    except Exception as e:
        log.error("get_documents_by_project_error", project_name=project_name, error=str(e))
        return []
```

**Update `get_storage_stats()` method:**
```python
def get_storage_stats(self) -> Dict[str, Any]:
    """Get storage statistics from Qdrant only"""
    try:
        # Get Qdrant stats
        collection_info = self.qdrant_client.get_collection(self.collection_name)
        vector_count = collection_info.points_count

        # Count unique documents and projects by scrolling
        documents = set()
        projects = set()
        offset = None

        while True:
            result = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                limit=100,
                offset=offset,
                with_payload=["document_id", "project_name"]
            )

            points, offset = result

            for point in points:
                documents.add(point.payload.get("document_id"))
                projects.add(point.payload.get("project_name"))

            if not offset:
                break

        stats = {
            "total_documents": len(documents),
            "total_chunks": vector_count,
            "total_projects": len(projects),
            "vector_size": self.embedding_dim,
            "status": collection_info.status
        }

        log.debug("storage_stats_retrieved")
        return stats

    except Exception as e:
        log.error("get_storage_stats_error", error=str(e))
        return {"error": str(e)}
```

**DELETE these methods entirely:**
- `_store_document_metadata()` (lines 533-547)
- `_store_chunk_metadata()` (lines 549-561)
- `_get_chunk_content()` (lines 563-574)

**Update class docstring:**
```python
class VectorStore:
    """Vector storage using Qdrant with complete chunk data in payloads"""
```

---

### 2. File: `src/retrieval/retrieval.py`

#### Changes Summary
- Update `_get_chunk_content()` to read from Qdrant instead of SQLite

#### Specific Modifications

**Replace `_get_chunk_content()` method (lines 322-335):**
```python
def _get_chunk_content(self, chunk_id: str) -> str:
    """Get chunk content from Qdrant payload"""
    try:
        # Scroll to find the point with this chunk_id
        result = self.vector_store.qdrant_client.scroll(
            collection_name=self.vector_store.collection_name,
            scroll_filter=Filter(
                must=[FieldCondition(key="chunk_id", match=MatchValue(value=chunk_id))]
            ),
            limit=1,
            with_payload=True
        )

        points, _ = result
        if points:
            return points[0].payload.get("content", "")
        return ""

    except Exception as e:
        log.error("get_chunk_content_error", chunk_id=chunk_id, error=str(e))
        return ""
```

**Note**: The hybrid search method `_hybrid_search()` already calls `_get_chunk_content()`, so it will automatically use the new implementation.

---

### 3. File: `src/config/settings.py`

#### Changes Summary
- Remove `metadata_db_path` configuration

#### Specific Modifications

**DELETE line 64:**
```python
# DELETE this line:
metadata_db_path: Path = _env_path("METADATA_DB_PATH", "./data/scenario_metadata.db")
```

**Update `get_storage_config()` method (lines 98-106):**
```python
def get_storage_config(self) -> Dict[str, Any]:
    """Get storage configuration as dictionary"""
    return {
        # DELETE this line:
        # "metadata_db_path": str(self.metadata_db_path),
        "qdrant_host": self.qdrant_host,
        "qdrant_port": self.qdrant_port,
        "collection_name": self.collection_name,
        "embedding_dim": self.embedding_dim
    }
```

---

### 4. File: `requirements.txt`

#### Changes Summary
- Remove aiosqlite dependency (sqlite3 is part of Python standard library)

#### Specific Modifications

**DELETE line 5:**
```
aiosqlite==0.19.0; python_version >= "3.7"
```

**Note**: `sqlite3` is part of the Python standard library, so no action needed there.

---

### 5. Documentation Updates

#### File: `README.md`

**Update Architecture Section (around line 27):**
```markdown
├── storage/          # Vector store (Qdrant only - no SQLite)
```

**Update RAG Pipeline Details (around line 398):**
```markdown
4. **Storage**: Store in Qdrant vector DB (vectors + content in payload)
```

**Update line mentioning dual storage** to clarify it's now single storage.

#### File: `docs/ARCHITECTURE.md` (if exists)

Update architecture diagrams and descriptions to reflect:
- Single storage system (Qdrant only)
- Content stored in Qdrant payload
- Simplified data flow

#### File: `docs/DOCKER.md` (if exists)

Remove any references to SQLite database files or backups.

---

## Implementation Steps

### Step 1: Backup Existing Data (if needed)
```bash
# Backup SQLite database
cp data/scenario_metadata.db data/scenario_metadata.db.backup

# Export Qdrant collection (optional)
# Use Qdrant snapshot API if you want to preserve existing vectors
```

### Step 2: Update Code Files

1. **Update `src/storage/vector_store.py`**
   - Follow all changes outlined in section 1 above
   - Test each method as you modify it

2. **Update `src/retrieval/retrieval.py`**
   - Replace `_get_chunk_content()` method
   - Test retrieval functionality

3. **Update `src/config/settings.py`**
   - Remove `metadata_db_path` configuration
   - Update config methods

4. **Update `requirements.txt`**
   - Remove aiosqlite dependency

### Step 3: Recreate Qdrant Collection

**Option A: Delete and recreate**
```python
# In Python shell or script:
from qdrant_client import QdrantClient

client = QdrantClient(host="localhost", port=6333)
client.delete_collection("scenarios")  # Your collection name
# Collection will be recreated on next startup
```

**Option B: Update via settings**
- Set `force_reprocess=true` when calling `/api/v1/process`

### Step 4: Reprocess Documents

```bash
# Call the process endpoint to repopulate with new payload structure
curl -X POST "http://localhost:8002/api/v1/process" \
  -H "Content-Type: application/json" \
  -d '{"force_reprocess": true}'
```

### Step 5: Update Dependencies

```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or specifically remove aiosqlite
pip uninstall aiosqlite
```

### Step 6: Test All Endpoints

1. Health check: `GET /health`
2. Process documents: `POST /api/v1/process`
3. Query: `POST /api/v1/query`
4. Structured query: `POST /api/v1/query_structured`
5. Ingest scenario: `POST /api/v1/ingest_scenario`

---

## Migration Strategy

### For New Deployments
- Simply deploy with updated code
- No migration needed

### For Existing Deployments

#### Option 1: Fresh Start (Recommended)
1. Back up important data if needed
2. Deploy updated code
3. Delete Qdrant collection (or create new one)
4. Reprocess all documents
5. Delete old SQLite database file

**Pros**: Clean, simple, guaranteed consistency
**Cons**: Requires reprocessing

#### Option 2: Data Migration Script
Create a migration script that:
1. Reads all chunks from SQLite
2. Updates corresponding Qdrant points with content
3. Validates migration
4. Deletes SQLite database

**Migration Script Skeleton:**
```python
import sqlite3
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

def migrate_sqlite_to_qdrant():
    # Connect to both
    db = sqlite3.connect("data/scenario_metadata.db")
    qdrant = QdrantClient(host="localhost", port=6333)

    # Get all chunks from SQLite
    cursor = db.execute("SELECT chunk_id, content FROM document_chunks")

    for chunk_id, content in cursor:
        # Find point in Qdrant
        result = qdrant.scroll(
            collection_name="scenarios",
            scroll_filter=Filter(must=[
                FieldCondition(key="chunk_id", match=MatchValue(value=chunk_id))
            ]),
            limit=1
        )

        points, _ = result
        if points:
            point_id = points[0].id
            payload = points[0].payload

            # Update payload with content
            payload["content"] = content

            qdrant.set_payload(
                collection_name="scenarios",
                payload=payload,
                points=[point_id]
            )

    print("Migration complete!")
```

**Pros**: Preserves existing data
**Cons**: More complex, risk of errors

---

## Testing Plan

### Unit Tests

Create/update tests for:

1. **Vector Store Tests** (`tests/test_vector_store.py`):
   ```python
   def test_store_chunks_with_content():
       # Verify content is stored in Qdrant payload

   def test_search_returns_content():
       # Verify search results include content

   def test_get_chunk_content():
       # Verify content retrieval from Qdrant

   def test_delete_document():
       # Verify document deletion (no SQLite)
   ```

2. **Retrieval Tests** (`tests/test_retrieval.py`):
   ```python
   def test_hybrid_search_with_content():
       # Verify hybrid search returns content

   def test_get_chunk_content_from_qdrant():
       # Verify content retrieval in retrieval system
   ```

### Integration Tests

1. **End-to-End Processing**:
   - Process a document
   - Verify all chunks stored with content in Qdrant
   - No SQLite database created

2. **Search Flow**:
   - Query documents
   - Verify results contain full content
   - No SQLite lookups performed

3. **Performance**:
   - Benchmark search latency (should be faster!)
   - Compare before/after performance

### Manual Testing Checklist

- [ ] Start service fresh (no SQLite file created)
- [ ] Upload and process documents
- [ ] Verify Qdrant payloads contain content
- [ ] Test query endpoint returns correct content
- [ ] Test structured query endpoint
- [ ] Test scenario ingestion
- [ ] Test document deletion
- [ ] Check storage stats endpoint
- [ ] Verify hybrid search works
- [ ] Test reranking pipeline

---

## Benefits & Trade-offs

### Benefits

✅ **Simplified Architecture**
- Single storage system (Qdrant only)
- Easier to understand and maintain

✅ **Better Performance**
- No secondary SQLite lookup
- Faster content retrieval
- Single I/O operation

✅ **Improved Consistency**
- Single source of truth
- No sync issues between stores
- Atomic operations

✅ **Reduced Dependencies**
- Remove aiosqlite
- Fewer packages to manage

✅ **Easier Deployment**
- One storage component
- No SQLite file management
- Simpler backup/restore

✅ **Better Developer Experience**
- Less context switching
- Clearer code flow
- Easier debugging

### Trade-offs

⚠️ **Qdrant Payload Size**
- Qdrant payloads can be large
- Monitor storage usage
- Mitigation: Qdrant is designed for this

⚠️ **Migration Required**
- Existing deployments need data migration or reprocessing
- Mitigation: Provide clear migration guide

⚠️ **Document-level Queries**
- Scroll-based queries for document metadata (not indexed)
- May be slower for large collections
- Mitigation: Most queries are chunk-based anyway

⚠️ **Payload Retrieval**
- Must use `with_payload=True` in searches
- Slightly larger response payloads
- Mitigation: Minimal impact, we need content anyway

### Overall Assessment

**The benefits far outweigh the trade-offs.** This refactoring simplifies the architecture, improves performance, and reduces complexity—all critical factors for long-term maintainability.

---

## Rollback Plan

If issues arise during/after migration:

1. **Keep SQLite backup** until fully validated
2. **Git revert** to previous version
3. **Restore Qdrant** from snapshot (if taken)
4. **Redeploy** old version

---

## Timeline Estimate

- **Code changes**: 2-3 hours
- **Testing**: 2-3 hours
- **Documentation updates**: 1 hour
- **Migration/reprocessing**: Depends on data size

**Total**: ~6-8 hours for complete refactoring

---

## Next Steps

1. ✅ Review this plan
2. ⬜ Create feature branch: `git checkout -b feature/remove-sqlite`
3. ⬜ Implement changes following this plan
4. ⬜ Test thoroughly
5. ⬜ Update documentation
6. ⬜ Create PR for review
7. ⬜ Deploy to staging/test environment
8. ⬜ Migrate production data
9. ⬜ Deploy to production
10. ⬜ Monitor and validate

---

## Questions & Considerations

### Should we keep document-level metadata?
**Decision needed**: Do we still need aggregated document metadata, or is chunk-level sufficient?

Current approach: Each chunk stores document info. For document-level queries, we scroll and deduplicate.

**Alternative**: Store separate "document" points with type="document" in payload for faster document queries.

### Payload size limits?
Qdrant has no hard limit on payload size, but very large payloads (>1MB) may impact performance.

**Recommendation**: Monitor payload sizes. If chunks are >10KB average, this is fine.

### Indexing payloads?
Qdrant can index payload fields for faster filtering.

**Recommendation**: Index `document_id`, `project_name`, `document_type` for filter performance.

---

**End of Plan**
