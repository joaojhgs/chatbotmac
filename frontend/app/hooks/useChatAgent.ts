import React, { useRef } from 'react';
import { useXAgent } from '@ant-design/x';
import { parseSSEStream } from '../utils/sse';
import { useChatStore } from '../store/chatStore';
import { getConversationId, saveConversationId } from '../utils/conversation';
import type { SSEMessage } from '../utils/sse';
import type { ToolCall } from '../types/chat';
import type { SSEOutput } from '@ant-design/x/es/x-stream';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Hook to create and manage the chat agent with SSE streaming support
 */
export function useChatAgent() {
  const currentAssistantMessageIdRef = useRef<string | number | null>(null);
  const hasContentForCurrentMessageRef = useRef(false);
  const [hasContent, setHasContent] = React.useState(false);

  const {
    conversationId,
    setConversationId,
    setIsRequesting,
    addMessage,
    addToolCall,
    updateToolCall,
  } = useChatStore();

  const [agent] = useXAgent({
    request: async (info: { message: string }, callbacks: { onSuccess: (output: SSEOutput[]) => void; onUpdate: (output: SSEOutput) => void; onError: (error: Error) => void }) => {
      const { message } = info;
      const { onSuccess, onUpdate, onError } = callbacks;

      setIsRequesting(true);
      hasContentForCurrentMessageRef.current = false;
      setHasContent(false);

      // Always use conversationId from store (single source of truth)
      // Only fall back to localStorage if store is null (shouldn't happen after initial load)
      const convId = conversationId || getConversationId();
      
      // Sync to store if needed (shouldn't happen after initial load)
      if (!conversationId && convId) {
        setConversationId(convId);
      }
      
      // Ensure we're using the store's conversationId, not a stale localStorage value
      // This prevents using old IDs after clearing history
      const currentStoreId = useChatStore.getState().conversationId;
      const finalConvId = currentStoreId || convId;

      // Create assistant message immediately with loading state
      // This ensures the message bubble appears before content arrives
      const assistantMessageId = `assistant-${Date.now()}-${Math.random()}`;
      currentAssistantMessageIdRef.current = assistantMessageId;
      addMessage({
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        status: 'loading',
      });

      let fullContent = '';

      try {
        const response = await fetch(`${API_URL}/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message,
            conversation_id: finalConvId,
          }),
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        // Parse SSE stream
        for await (const event of parseSSEStream(response)) {
          const sseEvent = event as SSEMessage;
          const currentMessageId = currentAssistantMessageIdRef.current;

          switch (sseEvent.type) {
            case 'conversation_id':
              // Always update conversation ID from SSE to keep in sync with backend
              // But only if it's different from what we have
              if (sseEvent.conversation_id) {
                const currentStoreId = useChatStore.getState().conversationId;
                if (sseEvent.conversation_id !== currentStoreId) {
                  setConversationId(sseEvent.conversation_id);
                  saveConversationId(sseEvent.conversation_id);
                }
              }
              break;

            case 'content_delta':
              if (sseEvent.content) {
                fullContent += sseEvent.content;
                hasContentForCurrentMessageRef.current = true;
                setHasContent(true);
                onUpdate({ data: fullContent } as SSEOutput);
              }
              break;

            case 'tool_call':
              if (sseEvent.tool && currentMessageId) {
                const toolCallId = `${sseEvent.tool}-${Date.now()}`;
                const toolCall: ToolCall = {
                  id: toolCallId,
                  tool: sseEvent.tool,
                  input: (sseEvent.input || {}) as Record<string, unknown>,
                  timestamp: Date.now(),
                };
                addToolCall(currentMessageId, toolCall);
              }
              break;

            case 'tool_result':
              if (sseEvent.tool && sseEvent.result && currentMessageId) {
                // Get current tool calls from store state (not selector) to get latest state
                const currentState = useChatStore.getState();
                const toolCalls = currentState.toolCallsByMessageId.get(String(currentMessageId)) || [];
                const toolCall = toolCalls.find(
                  (tc) => tc.tool === sseEvent.tool && !tc.result
                );
                if (toolCall) {
                  updateToolCall(currentMessageId, toolCall.id, sseEvent.result);
                }
              }
              break;

            case 'content':
              if (sseEvent.content) {
                fullContent = sseEvent.content;
                hasContentForCurrentMessageRef.current = true;
                setHasContent(true);
                onUpdate({ data: fullContent } as SSEOutput);
              }
              break;

            case 'done':
              setIsRequesting(false);
              currentAssistantMessageIdRef.current = null;
              onSuccess([{ data: fullContent }] as SSEOutput[]);
              break;

            case 'error':
              setIsRequesting(false);
              currentAssistantMessageIdRef.current = null;
              onError(new Error(sseEvent.message || 'Unknown error'));
              break;
          }
        }
      } catch (error) {
        console.error('Chat request failed:', error);
        setIsRequesting(false);
        currentAssistantMessageIdRef.current = null;
        onError(error as Error);
      }
    },
  });

  return {
    agent,
    currentAssistantMessageIdRef,
    hasContentForCurrentMessageRef,
    hasContent,
  };
}

