# MacBook Air Chatbot Agent

A specialized chatbot agent built with LangChain, FastAPI, and Supabase that answers questions about MacBook Air. The agent combines RAG (Retrieval Augmented Generation) with web search capabilities to provide accurate and up-to-date information.

## Features

- **LangChain Agent**: Intelligent agent that orchestrates tool usage
- **Web Search**: Real-time web search using DuckDuckGo
- **RAG Integration**: Retrieval of stored MacBook Air facts from Supabase
- **Streaming Responses**: Server-Sent Events (SSE) for real-time responses
- **Docker Support**: Easy deployment with Docker
- **FastAPI**: Modern, fast web framework

## Architecture

The chatbot uses a two-tool approach:
1. **RAG Tool**: Retrieves relevant facts from a Supabase vector store
2. **Web Search Tool**: Fetches current information from the web

The agent intelligently decides when to use each tool or both, providing comprehensive answers.

## Prerequisites

- Python 3.11+
- OpenAI API key
- Supabase project with:
  - PostgreSQL database with pgvector extension
  - A table for storing MacBook Air facts (see setup instructions)

## Setup

### 1. Clone and Navigate

```bash
cd agent
```

### 2. Install Dependencies

```bash
# Install the package and all dependencies
pip install -e .

# Or install with development dependencies (includes ruff)
pip install -e ".[dev]"
```

### 3. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your:
- `OPENAI_API_KEY`: Get from https://platform.openai.com/api-keys
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase service role key

### 4. Set Up Supabase Database

#### Create the Facts Table

Run this SQL in your Supabase SQL editor:

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create macbook_facts table
CREATE TABLE IF NOT EXISTS macbook_facts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(1536),  -- Adjust dimension based on your embedding model
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for vector similarity search
CREATE INDEX IF NOT EXISTS macbook_facts_embedding_idx 
ON macbook_facts 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create function for similarity search
CREATE OR REPLACE FUNCTION match_macbook_facts(
    query_embedding vector(1536),
    match_threshold float,
    match_count int
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    metadata JSONB,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        macbook_facts.id,
        macbook_facts.content,
        macbook_facts.metadata,
        1 - (macbook_facts.embedding <=> query_embedding) AS similarity
    FROM macbook_facts
    WHERE 1 - (macbook_facts.embedding <=> query_embedding) > match_threshold
    ORDER BY macbook_facts.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
```

#### Populate Initial Data

You can populate the `macbook_facts` table using the provided script that crawls official sources:

```bash
python scripts/populate_facts.py
```

This script will:
1. **Crawl official sources**: Automatically fetches content from:
   - Apple's official MacBook Air pages
   - Apple Support technical specifications
   - Wikipedia (for general information)
2. **Extract facts**: Uses GPT-4o-mini to extract relevant facts from the crawled content
3. **Generate embeddings**: Creates vector embeddings for each fact
4. **Store in Supabase**: Inserts facts with metadata into your database

The script includes:
- Automatic deduplication of facts
- Rate limiting to respect API limits
- Error handling and progress reporting
- Source attribution in metadata

**Note**: The script uses OpenAI's API for fact extraction, so ensure your `OPENAI_API_KEY` is set in your `.env` file.

Alternatively, you can manually insert facts through the Supabase dashboard. Each fact needs:
- `content`: The fact text
- `embedding`: Vector embedding (1536 dimensions for text-embedding-3-small)
- `metadata`: JSON metadata (optional)

Example fact structure:
```json
{
  "content": "The MacBook Air M3 features an 8-core CPU and up to 10-core GPU, with support for up to 24GB unified memory.",
  "metadata": {
    "source": "Apple Official",
    "url": "https://www.apple.com/macbook-air-13-and-15-m3/",
    "model": "M3",
    "category": "specifications"
  }
}
```

## Running the Application

### Development

```bash
python -m app.main
```

Or with uvicorn directly:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production with Docker

```bash
# Build the image
docker build -t macbook-chatbot .

# Run the container
docker run -p 8000:8000 --env-file .env macbook-chatbot
```

## API Usage

### Health Check

```bash
curl http://localhost:8000/health
```

### Chat Endpoint (SSE)

```bash
curl -N -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the specifications of the MacBook Air M3?"}'
```

### JavaScript Example

```javascript
const eventSource = new EventSource('http://localhost:8000/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message: 'Tell me about MacBook Air battery life'
  })
});

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'content') {
    console.log(data.content);
  } else if (data.type === 'done') {
    eventSource.close();
  }
};
```

## Project Structure

```
agent/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── agent.py             # LangChain agent setup
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── web_search.py    # Web search tool
│   │   └── rag_tool.py      # RAG retrieval tool
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── supabase_client.py  # Supabase vector store client
│   │   └── embeddings.py    # Embedding generation
│   └── models/
│       ├── __init__.py
│       └── schemas.py        # Pydantic models
├── Dockerfile
├── pyproject.toml
├── .env.example
└── README.md
```

## Environment Variables

See `.env.example` for all required environment variables.

## Troubleshooting

### Agent Not Initializing

- Check that all environment variables are set correctly
- Verify OpenAI API key is valid
- Ensure Supabase credentials are correct

### RAG Search Not Working

- Verify pgvector extension is enabled in Supabase
- Check that the `match_macbook_facts` function exists
- Ensure the embedding dimension matches your model (1536 for text-embedding-3-small)

### Web Search Errors

- Verify your Brave Search API key is set correctly in `.env`
- Check that your API key is valid and has available quota
- Check internet connectivity
- Get your API key from https://brave.com/search/api/

## Code Quality

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and code formatting.

### Running Ruff

```bash
# Check for linting issues
make lint
# or
ruff check .

# Format code
make format
# or
ruff format .

# Auto-fix issues
make fix
# or
ruff check --fix .
ruff format .
```

### Pre-commit Checks

Before committing, run:
```bash
make check
```

This will verify that your code passes all linting and formatting checks.

## License

MIT
