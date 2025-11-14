// SSE streaming utility for handling backend events

export interface SSEMessage {
  type: 'content_delta' | 'tool_call' | 'tool_result' | 'content' | 'done' | 'error';
  content?: string;
  tool?: string;
  input?: unknown;
  result?: string;
  message?: string;
  traceback?: string;
}

export async function* parseSSEStream(
  response: Response
): AsyncGenerator<SSEMessage, void, unknown> {
  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  if (!reader) {
    throw new Error('Response body is not readable');
  }

  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            yield data;
          } catch {
            // Skip invalid JSON
            console.warn('Failed to parse SSE data:', line);
          }
        }
      }
    }

    // Process remaining buffer
    if (buffer.startsWith('data: ')) {
      try {
        const data = JSON.parse(buffer.slice(6));
        yield data;
      } catch {
        console.warn('Failed to parse remaining SSE data:', buffer);
      }
    }
  } finally {
    reader.releaseLock();
  }
}

