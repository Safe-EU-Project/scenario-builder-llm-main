# Scenario Builder Service

A comprehensive document processing service that combines document extraction, RAG (Retrieval-Augmented Generation), and LLM integration to build intelligent scenario analysis systems.

## 🚀 Features

- **Multi-Format Document Extraction**: Support for PDF, Word (.docx), Excel (.xlsx), and text files
- **Intelligent Text Chunking**: Semantic document chunking for optimal retrieval
- **Vector-Based RAG Pipeline**: Powered by Qdrant for efficient similarity search
- **Hybrid Search**: Optional sparse + dense vector search with BM25
- **Advanced Reranking**: Cross-encoder reranking for improved retrieval accuracy
- **LLM Integration**: Generate contextual answers using open-source LLMs with OpenAI SDK
- **Structured Scenario Generation**: Generate validated JSON scenarios using Pydantic models and structured output
- **Scenario Ingestion**: Ingest human-reviewed scenarios back into the RAG pipeline
- **Document Retrieval**: Retrieve full document content by ID for review and export
- **Clean API Design**: RESTful API with multiple endpoints for processing, querying, and scenario management

## 📋 Architecture

```
scenario-builder/
├── src/
│   ├── api/              # FastAPI application and endpoints
│   ├── config/           # Configuration and settings
│   ├── extraction/       # Document extraction from multiple formats
│   ├── processing/       # Text chunking and preprocessing
│   ├── embeddings/       # Dense and sparse embedding generation
│   ├── storage/          # Vector store (Qdrant) and metadata (SQLite)
│   ├── retrieval/        # Search and reranking systems
│   └── llm/              # LLM client for answer generation
├── data/                 # Default folder for documents to process
├── main.py               # Application entry point
├── requirements.txt      # Python dependencies
└── .env.example          # Environment configuration template
```

## 🛠️ Installation

### Quick Start with Docker (Recommended)

The easiest way to get started:

```bash
# Start all services (Qdrant + Scenario Builder)
docker-compose up -d

# View logs
docker-compose logs -f

# Service available at http://localhost:8002
```

📖 See [DOCKER.md](DOCKER.md) for complete Docker documentation.

### Manual Installation

#### Prerequisites

- Python 3.10+
- Qdrant vector database (local or remote)
- LLM API endpoint (e.g., Ollama, LM Studio)

#### Setup

1. **Clone and navigate to the directory**:
```bash
cd scenario-builder
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your settings
```

5. **Start Qdrant** (if not already running):
```bash
docker run -p 6333:6333 qdrant/qdrant
```

6. **Start your LLM service** (e.g., Ollama):
```bash
ollama serve
ollama pull llama2
```

## 🚀 Usage

### Starting the Service

```bash
python main.py
```

The service will be available at `http://localhost:8002` (or your configured port).

### API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8002/docs`
- ReDoc: `http://localhost:8002/redoc`

### API Endpoints

#### 1. Health Check

```bash
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "service": "Scenario Builder Service",
  "timestamp": "2025-10-06T12:00:00",
  "version": "1.0.0"
}
```

#### 2. Process Documents

Extracts text from documents in the data folder and stores them in the vector database.

```bash
POST /api/v1/process
```

**Request Body**:
```json
{
  "data_folder": "./data",  // Optional, defaults to configured folder
  "force_reprocess": false   // Optional, reprocess existing documents
}
```

**Response**:
```json
{
  "status": "completed",
  "message": "Successfully processed 5 documents",
  "documents_processed": 5,
  "chunks_created": 87
}
```

**Example**:
```bash
curl -X POST "http://localhost:8002/api/v1/process" \
  -H "Content-Type: application/json" \
  -d '{
    "data_folder": "./data",
    "force_reprocess": false
  }'
```

#### 3. Query with LLM

Retrieves relevant context and generates an answer using the LLM.

```bash
POST /api/v1/query
```

