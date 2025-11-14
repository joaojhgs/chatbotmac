'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useXAgent, useXChat, Sender, Bubble } from '@ant-design/x';
import { ConfigProvider, Flex, theme } from 'antd';
import { RobotOutlined, UserOutlined } from '@ant-design/icons';
import { ToolCallDisplay } from './components/ToolCallDisplay';
import { MarkdownContent } from './components/MarkdownContent';
import { parseSSEStream } from './utils/sse';
import type { SSEMessage } from './utils/sse';
import type { ToolCall } from './types/chat';
import type { GetProp } from 'antd';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function Home() {
  const [inputValue, setInputValue] = useState('');
  const [toolCallsState, setToolCallsState] = useState<Map<string, ToolCall[]>>(new Map());
  const [hasContentForRequest, setHasContentForRequest] = useState<Map<string, boolean>>(new Map());
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const currentRequestIdRef = useRef<string | null>(null);
  const toolCallsByRequestRef = useRef<Map<string, ToolCall[]>>(new Map());
  const messageIdToRequestIdRef = useRef<Map<string, string>>(new Map());

  // Create agent with SSE streaming support
  const [agent] = useXAgent({
    request: async (info, callbacks) => {
      const { message } = info;
      const { onSuccess, onUpdate, onError } = callbacks;

      const requestId = `req-${Date.now()}-${Math.random()}`;
      currentRequestIdRef.current = requestId;
      toolCallsByRequestRef.current.set(requestId, []);
      // Initialize content tracking - no content received yet
      setHasContentForRequest((prev) => {
        const newMap = new Map(prev);
        newMap.set(requestId, false);
        return newMap;
      });

      let fullContent = '';

      try {
        const response = await fetch(`${API_URL}/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ message }),
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        // Parse SSE stream
        for await (const event of parseSSEStream(response)) {
          const sseEvent = event as SSEMessage;

          switch (sseEvent.type) {
            case 'content_delta':
              if (sseEvent.content) {
                fullContent += sseEvent.content;
                // Mark that we have content for this request
                setHasContentForRequest((prev) => {
                  const newMap = new Map(prev);
                  newMap.set(requestId, true);
                  return newMap;
                });
                onUpdate(fullContent as any);
              }
              break;

            case 'tool_call':
              if (sseEvent.tool) {
                const toolCallId = `${sseEvent.tool}-${Date.now()}`;
                const toolCall: ToolCall = {
                  id: toolCallId,
                  tool: sseEvent.tool,
                  input: sseEvent.input || {},
                  timestamp: Date.now(),
                };
                const toolCalls = toolCallsByRequestRef.current.get(requestId) || [];
                toolCalls.push(toolCall);
                toolCallsByRequestRef.current.set(requestId, toolCalls);
                // Update state immediately to trigger re-render and show tool call
                setToolCallsState(new Map(toolCallsByRequestRef.current));
                // Don't call onUpdate here - only update when we have actual content
                // This keeps the loading state active during tool calls
              }
              break;

            case 'tool_result':
              if (sseEvent.tool && sseEvent.result) {
                const toolCalls = toolCallsByRequestRef.current.get(requestId) || [];
                const toolCall = toolCalls.find(
                  (tc) => tc.tool === sseEvent.tool && !tc.result
                );
                if (toolCall) {
                  toolCall.result = sseEvent.result;
                  toolCallsByRequestRef.current.set(requestId, toolCalls);
                  // Update state to trigger re-render
                  setToolCallsState(new Map(toolCallsByRequestRef.current));
                  // Don't call onUpdate here - only update when we have actual content
                  // This keeps the loading state active during tool calls
                }
              }
              break;

            case 'content':
              if (sseEvent.content) {
                fullContent = sseEvent.content;
                // Mark that we have content for this request
                setHasContentForRequest((prev) => {
                  const newMap = new Map(prev);
                  newMap.set(requestId, true);
                  return newMap;
                });
                onUpdate(fullContent as any);
              }
              break;

            case 'done':
              // Associate the latest assistant message with this request
              // This will be done in useEffect when messages update
              currentRequestIdRef.current = null;
              onSuccess([fullContent] as any);
              break;

            case 'error':
              currentRequestIdRef.current = null;
              onError(new Error(sseEvent.message || 'Unknown error'));
              break;
          }
        }
      } catch (error) {
        console.error('Chat request failed:', error);
        currentRequestIdRef.current = null;
        onError(error as Error);
      }
    },
  });

  // Manage chat state
  const { onRequest, messages } = useXChat({ agent });

  // Associate tool calls with messages - update immediately when messages change
  useEffect(() => {
    if (currentRequestIdRef.current) {
      // Find the latest assistant message (loading or completed)
      const assistantMessages = messages.filter((msg) => msg.status !== 'local');
      if (assistantMessages.length > 0) {
        const latestAssistant = assistantMessages[assistantMessages.length - 1];
        // Associate this message with the current request
        const messageIdStr = String(latestAssistant.id);
        const existingRequestId = messageIdToRequestIdRef.current.get(messageIdStr);
        if (!existingRequestId || existingRequestId !== currentRequestIdRef.current) {
          messageIdToRequestIdRef.current.set(
            messageIdStr,
            currentRequestIdRef.current
          );
        }
        // Force re-render to show tool calls
        setToolCallsState(new Map(toolCallsByRequestRef.current));
      }
    }
  }, [messages]);

  // Also update when tool calls state changes to ensure UI updates
  useEffect(() => {
    // This effect ensures that when toolCallsState updates, we re-associate if needed
    if (currentRequestIdRef.current && messages.length > 0) {
      const assistantMessages = messages.filter((msg) => msg.status !== 'local');
      if (assistantMessages.length > 0) {
        const latestAssistant = assistantMessages[assistantMessages.length - 1];
        const messageIdStr = String(latestAssistant.id);
        if (!messageIdToRequestIdRef.current.has(messageIdStr)) {
          messageIdToRequestIdRef.current.set(
            messageIdStr,
            currentRequestIdRef.current
          );
        }
      }
    }
  }, [toolCallsState, messages]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

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
  const getToolCallsForMessage = (messageId: string | number, isUser: boolean): ToolCall[] => {
    const messageIdStr = String(messageId);
    if (isUser) return [];
    
    // First try to get tool calls by message ID association
    const requestId = messageIdToRequestIdRef.current.get(messageIdStr);
    if (requestId) {
      return toolCallsState.get(requestId) || [];
    }
    
    // If no association yet, check if this is the latest assistant message
    // and if there's a current request, show its tool calls
    const assistantMessages = messages.filter((msg) => msg.status !== 'local');
    if (assistantMessages.length > 0) {
      const latestAssistant = assistantMessages[assistantMessages.length - 1];
      if (String(latestAssistant.id) === messageIdStr && currentRequestIdRef.current) {
        return toolCallsState.get(currentRequestIdRef.current) || [];
      }
    }
    
    return [];
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
            background: 'radial-gradient(circle at 20% 50%, rgba(120, 119, 198, 0.3) 0%, transparent 50%), radial-gradient(circle at 80% 80%, rgba(255, 119, 198, 0.2) 0%, transparent 50%)',
            animation: 'pulse 15s ease-in-out infinite',
          }}
        />
        
        {/* Header */}
        <div className="glass-dark border-b border-white/10 px-6 py-5 relative z-10">
          <h1 className="m-0 text-xl font-semibold text-white/95 tracking-tight">
            MacBook Air Chatbot
          </h1>
          <p className="m-0 mt-1.5 text-sm text-white/60 font-light">
            Ask me anything about MacBook Air
          </p>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto px-6 py-8 relative z-10">
          <div className="mx-auto max-w-4xl">
            {messages.length === 0 ? (
              <div className="flex h-full items-center justify-center min-h-[60vh]">
                <div className="text-center">
                  <div className="mb-6 inline-flex items-center justify-center w-20 h-20 rounded-full glass-strong border border-white/20">
                    <RobotOutlined className="text-4xl text-white/80" />
                  </div>
                  <h2 className="mb-3 text-3xl font-semibold text-white/95 tracking-tight">
                    Welcome to MacBook Air Chatbot
                  </h2>
                  <p className="text-white/60 font-light text-base">
                    Start a conversation to learn about MacBook Air
                  </p>
                </div>
              </div>
            ) : (
              <div>
                {messages.map((msg) => {
                  const isUser = msg.status === 'local';
                  const msgIdStr = String(msg.id);
                  const toolCalls = getToolCallsForMessage(msgIdStr, isUser);
                  
                  // Determine loading state: show loading if message is loading AND we haven't received content yet
                  const requestId = messageIdToRequestIdRef.current.get(msgIdStr);
                  const hasContent = requestId ? hasContentForRequest.get(requestId) : false;
                  const isLoading = !isUser && msg.status === 'loading' && !hasContent;

                  return (
                    <div key={msg.id} className="mb-4">
                      <Bubble
                        content={
                          isUser ? (
                            msg.message
                          ) : (
                            <MarkdownContent content={msg.message} />
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
        <div className="glass-dark border-t border-white/10 px-6 py-5 relative z-10">
          <div className="mx-auto max-w-4xl">
            <div className="glass-strong rounded-2xl shadow-2xl overflow-hidden sender-container">
              <Sender
                value={inputValue}
                onChange={setInputValue}
                onSubmit={(text) => {
                  onRequest(text);
                  setInputValue('');
                }}
                loading={agent.isRequesting()}
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
