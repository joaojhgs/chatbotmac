// Types for chat messages and SSE events

export interface SSEMessage {
  type: 'content_delta' | 'tool_call' | 'tool_result' | 'content' | 'done' | 'error';
  content?: string;
  tool?: string;
  input?: unknown;
  result?: string;
  message?: string;
  traceback?: string;
}

export interface ToolCall {
  id: string;
  tool: string;
  input: unknown;
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

