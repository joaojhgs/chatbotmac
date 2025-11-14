import { useEffect, useRef } from 'react';
import { useChatStore } from '../store/chatStore';
import { getConversationId } from '../utils/conversation';
import type { ApiMessage, ApiToolCall, ConversationHistoryResponse, ToolCall } from '../types/chat';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const POLL_INTERVAL = 2000; // Poll every 2 seconds for updates
const POLL_DURATION = 30000; // Stop polling after 30 seconds

/**
 * Hook to load conversation history on mount and when conversation ID changes.
 * Also polls for updates to detect when backend finishes saving final messages.
 */
export function useConversationHistory() {
  const {
    conversationId,
    setConversationId,
    setMessages,
    setToolCallsForMessage,
    setIsLoadingHistory,
  } = useChatStore();
  
  // Track the last loaded conversation ID to prevent reloading the same conversation
  const lastLoadedIdRef = useRef<string | null>(null);
  const pollTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pollStartTimeRef = useRef<number | null>(null);
  const lastContentLengthRef = useRef<number>(0); // Track last content length to detect if still updating
  const noChangeCountRef = useRef<number>(0); // Count consecutive polls with no change

  const loadHistory = async (isPolling = false) => {
    // Use conversationId from store if available, otherwise get from localStorage
    const convId = conversationId || getConversationId();
    
    // Skip if we've already loaded this conversation ID (unless polling)
    if (!isPolling && lastLoadedIdRef.current === convId) {
      return;
    }
    
    // Update store with conversation ID if it wasn't already set
    if (!conversationId) {
      setConversationId(convId);
    }
    
    if (!isPolling) {
      setIsLoadingHistory(true);
      lastLoadedIdRef.current = convId;
    }

    try {
      const response = await fetch(`${API_URL}/conversations/${convId}/history`);
      if (response.ok) {
        const data = (await response.json()) as ConversationHistoryResponse;
        if (data.messages && data.messages.length > 0) {
          // Convert history messages to store format
          const historyMessages = data.messages.map((msg: ApiMessage) => ({
            id: msg.id,
            role: msg.role,
            content: msg.content,
            status: 'done' as const,
            timestamp: new Date(msg.created_at).getTime(),
            isPolling: false as boolean | undefined,
          }));

          // Check if messages have changed (for polling)
          if (isPolling) {
            const currentMessages = useChatStore.getState().messages;
            const lastCurrentMsg = currentMessages[currentMessages.length - 1];
            const lastHistoryMsg = historyMessages[historyMessages.length - 1];
            
            // Check if content changed (message was updated)
            const contentChanged = lastCurrentMsg && lastHistoryMsg && 
              String(lastCurrentMsg.id) === String(lastHistoryMsg.id) &&
              lastCurrentMsg.content !== lastHistoryMsg.content;
            
            // Check if new message was added
            const newMessageAdded = historyMessages.length > currentMessages.length;
            
            // Check if content length increased (message is still growing)
            const currentContentLength = lastHistoryMsg ? lastHistoryMsg.content.length : 0;
            const contentLengthIncreased = currentContentLength > lastContentLengthRef.current;
            lastContentLengthRef.current = currentContentLength;
            
            // Message is still updating if content changed OR content length increased
            const isStillUpdating = contentChanged || contentLengthIncreased;
            
            // Only update if something changed
            if (contentChanged || newMessageAdded || contentLengthIncreased) {
              // Reset no-change counter if content changed
              if (contentChanged || contentLengthIncreased) {
                noChangeCountRef.current = 0;
              }
              
              // Merge with existing messages to preserve isPolling state
              const existingMessages = useChatStore.getState().messages;
              const mergedMessages = historyMessages.map((historyMsg, idx) => {
                const existingMsg = existingMessages.find(m => String(m.id) === String(historyMsg.id));
                // Preserve isPolling if it was already set, or set it if content is still updating
                const shouldBePolling = (isStillUpdating && idx === historyMessages.length - 1) || existingMsg?.isPolling === true;
                return {
                  ...historyMsg,
                  isPolling: shouldBePolling ? true : undefined,
                };
              });
              
              setMessages(mergedMessages);
              
              // Update tool calls
              data.messages.forEach((msg: ApiMessage) => {
                if (msg.tool_calls && msg.tool_calls.length > 0) {
                  const toolCalls: ToolCall[] = msg.tool_calls.map((tc: ApiToolCall) => ({
                    id: tc.id,
                    tool: tc.tool_name,
                    input: (tc.input || {}) as Record<string, unknown>,
                    result: tc.result || undefined,
                    timestamp: new Date(tc.created_at).getTime(),
                  }));
                  setToolCallsForMessage(msg.id, toolCalls);
                }
              });
              
              // Continue polling if still updating
              // Don't stop yet
            } else {
              // Content didn't change - increment no-change counter
              noChangeCountRef.current += 1;
              
              // Stop polling only after 3 consecutive polls with no change (6 seconds)
              // This ensures the message is truly complete
              if (noChangeCountRef.current >= 3) {
                // Content stopped changing for 3 polls, message is complete - stop polling
                // Also mark the message as not polling anymore
                const updatedMessages = useChatStore.getState().messages.map((msg, idx) => 
                  idx === useChatStore.getState().messages.length - 1 
                    ? { ...msg, isPolling: false }
                    : msg
                );
                setMessages(updatedMessages);
                
                if (pollTimeoutRef.current) {
                  clearTimeout(pollTimeoutRef.current);
                  pollTimeoutRef.current = null;
                }
                pollStartTimeRef.current = null;
                noChangeCountRef.current = 0;
                lastContentLengthRef.current = 0;
              }
            }
          } else {
            // Initial load - always set messages
            setMessages(historyMessages);

            // Load tool calls for each message
            data.messages.forEach((msg: ApiMessage) => {
              if (msg.tool_calls && msg.tool_calls.length > 0) {
                const toolCalls: ToolCall[] = msg.tool_calls.map((tc: ApiToolCall) => ({
                  id: tc.id,
                  tool: tc.tool_name,
                  input: (tc.input || {}) as Record<string, unknown>,
                  result: tc.result || undefined,
                  timestamp: new Date(tc.created_at).getTime(),
                }));
                setToolCallsForMessage(msg.id, toolCalls);
              }
            });
            
            // Start polling if we have recent messages (within last 30 seconds)
            // Check the last message's timestamp
            if (historyMessages.length > 0) {
              const lastMsg = historyMessages[historyMessages.length - 1];
              const now = Date.now();
              const msgTime = lastMsg.timestamp || now;
              const isRecent = now - msgTime < POLL_DURATION;
              
              if (isRecent) {
                pollStartTimeRef.current = now;
                lastContentLengthRef.current = lastMsg.content.length;
                noChangeCountRef.current = 0;
                startPolling(convId);
              }
            }
          }
        } else {
          // No messages found, clear the store
          if (!isPolling) {
            setMessages([]);
          }
        }
      } else if (response.status === 404) {
        // Conversation doesn't exist, clear the store
        if (!isPolling) {
          setMessages([]);
        }
      }
    } catch (error) {
      console.error('Failed to load conversation history:', error);
    } finally {
      if (!isPolling) {
        setIsLoadingHistory(false);
      }
    }
  };

  const startPolling = (convId: string) => {
    // Clear any existing polling
    if (pollTimeoutRef.current) {
      clearTimeout(pollTimeoutRef.current);
    }
    
    const poll = () => {
      const now = Date.now();
      // Stop polling if we've exceeded the duration
      if (pollStartTimeRef.current && now - pollStartTimeRef.current > POLL_DURATION) {
        pollTimeoutRef.current = null;
        pollStartTimeRef.current = null;
        return;
      }
      
      // Poll for updates
      loadHistory(true);
      
      // Schedule next poll
      pollTimeoutRef.current = setTimeout(poll, POLL_INTERVAL);
    };
    
    pollTimeoutRef.current = setTimeout(poll, POLL_INTERVAL);
  };

  useEffect(() => {
    loadHistory(false);
    
    // Cleanup polling on unmount
    return () => {
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current);
        pollTimeoutRef.current = null;
      }
      pollStartTimeRef.current = null;
      lastContentLengthRef.current = 0;
      noChangeCountRef.current = 0;
    };
  }, [conversationId, setConversationId, setMessages, setToolCallsForMessage, setIsLoadingHistory]);
}

