# Docker Deployment Guide

Complete guide for deploying Scenario Builder Service with Docker.

## Basic Commands:
```bash 
docker-compose -f docker-compose.service-only.yml restart
docker-compose -f docker-compose.service-only.yml build
docker-compose -f docker-compose.service-only.yml up -d
docker-compose -f docker-compose.service-only.yml logs -f
```


## 🚀 Quick Start

### Prerequisites
- Docker Engine 20.10+
- Docker Compose 2.0+

### Start Everything

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f scenario-builder

# Check status
docker-compose ps
```

That's it! The service will be available at `http://localhost:8002`

## 📋 Services

The `docker-compose.yml` includes:

1. **Qdrant** (Vector Database)
   - Port: 6333 (HTTP API)
   - Port: 6334 (gRPC)
   - Web UI: http://localhost:6333/dashboard

2. **Scenario Builder** (Main Service)
   - Port: 8002
   - API Docs: http://localhost:8002/docs
   - Health: http://localhost:8002/health

## 🔧 Configuration

### Environment Variables

Edit `docker-compose.yml` to customize:

```yaml
environment:
  # Service
  - SERVICE_PORT=8002
  - LOG_LEVEL=INFO

  # Qdrant
  - QDRANT_HOST=qdrant
  - QDRANT_PORT=6333

  # LLM (adjust to your setup)
  - LLM_API_URL=http://host.docker.internal:11434/v1/chat/completions
  - LLM_MODEL=llama2
```

### Using External LLM Service

#### Option 1: LLM on Host Machine

If your LLM (e.g., Ollama) runs on the host:

```yaml
environment:
  - LLM_API_URL=http://host.docker.internal:11434/v1/chat/completions
```

#### Option 2: LLM in Docker Network

Add your LLM service to `docker-compose.yml`:

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    networks:
      - scenario-network

  scenario-builder:
    environment:
      - LLM_API_URL=http://ollama:11434/v1/chat/completions
```

#### Option 3: Remote LLM Service

```yaml
environment:
  - LLM_API_URL=http://your-llm-server:11434/v1/chat/completions
```

### Using GPU

To use GPU for embeddings, modify the Dockerfile:

```dockerfile
# Change base image
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# And in docker-compose.yml add:
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]

environment:
  - EMBEDDING_DEVICE=cuda
```

## 📁 Data Management

### Adding Documents

Place your documents in the `./data` folder:

```bash
# Copy documents
cp /path/to/docs/*.pdf ./data/

# The folder is automatically mounted in the container
```

### Processing Documents

```bash
# Process all documents in data folder
curl -X POST "http://localhost:8002/process" \
  -H "Content-Type: application/json" \
  -d '{"force_reprocess": false}'
```

### Persistent Storage

Data is persisted in Docker volumes:
- `qdrant_storage`: Vector database data
- `scenario_metadata`: SQLite metadata database

## 🛠️ Development

### Hot Reload

Source code is mounted as a volume for development:

```yaml
volumes:
  - ./src:/app/src
  - ./main.py:/app/main.py
```

Changes to Python files will trigger auto-reload.

### Rebuild After Dependency Changes

```bash
# Rebuild the image
docker-compose build scenario-builder

# Restart
docker-compose up -d scenario-builder
```

## 📊 Monitoring

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f scenario-builder

# Last 100 lines
docker-compose logs --tail=100 scenario-builder
```

### Health Checks

```bash
# Service health
curl http://localhost:8002/health

# Qdrant health
curl http://localhost:6333/health
```

### Access Qdrant Dashboard

Open http://localhost:6333/dashboard in your browser.

## 🔄 Common Operations

### Start Services

```bash
docker-compose up -d
```

### Stop Services

```bash
docker-compose down
```

### Restart Service

```bash
docker-compose restart scenario-builder
```

### View Service Status

```bash
docker-compose ps
```

### Execute Commands in Container

```bash
# Open shell
docker-compose exec scenario-builder bash

# Run Python script
docker-compose exec scenario-builder python -c "print('Hello')"
```

### Update Services

```bash
# Pull latest images
docker-compose pull

# Rebuild and restart
docker-compose up -d --build
```

## 🗄️ Database Management

### Backup Qdrant Data

```bash
# Create backup
docker run --rm \
  -v scenario-builder_qdrant_storage:/source \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/qdrant-backup-$(date +%Y%m%d).tar.gz -C /source .
```

### Restore Qdrant Data

```bash
# Stop services
docker-compose down

# Restore backup
docker run --rm \
  -v scenario-builder_qdrant_storage:/target \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/qdrant-backup-YYYYMMDD.tar.gz -C /target

# Start services
docker-compose up -d
```

### Reset Everything

```bash
# Stop and remove containers, volumes
docker-compose down -v

# Start fresh
docker-compose up -d
```

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs scenario-builder

# Check if port is in use
netstat -an | grep 8002

# Verify Qdrant is running
docker-compose ps qdrant
```

### Can't Connect to LLM

```bash
# Test from container
docker-compose exec scenario-builder curl http://host.docker.internal:11434/api/tags

# If it fails, check your LLM service
curl http://localhost:11434/api/tags
```

### Out of Memory

Increase Docker memory limits in Docker Desktop settings, or add to `docker-compose.yml`:

```yaml
services:
  scenario-builder:
    deploy:
      resources:
        limits:
          memory: 4G
```

### Permission Issues

```bash
# Fix data folder permissions
sudo chown -R $USER:$USER ./data

# Or run with sudo
sudo docker-compose up -d
```

## 🚀 Production Deployment

### Using .env File

Create a `.env` file:

```bash
# .env
SERVICE_PORT=8002
QDRANT_HOST=qdrant
LLM_API_URL=http://llm-service:11434/v1/chat/completions
LLM_MODEL=llama2
```

Update `docker-compose.yml`:

```yaml
services:
  scenario-builder:
    env_file:
      - .env
```

### Behind Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name scenario-builder.yourdomain.com;

    location / {
        proxy_pass http://localhost:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Resource Limits

```yaml
services:
  scenario-builder:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

### Auto-restart Policy

```yaml
services:
  scenario-builder:
    restart: always  # or 'unless-stopped'
```

## 📝 Example Workflow

```bash
# 1. Start services
docker-compose up -d

# 2. Wait for services to be ready (30-60 seconds)
docker-compose logs -f scenario-builder | grep "initialized"

# 3. Add documents
cp ~/Documents/*.pdf ./data/

# 4. Process documents
curl -X POST http://localhost:8002/process \
  -H "Content-Type: application/json" \
  -d '{"force_reprocess": false}'

# 5. Query
curl -X POST http://localhost:8002/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main topics?",
    "top_k": 5
  }'
```

## 🔐 Security Notes

- Change default ports in production
- Use environment variables for secrets
- Don't expose Qdrant ports publicly
- Use Docker secrets for sensitive data
- Enable authentication on Qdrant in production
- Run containers as non-root user

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/)
- [Qdrant Docker Guide](https://qdrant.tech/documentation/guides/installation/#docker)
