'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useXAgent, useXChat, Sender, Bubble, Prompts } from '@ant-design/x';
import { ConfigProvider, Flex, theme, Button } from 'antd';
import { RobotOutlined, UserOutlined, DeleteOutlined } from '@ant-design/icons';
import { ToolCallDisplay } from './components/ToolCallDisplay';
import { MarkdownContent } from './components/MarkdownContent';
import { parseSSEStream } from './utils/sse';
import type { SSEMessage } from './utils/sse';
import type { ToolCall } from './types/chat';
import type { GetProp } from 'antd';
import { useChatStore } from './store/chatStore';
import {
  getConversationId,
  saveConversationId,
  clearConversationId,
  generateConversationId,
} from './utils/conversation';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function Home() {
  const [inputValue, setInputValue] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);

  const [showSuggestions, setShowSuggestions] = useState(true); // Show by default
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const promptsContainerRef = useRef<HTMLDivElement>(null);
  const currentAssistantMessageIdRef = useRef<string | number | null>(null);
  const hasContentForCurrentMessageRef = useRef(false);

  // Zustand store
  const {
    conversationId,
    messages: storeMessages,
    toolCallsByMessageId,
    isLoadingHistory,
    isRequesting,
    setConversationId,
    addMessage,
    updateMessage,
    addToolCall,
    updateToolCall,
    setMessages,
    setToolCallsForMessage,
    setIsLoadingHistory,
    setIsRequesting,
    clearConversation,
  } = useChatStore();

  // Load conversation history on mount
  useEffect(() => {
    const loadHistory = async () => {
      const convId = getConversationId();
      setConversationId(convId);
      setIsLoadingHistory(true);

      try {
        const response = await fetch(`${API_URL}/conversations/${convId}/history`);
        if (response.ok) {
          const data = await response.json();
          if (data.messages && data.messages.length > 0) {
            // Convert history messages to store format
            const historyMessages = data.messages.map((msg: any) => ({
              id: msg.id,
              role: msg.role,
              content: msg.content,
              status: 'done' as const,
              timestamp: new Date(msg.created_at).getTime(),
            }));

            setMessages(historyMessages);

            // Load tool calls for each message
            data.messages.forEach((msg: any) => {
              if (msg.tool_calls && msg.tool_calls.length > 0) {
                const toolCalls: ToolCall[] = msg.tool_calls.map((tc: any) => ({
                  id: tc.id,
                  tool: tc.tool_name,
                  input: tc.input || {},
                  result: tc.result || undefined,
                  timestamp: new Date(tc.created_at).getTime(),
                }));
                setToolCallsForMessage(msg.id, toolCalls);
              }
            });
          }
        }
      } catch (error) {
        console.error('Failed to load conversation history:', error);
      } finally {
        setIsLoadingHistory(false);
      }
    };

    loadHistory();
  }, [setConversationId, setMessages, setToolCallsForMessage, setIsLoadingHistory]);

  // Load prompt suggestions from API
  useEffect(() => {
    const loadSuggestions = async () => {
      // Always use API endpoint, even when there's no conversation
      if (!conversationId || isRequesting) {
        return;
      }

      try {
        const response = await fetch(`${API_URL}/conversations/${conversationId}/suggestions`);
        if (response.ok) {
          const data = await response.json();
          setSuggestions(data.suggestions || []);
          setShowSuggestions(true);
        } else {
          console.error('Failed to load suggestions:', response.statusText);
          setSuggestions([]);
        }
      } catch (error) {
        console.error('Failed to load suggestions:', error);
        setSuggestions([]);
      }
    };

    loadSuggestions();
  }, [conversationId, isRequesting]);

  // Create agent with SSE streaming support
  const [agent] = useXAgent({
    request: async (info, callbacks) => {
      const { message } = info;
      const { onSuccess, onUpdate, onError } = callbacks;

      setIsRequesting(true);
      hasContentForCurrentMessageRef.current = false;

      // Get or use current conversation ID
      const convId = conversationId || getConversationId();
      if (!conversationId) {
        setConversationId(convId);
      }

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
            conversation_id: convId,
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
              if (sseEvent.conversation_id) {
                setConversationId(sseEvent.conversation_id);
                saveConversationId(sseEvent.conversation_id);
              }
              break;

            case 'content_delta':
              if (sseEvent.content) {
                fullContent += sseEvent.content;
                hasContentForCurrentMessageRef.current = true;
                onUpdate(fullContent as any);
                // Don't update store here - let useXChat handle it via onUpdate
              }
              break;

            case 'tool_call':
              if (sseEvent.tool && currentMessageId) {
                const toolCallId = `${sseEvent.tool}-${Date.now()}`;
                const toolCall: ToolCall = {
                  id: toolCallId,
                  tool: sseEvent.tool,
                  input: sseEvent.input || {},
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
                onUpdate(fullContent as any);
                // Don't update store here - let useXChat handle it via onUpdate
              }
              break;

            case 'done':
              setIsRequesting(false);
              // Don't update message here - useXChat will handle it via onSuccess
              currentAssistantMessageIdRef.current = null;
              onSuccess([fullContent] as any);
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

  // Manage chat state with useXChat
  const { onRequest, messages: xChatMessages } = useXChat({ agent });

  // Sync useXChat messages with Zustand store - prevent duplicates
  useEffect(() => {
    // Track messages we've processed in this effect run to prevent duplicates
    const processedIds = new Set<string>();
    
    xChatMessages.forEach((xMsg) => {
      const msgIdStr = String(xMsg.id);
      
      // Skip if we've already processed this message in this effect run
      if (processedIds.has(msgIdStr)) {
        return;
      }
      processedIds.add(msgIdStr);
      
      // Always get the latest store state for each message to avoid race conditions
      const currentStoreMessages = useChatStore.getState().messages;
      const existingMsg = currentStoreMessages.find((m) => String(m.id) === msgIdStr);
      
      if (!existingMsg) {
        // Add new message only if it doesn't exist in store
        const isUser = xMsg.status === 'local';
        
        // For assistant messages, check if we have a loading message to replace
        if (!isUser && currentAssistantMessageIdRef.current) {
          const loadingMsgId = String(currentAssistantMessageIdRef.current);
          const loadingMsg = currentStoreMessages.find((m) => String(m.id) === loadingMsgId && m.status === 'loading');
          
          if (loadingMsg) {
            // Replace the loading message with useXChat's message (same content, but use useXChat's ID)
            // First, get any tool calls associated with the old message
            const currentState = useChatStore.getState();
            const oldToolCalls = currentState.toolCallsByMessageId.get(loadingMsgId) || [];
            
            // Remove the old message and add the new one
            const updatedMessages = currentStoreMessages.filter((m) => String(m.id) !== loadingMsgId);
            updatedMessages.push({
              id: xMsg.id,
              role: 'assistant',
              content: xMsg.message,
              status: xMsg.status === 'loading' ? 'loading' : 'done',
            });
            
            // Update messages and migrate tool calls to new message ID
            useChatStore.getState().setMessages(updatedMessages);
            if (oldToolCalls.length > 0) {
              const newMap = new Map(currentState.toolCallsByMessageId);
              newMap.delete(loadingMsgId);
              newMap.set(String(xMsg.id), oldToolCalls);
              useChatStore.setState({ toolCallsByMessageId: newMap });
            }
            
            // Update the ref to use the new ID
            currentAssistantMessageIdRef.current = xMsg.id;
            return; // Skip adding a new message
          }
        }
        
        addMessage({
          id: xMsg.id,
          role: isUser ? 'user' : 'assistant',
          content: xMsg.message,
          status: xMsg.status === 'local' ? 'local' : xMsg.status === 'loading' ? 'loading' : 'done',
        });

        // Track assistant message ID for tool calls
        if (!isUser && xMsg.status === 'loading') {
          currentAssistantMessageIdRef.current = xMsg.id;
        }
      } else {
        // Only update if content or status actually changed
        const contentChanged = existingMsg.content !== xMsg.message;
        const newStatus = xMsg.status === 'local' ? 'local' : xMsg.status === 'loading' ? 'loading' : 'done';
        const statusChanged = existingMsg.status !== newStatus;
        
        if (contentChanged || statusChanged) {
          updateMessage(xMsg.id, {
            content: xMsg.message,
            status: newStatus,
          });
        }
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [xChatMessages]); // Only depend on xChatMessages to avoid infinite loop

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [storeMessages]);

  // Clear conversation handler
  const handleClearHistory = async () => {
    if (conversationId) {
      try {
        await fetch(`${API_URL}/conversations/${conversationId}`, {
          method: 'DELETE',
        });
      } catch (error) {
        console.error('Failed to delete conversation:', error);
      }
    }
    clearConversationId();
    clearConversation();
    const newId = generateConversationId();
    setConversationId(newId);
    saveConversationId(newId);
  };

  const roles: GetProp<typeof Bubble.List, 'roles'> = {
    ai: {
      placement: 'start',
      avatar: {
        icon: <RobotOutlined />,
        style: {
          background: 'linear-gradient(135deg, rgba(120, 119, 198, 0.4) 0%, rgba(118, 75, 162, 0.4) 100%)',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(255, 255, 255, 0.2)',
          boxShadow: '0 4px 16px rgba(120, 119, 198, 0.2)',
        },
      },
    },
    user: {
      placement: 'end',
      avatar: {
        icon: <UserOutlined />,
        style: {
          background: 'linear-gradient(135deg, rgba(240, 147, 251, 0.4) 0%, rgba(245, 87, 108, 0.4) 100%)',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(255, 255, 255, 0.2)',
          boxShadow: '0 4px 16px rgba(240, 147, 251, 0.2)',
        },
      },
    },
  };

  // Get tool calls for a message
  const getToolCallsForMessage = (messageId: string | number): ToolCall[] => {
    return toolCallsByMessageId.get(String(messageId)) || [];
  };

  return (
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorBgBase: '#0a0a0a',
          colorTextBase: '#ededed',
          borderRadius: 12,
        },
      }}
    >
      <Flex
        vertical
        className="h-screen w-full relative"
        style={{
          overflow: 'hidden',
          background: 'linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 25%, #16213e 50%, #0f3460 75%, #0a0a0a 100%)',
        }}
      >
        {/* Animated background gradient overlay */}
        <div
          className="absolute inset-0 opacity-30"
          style={{
            background:
              'radial-gradient(circle at 20% 50%, rgba(120, 119, 198, 0.3) 0%, transparent 50%), radial-gradient(circle at 80% 80%, rgba(255, 119, 198, 0.2) 0%, transparent 50%)',
            animation: 'pulse 15s ease-in-out infinite',
          }}
        />

        {/* Header */}
        <div className="glass-dark border-b border-white/10 px-6 py-3 relative z-10">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="m-0 text-xl font-semibold text-white/95 tracking-tight">
                MacBook Air Chatbot
              </h1>
              <p className="m-0 mt-1.5 text-sm text-white/60 font-light">
                Ask me anything about MacBook Air
              </p>
            </div>
            {storeMessages.length > 0 && (
              <Button
                icon={<DeleteOutlined />}
                onClick={handleClearHistory}
                className="glass border-white/20 text-white/80 hover:text-white hover:border-white/40"
              >
                Clear History
              </Button>
            )}
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto px-6 py-8 relative z-10">
          <div className="mx-auto max-w-4xl">
            {isLoadingHistory ? (
              <div className="flex h-full items-center justify-center min-h-[60vh]">
                <div className="text-white/60">Loading conversation history...</div>
              </div>
            ) : storeMessages.length === 0 ? (
              <div className="flex h-full items-center justify-center min-h-[60vh]">
                <div className="text-center">
                  <div className="mb-6 inline-flex items-center justify-center w-20 h-20 rounded-full glass-strong border border-white/20">
                    <RobotOutlined className="text-4xl text-white/80" />
                  </div>
                  <h2 className="mb-3 text-3xl font-semibold text-white/95 tracking-tight">
                    Welcome to MacBook Air Chatbot
                  </h2>
                </div>
              </div>
            ) : (
              <div>
                {storeMessages.map((msg, index) => {
                  const isUser = msg.role === 'user';
                  const toolCalls = getToolCallsForMessage(msg.id);
                  const isLoading = !isUser && msg.status === 'loading' && !hasContentForCurrentMessageRef.current;
                  
                  // Check if previous message was also a user message
                  const prevMsg = index > 0 ? storeMessages[index - 1] : null;
                  const isConsecutiveUserMessage = isUser && prevMsg?.role === 'user';
                  
                  // Larger spacing on mobile for consecutive user messages
                  const spacingClass = isConsecutiveUserMessage 
                    ? 'mb-8 md:mb-4' 
                    : 'mb-4';

                  return (
                    <div key={String(msg.id)} className={spacingClass}>
                      <Bubble
                        content={
                          isUser ? (
                            msg.content
                          ) : (
                            <MarkdownContent content={msg.content} />
                          )
                        }
                        placement={isUser ? 'end' : 'start'}
                        avatar={isUser ? roles.user?.avatar : roles.ai?.avatar}
                        loading={isLoading}
                      />
                      {!isUser && toolCalls.length > 0 && (
                        <div className="ml-12 mt-2 space-y-2">
                          {toolCalls.map((toolCall) => (
                            <ToolCallDisplay key={toolCall.id} toolCall={toolCall} />
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Area */}
        <div className="glass-dark border-t border-white/10 px-6 py-3 relative z-10">
          <div className="mx-auto max-w-4xl space-y-3">
            {/* Prompt Suggestions */}
            {showSuggestions && suggestions.length > 0 && (
              <div 
                ref={promptsContainerRef}
                className="prompts-container"
                onWheel={(e) => {
                  if (promptsContainerRef.current) {
                    const { scrollTop, scrollHeight, clientHeight } = promptsContainerRef.current;
                    const isAtTop = scrollTop === 0;
                    const isAtBottom = scrollTop + clientHeight >= scrollHeight - 1;
                    if ((isAtTop && e.deltaY < 0) || (isAtBottom && e.deltaY > 0)) {
                      return;
                    }
                    e.stopPropagation();
                  }
                }}>
                <Prompts
                  items={suggestions.map((suggestion, index) => ({
                    key: String(index),
                    label: suggestion,
                  }))}
                  onItemClick={(item) => {
                    const label = String(item.data?.label || suggestions[Number(item.data?.key) || 0] || '');
                    if (label) {
                      onRequest(label);
                      setShowSuggestions(false);
                    }
                  }}
                />
              </div>
            )}

            {/* Input */}
            <div className="glass-strong rounded-2xl shadow-2xl overflow-hidden sender-container">
              <Sender
                value={inputValue}
                onChange={setInputValue}
                onSubmit={(text) => {
                  onRequest(text);
                  setInputValue('');
                  setShowSuggestions(false);
                }}
                loading={isRequesting}
                placeholder="Ask about MacBook Air..."
                autoSize={{ minRows: 1, maxRows: 6 }}
              />
            </div>
          </div>
        </div>
      </Flex>
    </ConfigProvider>
  );
}
