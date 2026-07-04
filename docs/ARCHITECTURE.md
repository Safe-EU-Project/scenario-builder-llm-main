# Architecture Documentation

## System Overview

The Scenario Builder Service is a modular document processing and question-answering system that combines document extraction, RAG (Retrieval-Augmented Generation), and LLM integration.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Application                       │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP REST API
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Service                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  API Endpoints                                            │  │
│  │  • POST /process - Process documents                      │  │
│  │  • POST /api/query - Query with LLM                       │  │
│  │  • GET /health - Health check                             │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Core Components                             │
│                                                                   │
│  ┌────────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   Document     │  │  Processing  │  │   Embeddings     │   │
│  │  Extraction    │─▶│  & Chunking  │─▶│   Generation     │   │
│  └────────────────┘  └──────────────┘  └──────────────────┘   │
│                                                   │              │
│                                                   ▼              │
│  ┌────────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │      LLM       │◀─│  Retrieval   │◀─│  Vector Store    │   │
│  │  Integration   │  │   System     │  │   (Qdrant)       │   │
│  └────────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     External Services                            │
│  • Qdrant (Vector Database)                                      │
│  • SQLite (Metadata Database)                                    │
│  • LLM API (Ollama, LM Studio, etc.)                            │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. API Layer (`src/api/`)

**Purpose**: Provides REST API endpoints for external interaction.

**Components**:
- `api.py`: FastAPI application with endpoint definitions
- Request/Response models defined in `src/config/models.py`

**Key Endpoints**:
- `POST /process`: Trigger document processing pipeline
- `POST /api/query`: Query documents and get LLM-generated answers
- `GET /health`: Service health check

**Flow**:
```
Client Request → FastAPI → Service Components → Response
```

### 2. Document Extraction (`src/extraction/`)

**Purpose**: Extract text from various document formats.

**Components**:
- `extractor.py`: Multi-format document extraction

**Supported Formats**:
- PDF: Using PyPDF2
- Word: Using python-docx
- Excel: Using openpyxl
- Text: Built-in Python support

**Process**:
1. Scan configured data folder
2. Identify file types by extension
3. Route to appropriate extraction method
4. Return structured text content with metadata

### 3. Processing & Chunking (`src/processing/`)

**Purpose**: Split extracted text into semantic chunks for optimal retrieval.

**Components**:
- `processors.py`: Document chunking logic
- `DocumentChunker`: Implements recursive text splitting
- `DocumentProcessor`: Coordinates processing pipeline

**Chunking Strategy**:
- Configurable chunk size and overlap
- Hierarchical splitting using separators:
  1. Paragraph breaks (`\n\n`)
  2. Line breaks (`\n`)
  3. Sentence endings (`. `, `? `, `! `)
  4. Clauses (`;`, `,`)
  5. Words (` `)
  6. Character-level (fallback)

**Metadata Tracking**:
- Chunk index and position
- Source document information
- Chunk size statistics

### 4. Embeddings Generation (`src/embeddings/`)

**Purpose**: Convert text chunks into vector representations.

**Components**:
- `embeddings.py`: Dense embedding service using sentence transformers
- `sparse_embeddings.py`: Sparse embedding service using BM25

**Dense Embeddings**:
- Model: `all-MiniLM-L6-v2` (default, configurable)
- Dimension: 384
- Use case: Semantic similarity

**Sparse Embeddings** (Optional):
- Algorithm: BM25
- Use case: Keyword matching, hybrid search

### 5. Storage Layer (`src/storage/`)

**Purpose**: Persist vectors and metadata.

**Components**:
- `vector_store.py`: Qdrant vector database interface
- `storage.py`: MinIO/S3 storage (from rag_service, not used in current implementation)

**Qdrant Collections**:
```python
{
  "vectors": {
    "dense": [384-dimensional float vectors],
    "sparse": [BM25 sparse vectors] (optional)
  },
  "payload": {
    "chunk_id": "unique_identifier",
    "document_id": "document_hash",
    "document_name": "filename",
    "document_type": "file_extension",
    "chunk_index": 0,
    "metadata": {...}
  }
}
```

**SQLite Metadata**:
- Stores full chunk text content
- Indexed by chunk_id
- Used for displaying search results

### 6. Retrieval System (`src/retrieval/`)

**Purpose**: Find relevant chunks for a given query.

**Components**:
- `retrieval.py`: Main retrieval orchestration
- `advanced_reranker.py`: Cross-encoder reranking
- `models.py`: Data models for retrieval

**Search Pipeline**:

```
Query → Embedding → Initial Retrieval (k=150) → Reranking → Top Results (k=5)
```

**Search Modes**:

1. **Dense Vector Search** (Default):
   - Semantic similarity using cosine distance
   - Fast and effective for most queries

2. **Hybrid Search** (Optional):
   - Combines dense + sparse vectors
   - Uses Reciprocal Rank Fusion (RRF)
   - Better for keyword-heavy queries

3. **Reranking** (Optional):
   - Cross-encoder model for precise ranking
   - Computationally expensive, applied to top-k candidates
   - Significantly improves relevance

### 7. LLM Integration (`src/llm/`)

**Purpose**: Generate natural language answers from retrieved context.

**Components**:
- `llm_client.py`: LLM API client

**Answer Generation Pipeline**:

