# Quick Start Guide

Get your MacBook Air chatbot up and running in minutes!

## Prerequisites Checklist

- [ ] Python 3.11+ installed
- [ ] OpenAI API key (get from https://platform.openai.com/api-keys)
- [ ] Supabase account and project (create at https://supabase.com)

## Step-by-Step Setup

### 1. Install Dependencies

```bash
cd agent
# Install the package and all dependencies
pip install -e .

# Or with development dependencies (includes ruff)
pip install -e ".[dev]"
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:
- `OPENAI_API_KEY`: Your OpenAI API key
- `SUPABASE_URL`: Your Supabase project URL (found in Project Settings > API)
- `SUPABASE_KEY`: Your Supabase service role key (found in Project Settings > API)

### 3. Set Up Supabase Database

1. Go to your Supabase project dashboard
2. Navigate to SQL Editor
3. Copy and paste the contents of `supabase_setup.sql`
4. Run the SQL script

This will:
- Enable the pgvector extension
- Create the `macbook_facts` table
- Create the similarity search function
- Set up necessary indexes

### 4. Populate Initial Facts

```bash
python scripts/populate_facts.py
```

This will add 15 sample MacBook Air facts to your database.

### 5. Start the Server

```bash
python -m app.main
```

Or with uvicorn:

```bash
uvicorn app.main:app --reload
```

The server will start on `http://localhost:8000`

### 6. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Test chat (SSE)
curl -N -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the specifications of the MacBook Air M3?"}'
```

## Docker Quick Start

```bash
# Build
docker build -t macbook-chatbot .

# Run
docker run -p 8000:8000 --env-file .env macbook-chatbot
```

## Troubleshooting

### "Agent not initialized" error
- Check that all environment variables are set correctly
- Verify your OpenAI API key is valid
- Check server logs for detailed error messages

### RAG search not working
- Verify the `match_macbook_facts` function exists in Supabase
- Check that you've populated some facts
- Ensure pgvector extension is enabled

### Import errors
- Make sure you're running from the `agent` directory
- Verify all dependencies are installed: `pip install -r requirements.txt`

## Next Steps

- Add more MacBook Air facts to improve responses
- Customize the system prompt in `app/agent.py`
- Add conversation history/memory
- Deploy to production (see README.md for deployment options)

## Need Help?

- Check the full [README.md](README.md) for detailed documentation
- Review [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for architecture details
- Check server logs for error messages


