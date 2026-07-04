# Quick Start Guide

Get the Scenario Builder Service up and running in 5 minutes!

## 1️⃣ Prerequisites

Make sure you have:
- Python 3.8 or higher
- Qdrant running (vector database)
- An LLM service (e.g., Ollama)

### Start Qdrant (Docker)
```bash
docker run -d -p 6333:6333 qdrant/qdrant
```

### Start Ollama (if using Ollama)
```bash
# Install Ollama from https://ollama.ai
ollama serve
ollama pull llama2  # or any other model
```

## 2️⃣ Install

```bash
cd scenario-builder

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## 3️⃣ Configure

```bash
# Copy example configuration
cp .env.example .env

# Edit .env if needed (optional for local development)
# Default settings work with local Qdrant and Ollama
```

Key settings to verify in `.env`:
```env
# Make sure these match your setup
QDRANT_HOST=localhost
QDRANT_PORT=6333
LLM_API_URL=http://localhost:11434/v1/chat/completions
LLM_MODEL=llama2
```

## 4️⃣ Add Documents

Place your documents in the `data` folder:

```bash
mkdir -p data
cp /path/to/your/documents/*.pdf data/
cp /path/to/your/documents/*.docx data/
```

Supported formats: `.pdf`, `.docx`, `.xlsx`, `.txt`, `.md`

## 5️⃣ Start the Service

```bash
python main.py
```

You should see:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8002
```

## 6️⃣ Test It!

### Option A: Use the example script
```bash
# In a new terminal (keep the service running)
python example_usage.py
```

### Option B: Use curl

**Process documents:**
```bash
curl -X POST "http://localhost:8002/process" \
  -H "Content-Type: application/json" \
  -d '{"force_reprocess": false}'
```

**Query with LLM:**
```bash
curl -X POST "http://localhost:8002/api/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main topics?",
    "top_k": 5
  }'
```

### Option C: Use the interactive API docs
Open your browser: http://localhost:8002/docs

## 🎉 You're Done!

Your scenario builder is now running. You can:

1. **Process documents** with `/process` endpoint
2. **Query and get AI answers** with `/api/query` endpoint
3. **Monitor service** at `/health` endpoint

## 📚 Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Explore the API docs at http://localhost:8002/docs
- Customize the configuration in `.env`
- Add more documents to the `data` folder