**Request Body**:
```json
{
  "query": "What are the main objectives?",
  "top_k": 5,                        // Number of chunks to retrieve
  "use_reranking": true,             // Apply reranking
  "use_hybrid": false,               // Use hybrid search
  "initial_k": 150,                  // Initial retrieval for reranking
  "use_advanced_reranker": true      // Use cross-encoder reranking
}
```

**Response**:
```json
{
  "query": "What are the main objectives?",
  "answer": "Based on the documents, the main objectives are...",
  "context": "[Source: document1.pdf]\nThe objectives include...",
  "sources": [
    {
      "document_name": "document1.pdf",
      "document_type": ".pdf",
      "score": 0.92,
      "chunk_id": "abc123_chunk_0"
    }
  ],
  "metadata": {
    "initial_retrieval_count": 150,
    "final_count": 5,
    "reranking_applied": true,
    "advanced_reranker_used": true,
    "hybrid_search_used": false
  }
}
```

**Example**:
```bash
curl -X POST "http://localhost:8002/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main objectives?",
    "top_k": 5,
    "use_reranking": true
  }'
```

#### 4. Structured Scenario Generation

Generate a structured scenario with validated JSON output using Ollama's JSON schema mode. Returns a complete scenario with title and multiple incidents.

```bash
POST /api/v1/query_structured
```

**Request Body**:
```json
{
  "query": "Generate a cybersecurity incident scenario",
  "top_k": 20,
  "use_reranking": true,
  "use_hybrid": false,
  "initial_k": 150,
  "use_advanced_reranker": true
}
```

**Response**:
```json
{
  "query": "Generate a cybersecurity incident scenario",
  "scenario": {
    "scenario_title": "Advanced Persistent Threat Campaign",
    "incidents": [
      {
        "title": "Initial Reconnaissance Detected",
        "message_timestamp": "08:00",
        "description": "Unusual port scanning activity detected...",
        "inject": "Security alert notification",
        "expected_actions": [
          "Review firewall logs",
          "Block suspicious IP addresses",
          "Notify security team"
        ]
      }
    ]
  },
  "context": "[Source: document1.pdf]\nRelevant context...",
  "sources": [...],
  "metadata": {...}
}
```

**Example**:
```bash
curl -X POST "http://localhost:8002/api/v1/query_structured" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Generate a cybersecurity incident scenario",
    "top_k": 20
  }'
```

#### 5. Ingest Human-Reviewed Scenario

Ingest a human-reviewed scenario back into the RAG pipeline for future retrieval and learning.

```bash
POST /api/v1/ingest_scenario
```

**Request Body**:
```json
{
  "content": "Scenario Title: Data Breach Response\n\nIncident 1...\nIncident 2..."
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Scenario successfully ingested with 5 chunks",
  "document_id": "scenario_20251027_142544_04746b33"
}
```

**Example**:
```bash
curl -X POST "http://localhost:8002/api/v1/ingest_scenario" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Your human-reviewed scenario content here..."
  }'
```

#### 6. Get Document by ID

Retrieve the full content of a previously ingested document by its ID.

```bash
GET /api/v1/document/{document_id}
```

**Response**:
```json
{
  "document_id": "scenario_20251027_142544_04746b33",
  "content": "Full document content with all chunks concatenated..."
}
```

**Example**:
```bash
curl -X GET "http://localhost:8002/api/v1/document/scenario_20251027_142544_04746b33"
```

## ⚙️ Configuration

Edit `.env` file to configure the service:

### Service Configuration
```env
SERVICE_PORT=8002          # API service port
LOG_LEVEL=INFO            # Logging level (DEBUG, INFO, WARNING, ERROR)
```

### Data Configuration
```env
DATA_FOLDER=./data        # Folder containing documents to process
```

### Vector Database (Qdrant)
```env
QDRANT_HOST=localhost     # Qdrant host
QDRANT_PORT=6333          # Qdrant port
COLLECTION_NAME=scenarios  # Collection name for vectors
EMBEDDING_DIM=384         # Embedding dimensions
```

