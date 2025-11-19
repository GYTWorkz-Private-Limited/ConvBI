# Docker Setup Guide

This guide explains how to run the Text2SQL API using Docker.

## Prerequisites

- Docker and Docker Compose installed
- `.env` file configured with external service credentials

## Quick Start

1. **Copy environment file**:
   ```bash
   cp docker-compose.env.example .env
   ```

2. **Edit `.env` file** with your external service credentials:
   - PostgreSQL connection details
   - Azure OpenAI API credentials
   - Optional: Cohere API key, Langfuse keys

3. **Build and start services**:
   ```bash
   docker-compose up -d
   ```

4. **Check logs**:
   ```bash
   docker-compose logs -f text2sql-api
   ```

5. **Access the API**:
   - API: http://localhost:8000
   - Health check: http://localhost:8000/health
   - API docs: http://localhost:8000/docs

## Services

The Docker Compose setup includes:

- **text2sql-api**: FastAPI application (port 8000)
- **redis**: Redis server for session management (port 6379)
- **qdrant**: Vector database for semantic search (ports 6333, 6334)

## Environment Variables

### Internal Services (Auto-configured)
- `REDIS_HOST=redis` (Docker service name)
- `QDRANT_URL=http://qdrant:6333` (Docker service name)

### External Services (Configure in `.env`)
- PostgreSQL database connection
- Azure OpenAI API credentials
- Optional: Cohere, Langfuse

## Common Commands

### Start services
```bash
docker-compose up -d
```

### Stop services
```bash
docker-compose down
```

### View logs
```bash
docker-compose logs -f
```

### Rebuild after code changes
```bash
docker-compose up -d --build
```

### Remove all data (volumes)
```bash
docker-compose down -v
```

### Execute commands in container
```bash
docker-compose exec text2sql-api bash
```

## Troubleshooting

### Port already in use
If ports 8000, 6379, or 6333 are already in use, modify the port mappings in `docker-compose.yml`.

### Connection issues
- Ensure external services (PostgreSQL, Azure OpenAI) are accessible
- Check `.env` file has correct credentials
- Verify network connectivity from Docker container

### Health check failures
- Check container logs: `docker-compose logs text2sql-api`
- Verify all environment variables are set correctly
- Ensure external services are reachable

## Data Persistence

- Redis data: Stored in `redis-data` volume
- Qdrant data: Stored in `qdrant-data` volume
- Semantics templates: Mounted from `./semantics` directory

Volumes persist even after containers are stopped. To remove all data, use `docker-compose down -v`.

