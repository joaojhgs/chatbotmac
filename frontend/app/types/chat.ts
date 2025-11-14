// Types for chat messages and SSE events

export interface SSEMessage {
  type: 'content_delta' | 'tool_call' | 'tool_result' | 'content' | 'done' | 'error' | 'conversation_id';
  content?: string;
  tool?: string;
  input?: Record<string, unknown>;
  result?: string;
  message?: string;
  traceback?: string;
  conversation_id?: string;
}

export interface ToolCall {
  id: string;
  tool: string;
  input: Record<string, unknown>;
  result?: string;
  timestamp: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  toolCalls?: ToolCall[];
  loading?: boolean;
  error?: string;
}

// API Response Types
export interface ApiToolCall {
  id: string;
  tool_name: string;
  input: Record<string, unknown> | null;
  result: string | null;
  created_at: string;
}

export interface ApiMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  tool_calls: ApiToolCall[];
}

export interface ConversationHistoryResponse {
  messages: ApiMessage[];
}

export interface SuggestionsResponse {
  suggestions: string[];
}