```
1. Query → Retrieval System → Context Chunks
                                     ↓
2. System Prompt + Context + Query → LLM API
                                     ↓
3. LLM Response → Format → Return to Client
```

**Message Structure**:
```python
[
  {"role": "system", "content": "System prompt"},
  {"role": "system", "content": "Context:\n[Retrieved chunks]"},
  {"role": "user", "content": "User query"}
]
```

**Configurable Parameters**:
- Temperature: Controls randomness
- Seed: For reproducible results
- Model: LLM model name

### 8. Configuration (`src/config/`)

**Purpose**: Centralized configuration management.

**Components**:
- `settings.py`: Environment-based settings using dataclasses
- `models.py`: Pydantic models for API validation

**Configuration Sources**:
1. Environment variables
2. `.env` file
3. Default values in code

## Data Flow

### Document Processing Flow

```
1. Client triggers /process
        ↓
2. DocumentExtractor scans data folder
        ↓
3. Extract text from each document
        ↓
4. DocumentProcessor chunks text
        ↓
5. EmbeddingService generates vectors
        ↓
6. VectorStore stores in Qdrant + SQLite
        ↓
7. Return processing statistics
```

### Query Flow

```
1. Client sends query to /api/query
        ↓
2. RetrievalSystem embeds query
        ↓
3. Search Qdrant for similar chunks
        ↓
4. (Optional) Apply reranking
        ↓
5. Retrieve full text from SQLite
        ↓
6. Format context with sources
        ↓
7. LLMClient sends to LLM API
        ↓
8. Parse and return LLM response
```

## Design Decisions

### Why Two Databases?

**Qdrant** (Vector Store):
- Optimized for vector similarity search
- Fast nearest neighbor retrieval
- Stores vectors + lightweight metadata

**SQLite** (Metadata Store):
- Stores full chunk text content
- Cheaper storage for large text
- SQL queries for document management

### Why Reranking Pipeline?

**Two-Stage Retrieval**:
1. **Initial Retrieval (k=150)**: Fast vector search, recall-focused
2. **Reranking (k=5)**: Expensive but precise, precision-focused

**Benefits**:
- Better relevance without sacrificing speed
- Cross-encoder models are more accurate but slower
- Best of both worlds: fast initial retrieval + precise reranking

### Why Chunking?

**Challenges with Full Documents**:
- Too large for LLM context windows
- Dilutes relevance signals
- Less precise retrieval

**Benefits of Chunking**:
- Granular retrieval
- Better semantic matching
- Optimal LLM context usage

## Extensibility

### Adding New Document Formats

Edit `src/extraction/extractor.py`:

```python
def _extract_new_format(self, file_path: Path) -> str:
    # Implement extraction logic
    return extracted_text

def extract_from_file(self, file_path: str) -> str:
    if extension == '.new_ext':
        return self._extract_new_format(file_path)
```

### Adding New Data Sources

Create a new extractor class that implements:
```python
class NewDataSource:
    def extract_documents(self) -> List[Dict[str, str]]:
        # Return list of {extracted_text, metadata}
        pass
```

### Customizing Chunking

Modify `src/processing/processors.py`:
- Adjust `chunk_size` and `chunk_overlap`
- Change `separators` list for different splitting logic
- Implement domain-specific chunking strategies

### Using Different Embedding Models

Update `.env`:
```env
EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2
EMBEDDING_DIM=768  # Match model dimension
```

### Using Different LLM Providers

Modify `src/llm/llm_client.py` to support different API formats:
- OpenAI API
- Anthropic Claude
- Custom endpoints

## Performance Considerations

### Scaling

**Document Processing**:
- CPU-bound: Embedding generation
- I/O-bound: Document extraction
- Can be parallelized per document

**Query Performance**:
- Vector search: O(log n) with HNSW index
- Reranking: O(k) where k is number of candidates
- LLM call: Network latency dependent

### Optimization Tips

1. **Batch Processing**: Process multiple documents simultaneously
2. **GPU Acceleration**: Use CUDA for embedding generation
3. **Caching**: Cache embeddings for frequently queried text
4. **Index Tuning**: Adjust Qdrant HNSW parameters
5. **Async Operations**: Use async/await for I/O operations

## Security Considerations

1. **Input Validation**: All API inputs validated via Pydantic
2. **File Type Verification**: Extension-based file handling
3. **Path Traversal**: Restricted to configured data folder
4. **API Keys**: Store in environment variables, never in code
5. **CORS**: Configure allowed origins in production

## Monitoring & Observability

### Logging

Structured logging with `structlog`:
- Request/response logging
- Performance metrics
- Error tracking
- Component lifecycle events

### Key Metrics to Monitor

1. Document processing rate
2. Query latency (P50, P95, P99)
3. Retrieval quality (precision@k)
4. LLM response times
5. Error rates by component

## Future Enhancements

### Potential Improvements

1. **Multi-tenancy**: Project/user isolation
2. **Incremental Updates**: Update only changed documents
3. **Semantic Caching**: Cache LLM responses for similar queries
4. **Streaming Responses**: Stream LLM outputs
5. **Feedback Loop**: Learn from user ratings
6. **Multi-modal**: Support images, tables, charts
7. **Advanced Chunking**: Structure-aware splitting (markdown, code)
8. **Query Understanding**: Query expansion and reformulation