### Embedding Model
```env
EMBEDDING_PROVIDER=sentence_transformer
EMBEDDING_MODEL=all-MiniLM-L6-v2  # Sentence transformer model
EMBEDDING_DEVICE=cpu               # cpu or cuda
EMBEDDING_BATCH_SIZE=32
```

### Document Processing
```env
CHUNK_SIZE=1000           # Target chunk size in characters
CHUNK_OVERLAP=200         # Overlap between chunks
MAX_CHUNK_SIZE=2000       # Maximum chunk size
```

### Retrieval
```env
DEFAULT_TOP_K=5           # Default number of results
MAX_TOP_K=20              # Maximum allowed results
RETRIEVAL_ALPHA=0.7       # Vector search weight for hybrid mode
```

### LLM Configuration
```env
LLM_API_URL=http://localhost:11434/v1/chat/completions  # OpenAI-compatible endpoint
LLM_MODEL=llama2                                         # Model name
LLM_TEMPERATURE=0.7                                      # Temperature (0.0-1.0)
LLM_SEED=42                                              # Seed for reproducibility
LLM_STREAM=false                                         # Streaming mode
```

**Note**: Uses the OpenAI-compatible `/v1/chat/completions` endpoint with structured output support. Compatible with:
- Ollama (e.g., `http://localhost:11434/v1/chat/completions`) - Supports JSON schema mode for structured responses
- LM Studio
- vLLM
- Any OpenAI-compatible API

**Structured Output**: The `/api/v1/query_structured` endpoint leverages the OpenAI SDK's `beta.chat.completions.parse` method to ensure LLM responses conform to the Pydantic `Scenario` model, providing validated JSON output with full scenarios containing multiple incidents.

## 📁 Supported Document Formats

| Format | Extensions | Library |
|--------|-----------|---------|
| PDF | `.pdf` | PyPDF2 |
| Word | `.docx`, `.doc` | python-docx |
| Excel | `.xlsx`, `.xls` | openpyxl |
| Text | `.txt`, `.md` | Built-in |

## 🔧 Extending Document Extraction

To add support for new document formats, edit `src/extraction/extractor.py`:

```python
def extract_from_file(self, file_path: str) -> str:
    # Add new format handler
    if extension == '.new_format':
        return self._extract_new_format(file_path)
```

## 🏗️ RAG Pipeline Details

### Processing Flow

1. **Document Extraction**: Read files from data folder
2. **Text Chunking**: Split documents into semantic chunks
3. **Embedding Generation**: Generate dense (and optionally sparse) vectors
4. **Storage**: Store in Qdrant vector DB + SQLite metadata DB
5. **Retrieval**: Semantic search with optional reranking
6. **LLM Integration**: Generate contextual answers

### Search Strategies

- **Dense Vector Search**: Default semantic search using sentence embeddings
- **Hybrid Search**: Combines dense vectors + BM25 sparse vectors using RRF (Reciprocal Rank Fusion)
- **Reranking**: Optional cross-encoder reranking for improved precision

## 🧪 Example Workflow

### 1. Add Documents
```bash
# Place your documents in the data folder
mkdir -p data
cp /path/to/your/documents/*.pdf data/
```

### 2. Process Documents
```bash
curl -X POST "http://localhost:8002/api/v1/process" \
  -H "Content-Type: application/json" \
  -d '{"force_reprocess": false}'
```

### 3. Query
```bash
curl -X POST "http://localhost:8002/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Summarize the key findings",
    "top_k": 5
  }'
```

### 4. Generate Structured Scenario
```bash
curl -X POST "http://localhost:8002/api/v1/query_structured" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Create a cybersecurity training scenario",
    "top_k": 20
  }'
```

### 5. Ingest Human-Reviewed Scenario
```bash
curl -X POST "http://localhost:8002/api/v1/ingest_scenario" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Your reviewed scenario content..."
  }'
```

### 6. Retrieve Ingested Scenario
```bash
# Use the document_id returned from the ingest endpoint
curl -X GET "http://localhost:8002/api/v1/document/scenario_20251027_142544_04746b33"
```

