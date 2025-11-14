# MacBook Air Chatbot

A full-stack AI chatbot application that provides intelligent answers about MacBook Air products. The application combines a FastAPI backend with LangChain agents, RAG (Retrieval Augmented Generation), web search capabilities, and a modern Next.js frontend with real-time streaming.

## 🚀 Features

### Core Functionality
- **Intelligent Chat Agent**: LangChain-powered agent that orchestrates multiple tools to provide comprehensive answers
- **RAG Integration**: Retrieves relevant facts from a Supabase vector database for accurate information
- **Real-time Web Search**: Uses Brave Search API to fetch current information from the web
- **Streaming Responses**: Server-Sent Events (SSE) for real-time message streaming
- **Conversation History**: Persistent conversation storage with Supabase
- **Tool Call Visualization**: Displays tool calls and their results in a collapsible UI

### Frontend Features
- **Modern UI**: Beautiful dark mode interface with Apple-inspired liquid glass design
- **Real-time Updates**: Live message streaming with loading indicators
- **Markdown Support**: Rich text rendering for assistant responses
- **Prompt Suggestions**: LLM-generated prompt suggestions based on conversation history
- **Mobile Responsive**: Optimized for both desktop and mobile devices
- **State Management**: Zustand store for efficient state management

### Backend Features
- **Modular Architecture**: Clean separation of services, routes, and utilities
- **Background Processing**: Ensures complete message saving even if client disconnects
- **Incremental Saves**: Periodic saves during streaming to prevent data loss
- **Tool Call Tracking**: Prevents duplicate tool call saves
- **Error Handling**: Robust error handling with graceful degradation

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11+** (for backend)
- **Node.js 18+** and **npm** (for frontend)
- **OpenAI API Key** ([Get one here](https://platform.openai.com/api-keys))
- **Brave Search API Key** ([Get one here](https://brave.com/search/api/))
- **Supabase Project** with:
  - PostgreSQL database with `pgvector` extension
  - Service role key for backend access

## 🏗️ Architecture

The application consists of two main components:

1. **Backend (FastAPI)**: Located in `agent/`
   - LangChain agent orchestrates tool usage
   - RAG tool for retrieving stored facts
   - Web search tool for current information
   - Conversation history management
   - SSE streaming for real-time responses

2. **Frontend (Next.js)**: Located in `frontend/`
   - React components with Ant Design X
   - Zustand for state management
   - Real-time SSE consumption
   - Conversation history polling

## 🛠️ Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd chatbotmac
```

### 2. Backend Setup

#### Navigate to the agent directory

```bash
cd agent
```

#### Install Dependencies

```bash
pip install -e .
# Or with development dependencies
pip install -e ".[dev]"
```

#### Configure Environment Variables

Create a `.env` file in the `agent/` directory:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# OpenAI API
OPENAI_API_KEY=your_openai_api_key_here

# Supabase
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_service_role_key

# Brave Search API
BRAVE_API_KEY=your_brave_search_api_key
```

#### Set Up Supabase Database

1. **Enable pgvector extension** in your Supabase SQL editor:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

2. **Create the MacBook facts table** (see `agent/README.md` for full SQL)

3. **Run the conversation history migration**:

```sql
-- Run the SQL from agent/migrations/001_create_conversations_tables.sql
-- This creates conversations, messages, and tool_calls tables
```

4. **(Optional) Populate initial facts**:

```bash
python scripts/populate_facts.py
```

### 3. Frontend Setup

#### Navigate to the frontend directory

```bash
cd ../frontend
```

#### Install Dependencies

```bash
npm install
```

#### Configure Environment Variables

Create a `.env.local` file in the `frontend/` directory:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 🚀 Running the Application

### Development Mode

#### Terminal 1: Start the Backend

```bash
cd agent
python -m app.main
# Or with uvicorn directly:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at `http://localhost:8000`

#### Terminal 2: Start the Frontend

```bash
cd frontend
npm run dev
```

The frontend will be available at `http://localhost:3000`

### Production Mode

#### Backend with Docker

```bash
cd agent
docker build -t macbook-chatbot .
docker run -p 8000:8000 --env-file .env macbook-chatbot
```

#### Frontend

```bash
cd frontend
npm run build
npm start
```

## 📁 Project Structure

```
chatbotmac/
├── agent/                          # Backend FastAPI application
│   ├── app/
│   │   ├── main.py                 # FastAPI app initialization
│   │   ├── agent.py                # LangChain agent setup
│   │   ├── models/                 # Pydantic models
│   │   │   ├── schemas.py          # API request/response models
│   │   │   └── database.py         # Database models
│   │   ├── routes/                 # API route handlers
│   │   │   ├── chat.py             # Chat streaming endpoint
│   │   │   ├── conversations.py    # Conversation management
│   │   │   ├── suggestions.py      # Prompt suggestions
│   │   │   └── health.py           # Health check endpoint
│   │   ├── services/               # Business logic services
│   │   │   ├── chat_service.py     # Chat streaming service
│   │   │   ├── conversation_service.py  # Conversation CRUD
│   │   │   └── suggestion_service.py   # LLM suggestions
│   │   ├── tools/                  # LangChain tools
│   │   │   ├── rag_tool.py         # RAG retrieval tool
│   │   │   └── web_search.py       # Web search tool
│   │   ├── rag/                    # RAG implementation
│   │   │   ├── supabase_client.py  # Supabase vector client
│   │   │   └── embeddings.py       # Embedding generation
│   │   └── utils/                  # Utility functions
│   │       └── message_formatter.py
│   ├── migrations/                 # Database migrations
│   │   └── 001_create_conversations_tables.sql
│   ├── scripts/                    # Utility scripts
│   │   └── populate_facts.py       # Populate facts script
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── README.md                   # Detailed backend docs
│
└── frontend/                       # Next.js frontend application
    ├── app/
    │   ├── page.tsx                # Main chat interface
    │   ├── layout.tsx              # Root layout
    │   ├── components/             # React components
    │   │   ├── MarkdownContent.tsx # Markdown renderer
    │   │   └── ToolCallDisplay.tsx # Tool call UI
    │   ├── hooks/                  # Custom React hooks
    │   │   ├── useChatAgent.ts     # SSE streaming hook
    │   │   ├── useConversationHistory.ts  # History loading
    │   │   ├── useMessageSync.ts   # Message synchronization
    │   │   ├── useSuggestions.ts   # Prompt suggestions
    │   │   └── useClearHistory.ts  # History clearing
    │   ├── store/                  # Zustand store
    │   │   └── chatStore.ts        # Chat state management
    │   ├── types/                  # TypeScript types
    │   │   └── chat.ts
    │   └── utils/                  # Utility functions
    │       ├── conversation.ts     # Conversation ID management
    │       └── sse.ts              # SSE parsing
    ├── package.json
    └── README.md                   # Frontend setup guide
```

## 🔧 Environment Variables

### Backend (`agent/.env`)

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for LLM and embeddings | Yes |
| `SUPABASE_URL` | Your Supabase project URL | Yes |
| `SUPABASE_KEY` | Supabase service role key | Yes |
| `BRAVE_API_KEY` | Brave Search API key | Yes |

### Frontend (`frontend/.env.local`)

| Variable | Description | Required |
|----------|-------------|----------|
| `NEXT_PUBLIC_API_URL` | Backend API URL (default: `http://localhost:8000`) | No |

## 📡 API Endpoints

### Backend Endpoints

- `GET /health` - Health check endpoint
- `POST /chat` - Chat streaming endpoint (SSE)
- `GET /conversations/{id}/history` - Get conversation history
- `DELETE /conversations/{id}` - Delete conversation
- `GET /suggestions` - Get prompt suggestions

See `agent/README.md` for detailed API documentation.

## 🎨 Key Features Explained

### Streaming Responses

The backend uses Server-Sent Events (SSE) to stream responses in real-time. The frontend consumes these events and updates the UI as content arrives.

### Conversation History

- Conversations are automatically saved to Supabase
- Each conversation has a unique ID stored in `localStorage`
- History persists across page refreshes
- Users can clear their conversation history

### Tool Call Visualization

When the agent uses tools (RAG search, web search), the frontend displays:
- Tool name and input parameters
- Loading state while tool executes
- Collapsible results display
- Tool calls are saved with messages

### Background Processing

The backend ensures complete message saving even if the client disconnects:
- Background task processes agent stream independently
- Incremental saves every 100 characters
- Final save when agent completes
- Tool calls saved incrementally as they complete

## 🐛 Troubleshooting

### Backend Issues

**Agent not initializing:**
- Verify all environment variables are set correctly
- Check OpenAI API key is valid
- Ensure Supabase credentials are correct

**RAG search not working:**
- Verify `pgvector` extension is enabled
- Check that the `match_macbook_facts` function exists
- Ensure embedding dimension matches (1536 for text-embedding-3-small)

**Web search errors:**
- Verify Brave Search API key is set correctly
- Check API key has available quota
- Verify internet connectivity

### Frontend Issues

**Messages not displaying:**
- Check that backend is running on the correct port
- Verify `NEXT_PUBLIC_API_URL` matches backend URL
- Check browser console for errors

**SSE connection issues:**
- Ensure backend CORS is configured correctly
- Check network tab for SSE connection status
- Verify backend is accessible from frontend

## 📚 Additional Documentation

- **Backend Details**: See `agent/README.md` for comprehensive backend documentation
- **Frontend Setup**: See `frontend/README.md` for frontend-specific setup

## 🧪 Development

### Code Quality

The backend uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
cd agent
make lint      # Check for issues
make format    # Format code
make fix       # Auto-fix issues
```

### Type Checking

The frontend uses TypeScript for type safety:

```bash
cd frontend
npm run build  # Type check and build
```

## 📝 License

MIT

