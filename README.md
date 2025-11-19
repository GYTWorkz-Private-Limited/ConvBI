# ConvBI Standalone - Conversational Business Intelligence System

A standalone Conversational BI system that converts natural language questions into SQL queries using LangGraph, Azure OpenAI, and vector search. This system enables users to interact with databases using natural language, making data exploration accessible to non-technical users.

## 🎯 Features

- **Natural Language to SQL**: Convert questions into SQL queries using Azure OpenAI
- **Hybrid Vector Search**: Uses Qdrant with dense (Azure OpenAI) and sparse (BM42) embeddings for semantic table discovery
- **Conversation Management**: Redis-based session management for maintaining conversation context
- **Intelligent Routing**: LangGraph workflow with intent classification, SQL generation, execution, and error handling
- **Visualization Suggestions**: Automatically suggests appropriate visualizations based on query results
- **Follow-up Questions**: Generates relevant follow-up questions to guide users
- **Error Recovery**: Automatic retry mechanism with clarification agent for failed queries
- **Optional Reranking**: Cohere reranking for improved search relevance
- **Observability**: Optional Langfuse integration for monitoring and debugging

## 📋 Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Setup Steps](#setup-steps)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Docker Deployment](#docker-deployment)
- [Troubleshooting](#troubleshooting)
- [Project Structure](#project-structure)

## 🏗️ Architecture

The system uses a Agentic workflow with the following components:

```
User Question
    ↓
Intent Classification
    ↓
┌─────────────────────────────────────┐
│  General → Greeting Agent           │
│  Help → Help Agent                  │
│  System Query → SQL Workflow       │
└─────────────────────────────────────┘
    ↓ (System Query path)
Populate Qdrant Data (Semantic Search)
    ↓
Text to SQL Generation
    ↓
Execute SQL Query
    ↓
┌─────────────────────────────────────┐
│  Success → Summarizer               │
│  Error → Clarification Agent        │
│  Max Retries → No Answer            │
└─────────────────────────────────────┘
    ↓ (Success path)
Visualization Agent
    ↓
Follow-up Questions
    ↓
Final Response
```

### Key Components

1. **FastAPI Server**: REST API with streaming SSE endpoints
2. **LangGraph Workflow**: State machine for orchestrating the conversation flow
3. **Qdrant Vector Database**: Stores table schemas and metadata for semantic search
4. **Redis**: Session storage for conversation history
5. **PostgreSQL**: Target database for SQL queries
6. **Azure OpenAI**: LLM for SQL generation and embeddings

## 📦 Prerequisites

### Required

- **Python 3.11+** (tested with Python 3.11)
- **PostgreSQL Database** (accessible from your network)
- **Azure OpenAI Account** with:
  - Chat completion model (e.g., GPT-4, GPT-3.5-turbo)
  - Embedding model (text-embedding-3-large)
- **Redis** (can run locally or via Docker)
- **Qdrant** (can run locally or via Docker)

### Optional

- **Cohere API Key** (for reranking - improves search quality)
- **Langfuse Account** (for observability and monitoring)
- **Docker & Docker Compose** (for containerized deployment)

## 🚀 Installation

### Method 1: Local Development Setup

1. **Clone or navigate to the project directory**:
   ```bash
   git clone <repository-url>
   cd <repository-name>/Text2SQL
   ```
   
   Or if you already have the project:
   ```bash
   cd <path-to-Text2SQL-folder>
   ```

2. **Create a virtual environment**:
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

### Method 2: Docker Setup (Recommended)

See [Docker Deployment](#docker-deployment) section below.

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root directory by copying the example:

```bash
cp env.example .env
```

### Required Configuration

Edit `.env` with your credentials:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_API_KEY=your-azure-openai-api-key

# Database Configuration (PostgreSQL)
QUERY_DB_HOST=your-db-host.example.com
QUERY_DB_PORT=5432
QUERY_DB_NAME=your_database_name
QUERY_DB_USER=your_db_user
QUERY_DB_PASSWORD=your_db_password

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Qdrant Configuration
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
```

### Optional Configuration

```env
# Cohere Reranking (Optional - improves search quality)
COHERE_API_KEY=your-cohere-api-key
COHERE_RERANK_MODEL=rerank-v3.5
COHERE_RERANK_TOP_K=10

# Langfuse Observability (Optional - for monitoring)
LANGFUSE_PUBLIC_KEY=your-langfuse-public-key
LANGFUSE_SECRET_KEY=your-langfuse-secret-key

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false
```

## 🔧 Setup Steps

### Step 1: Start Required Services

#### Option A: Using Docker Compose (Easiest)

```bash
docker-compose up -d redis qdrant
```

This starts Redis and Qdrant in containers. The API will run locally.

#### Option B: Local Installation

**Redis**:
```bash
# macOS
brew install redis
brew services start redis

# Linux
sudo apt-get install redis-server
sudo systemctl start redis

# Or use Docker
docker run -d -p 6379:6379 redis:7-alpine
```

**Qdrant**:
```bash
# Using Docker (recommended)
docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant:latest

# Or download binary from https://qdrant.tech/documentation/guides/installation/
```

### Step 2: Prepare Your Database Schema

The system needs a JSON template file describing your database schema. A sample template is provided at `semantics/template.json`.

**Template Structure**:
```json
{
  "schemas": {
    "schema_name": {
      "tables": [
        {
          "table_name": "users",
          "description": "Stores user account information",
          "primary_key": ["user_id"],
          "foreign_keys": [
            {
              "column": "organization_id",
              "references": {
                "table": "organizations",
                "column": "org_id"
              }
            }
          ],
          "columns": [
            {
              "column_name": "user_id",
              "data_type": "uuid",
              "description": "Unique identifier for each user"
            }
          ],
          "indexes": []
        }
      ]
    }
  }
}
```

### Step 3: Index Your Database Schema

Once your template is ready, index it to Qdrant:

**Using the API** (after starting the server):
```bash
curl -X POST "http://localhost:8000/api/v1/index" \
  -F "collection_name=semantics" \
  -F "template_path=semantics/template.json"
```

**Or using Python**:
```python
from services.hybrid_retrieval import HybridRetrieval
import json

# Load your template
with open('semantics/template.json', 'r') as f:
    template_data = json.load(f)

# Index to Qdrant
hybrid_retrieval = HybridRetrieval(collection_name="semantics")
hybrid_retrieval.index_tables(template_data)
```

### Step 4: Verify Configuration

Test your connections:

```python
# Test Redis
import redis
r = redis.Redis(host='localhost', port=6379)
r.ping()  # Should return True

# Test Qdrant
from qdrant_client import QdrantClient
client = QdrantClient(url="http://localhost:6333")
client.get_collections()  # Should return your collections

# Test PostgreSQL
import psycopg
conn = psycopg.connect(
    host="your-host",
    port=5432,
    dbname="your-db",
    user="your-user",
    password="your-password"
)
conn.close()
```

## 🏃 Running the Application

### Local Development

1. **Activate virtual environment**:
   ```bash
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Start the server**:
   ```bash
   python main.py
   ```

   Or using uvicorn directly:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. **Verify the server is running**:
   - Health check: http://localhost:8000/health
   - API docs: http://localhost:8000/docs
   - Root: http://localhost:8000/

### Production

For production, use a process manager like `gunicorn` with `uvicorn` workers:

```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 📡 API Documentation

### Endpoints

#### 1. Health Check
```http
GET /health
```

Response:
```json
{
  "status": "healthy"
}
```

#### 2. Index Schema
```http
POST /api/v1/index
Content-Type: multipart/form-data

collection_name: semantics
template_path: semantics/template.json
```

Response:
```json
{
  "status": "success",
  "message": "Successfully indexed 10 tables to Qdrant",
  "collection_name": "semantics",
  "total_tables": 10,
  "total_indexes": 5,
  "total_schemas": 1
}
```

#### 3. Stream Chat (Main Endpoint)
```http
POST /api/v1/stream/chat
Content-Type: application/json

{
  "question": "How many users do we have?",
  "user_id": "user123",
  "collection_name": "semantics",
  "thread_id": "optional-thread-id"
}
```

**Response**: Server-Sent Events (SSE) stream

Example stream events:
```
data: {"type":"node_update","data":{"node":"intent_classification","message":"Understanding what you need..."},"timestamp":"2024-01-01T12:00:00"}

data: {"type":"node_update","data":{"node":"text_to_sql","message":"Figuring out the best way to answer your question..."},"timestamp":"2024-01-01T12:00:01"}

data: {"type":"final_answer","data":{"final_answer":"You have 1,234 users in the database.","sql_query":"SELECT COUNT(*) FROM users;","visualization_data":{"chart_type":"number","data":1234},"follow_up_questions":["Show me users by organization","What's the average age of users?"]}}
```

## 🐳 Docker Deployment

### Full Docker Setup

1. **Copy Docker environment file**:
   ```bash
   cp docker-compose.env.example .env
   ```

2. **Edit `.env`** with your external service credentials (PostgreSQL, Azure OpenAI)

3. **Build and start all services**:
   ```bash
   docker-compose up -d
   ```

4. **Check logs**:
   ```bash
   docker-compose logs -f text2sql-api
   ```

5. **Access the API**:
   - API: http://localhost:8000
   - Health: http://localhost:8000/health
   - Docs: http://localhost:8000/docs

### Docker Services

The `docker-compose.yml` includes:
- **text2sql-api**: FastAPI application (port 8000)
- **redis**: Redis server (port 6379)
- **qdrant**: Vector database (ports 6333, 6334)

### Docker Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Rebuild after code changes
docker-compose up -d --build

# Remove all data (volumes)
docker-compose down -v

# Execute commands in container
docker-compose exec text2sql-api bash
```

For more Docker details, see [DOCKER.md](DOCKER.md).

## 🔍 Troubleshooting

### Common Issues

#### 1. Connection Errors

**Redis Connection Failed**:
```
Error: Error 111 connecting to localhost:6379
```
**Solution**: Ensure Redis is running:
```bash
redis-cli ping  # Should return PONG
# Or start Redis: docker run -d -p 6379:6379 redis:7-alpine
```

**Qdrant Connection Failed**:
```
Error: Connection refused to http://localhost:6333
```
**Solution**: Ensure Qdrant is running:
```bash
curl http://localhost:6333/health  # Should return {"status":"ok"}
# Or start Qdrant: docker run -d -p 6333:6333 qdrant/qdrant:latest
```

**PostgreSQL Connection Failed**:
```
Error: could not connect to server
```
**Solution**: 
- Verify database credentials in `.env`
- Check network connectivity
- Ensure database allows connections from your IP
- For SSL connections, ensure `sslmode=require` is set

#### 2. Azure OpenAI Errors

**Invalid API Key**:
```
Error: Invalid API key provided
```
**Solution**: 
- Verify `AZURE_OPENAI_API_KEY` in `.env`
- Check API key hasn't expired
- Ensure key has access to the deployment

**Deployment Not Found**:
```
Error: The API deployment for this resource does not exist
```
**Solution**: 
- Verify `AZURE_OPENAI_DEPLOYMENT_NAME` matches your Azure deployment
- Check `AZURE_OPENAI_ENDPOINT` is correct
- Ensure deployment is active in Azure portal

#### 3. Qdrant Collection Issues

**Collection Not Found**:
```
Error: Collection 'semantics' not found
```
**Solution**: Index your schema first:
```bash
curl -X POST "http://localhost:8000/api/v1/index" \
  -F "collection_name=semantics" \
  -F "template_path=semantics/template.json"
```

#### 4. SQL Generation Issues

**Poor SQL Quality**:
- Ensure your schema template is comprehensive with good descriptions
- Check that relevant tables are being retrieved from Qdrant
- Verify conversation history is being maintained (check Redis)

**SQL Errors**:
- The system has automatic retry with clarification agent
- Check error messages in the response
- Verify table/column names match your actual database

#### 5. Import Errors

**Module Not Found**:
```
ModuleNotFoundError: No module named 'convBI'
```
**Solution**: 
- Ensure you're in the project root directory (where `main.py` is located)
- Verify virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

### Debug Mode

Enable debug mode for detailed logging:

```bash
# In .env
DEBUG=true

# Or when running
DEBUG=true python main.py
```

### Logs

Check application logs for detailed error information:
- Local: Console output
- Docker: `docker-compose logs -f text2sql-api`

## 📁 Project Structure

```
Text2SQL/                           # Project root (this directory)
├── convBI/                         # Core ConvBI module
│   ├── agents/                     # LangGraph agents
│   │   ├── intent.py              # Intent classification
│   │   ├── text_to_sql.py         # SQL generation
│   │   ├── execute_sql.py          # SQL execution
│   │   ├── clarification.py       # Error recovery
│   │   ├── summarizer.py          # Result summarization
│   │   ├── visualization.py       # Visualization suggestions
│   │   ├── followups.py           # Follow-up questions
│   │   └── populate_qdrant_data.py # Semantic search
│   ├── config/
│   │   └── models.py              # Workflow state models
│   ├── prompts/                    # LLM prompts
│   │   ├── intent.py
│   │   ├── text_to_sql.py
│   │   ├── summarizer.py
│   │   ├── visualization.py
│   │   └── ...
│   ├── conversationalBI.py        # Main workflow
│   ├── qdrant_service.py          # Qdrant wrapper
│   └── redis_session.py           # Redis session management
├── routes/                         # FastAPI routes
│   ├── chat.py                    # Chat streaming endpoint
│   ├── health.py                  # Health check
│   ├── index.py                   # Schema indexing
│   └── models.py                  # Request models
├── services/                       # External services
│   ├── hybrid_retrieval.py        # Vector search
│   ├── cohere_reranker.py         # Reranking service
│   └── qdrant/
│       └── client.py              # Qdrant client
├── semantics/                      # Schema templates
│   └── template.json              # Example schema
├── main.py                         # FastAPI application
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Docker image
├── docker-compose.yml              # Docker services
├── docker-compose.env.example      # Docker env template
├── env.example                     # Environment template
├── README.md                       # This file
└── DOCKER.md                       # Docker documentation
```

## 🔐 Security Considerations

1. **Environment Variables**: Never commit `.env` files to version control
2. **API Keys**: Rotate API keys regularly
3. **Database Access**: Use read-only database users when possible
4. **Network Security**: Use SSL/TLS for database connections
5. **Rate Limiting**: Consider adding rate limiting for production
6. **Authentication**: Add authentication/authorization for production use

## 📚 Additional Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangChain Documentation](https://python.langchain.com/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Azure OpenAI Documentation](https://learn.microsoft.com/en-us/azure/ai-services/openai/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

[Add your license information here]

## 🆘 Support

For issues and questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review application logs
3. Check Azure OpenAI, PostgreSQL, Redis, and Qdrant connectivity
4. Open an issue with detailed error messages and logs

---

**Built with ❤️ using LangGraph, Azure OpenAI, and FastAPI**

