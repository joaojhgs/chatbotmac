'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Sender, Bubble, Prompts } from '@ant-design/x';
import type { PromptProps } from '@ant-design/x';
import { ConfigProvider, Flex, theme, Button } from 'antd';
import { RobotOutlined, UserOutlined, DeleteOutlined } from '@ant-design/icons';
import { ToolCallDisplay } from './components/ToolCallDisplay';
import { MarkdownContent } from './components/MarkdownContent';
import type { ToolCall } from './types/chat';
import type { GetProp } from 'antd';
import { useChatStore } from './store/chatStore';
import {
  useConversationHistory,
  useSuggestions,
  useChatAgent,
  useMessageSync,
  useClearHistory,
} from './hooks';

export default function Home() {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const promptsContainerRef = useRef<HTMLDivElement>(null);

  // Zustand store
  const {
    messages: storeMessages,
    toolCallsByMessageId,
    isLoadingHistory,
    isRequesting,
  } = useChatStore();

  // Custom hooks
  useConversationHistory();
  const { suggestions, showSuggestions, setShowSuggestions } = useSuggestions();
  const { agent, currentAssistantMessageIdRef, hasContent } = useChatAgent();
  const { onRequest } = useMessageSync(agent, currentAssistantMessageIdRef);
  const { handleClearHistory } = useClearHistory();

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [storeMessages]);

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
                  const isLoading = !isUser && msg.status === 'loading' && !hasContent;

                  // Check if previous message was also a user message
                  const prevMsg = index > 0 ? storeMessages[index - 1] : null;
                  const isConsecutiveUserMessage = isUser && prevMsg?.role === 'user';

                  // Larger spacing on mobile for consecutive user messages
                  const spacingClass = isConsecutiveUserMessage ? 'mb-8 md:mb-4' : 'mb-4';

                  return (
                    <div key={String(msg.id)} className={spacingClass}>
                      <Bubble
                        content={
                          isUser ? (
                            typeof msg.content === 'string' ? msg.content : String(msg.content || '')
                          ) : (
                            <MarkdownContent
                              content={typeof msg.content === 'string' ? msg.content : String(msg.content || '')}
                            />
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
                }}
              >
                <Prompts
                  items={suggestions.map((suggestion, index) => ({
                    key: String(index),
                    label: suggestion,
                  }))}
                  onItemClick={(item: { data: PromptProps }) => {
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
                onSubmit={(text: string) => {
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
