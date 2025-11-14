/**
 * Zustand store for chat state management.
 * Centralized state for messages, tool calls, and conversation management.
 */

import { create } from 'zustand';
import type { ToolCall } from '../types/chat';

export interface Message {
  id: string | number;
  role: 'user' | 'assistant';
  content: string;
  status?: 'loading' | 'local' | 'done';
  timestamp?: number;
  isPolling?: boolean; // Track if message is still being updated via polling
}

interface ChatState {
  // Conversation
  conversationId: string | null;

  // Messages (from server + SSE)
  messages: Message[];

  // Tool calls by message ID
  toolCallsByMessageId: Map<string, ToolCall[]>;

  // Loading states
  isLoadingHistory: boolean;
  isRequesting: boolean;

  // Actions
  setConversationId: (id: string | null) => void;
  addMessage: (message: Message) => void;
  updateMessage: (id: string | number, updates: Partial<Message>) => void;
  addToolCall: (messageId: string | number, toolCall: ToolCall) => void;
  updateToolCall: (messageId: string | number, toolCallId: string, result: string) => void;
  setMessages: (messages: Message[]) => void;
  setToolCallsForMessage: (messageId: string | number, toolCalls: ToolCall[]) => void;
  setIsLoadingHistory: (loading: boolean) => void;
  setIsRequesting: (requesting: boolean) => void;
  clearConversation: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  // Initial state
  conversationId: null,
  messages: [],
  toolCallsByMessageId: new Map(),
  isLoadingHistory: false,
  isRequesting: false,

  // Actions
  setConversationId: (id) => set({ conversationId: id }),

  addMessage: (message) =>
    set((state) => {
      // Check if message already exists to prevent duplicates
      const messageIdStr = String(message.id);
      const exists = state.messages.some((m) => String(m.id) === messageIdStr);
      if (exists) {
        return state; // Message already exists, don't add
      }
      return {
        messages: [...state.messages, message],
      };
    }),
  updateMessage: (id, updates) =>
    set((state) => {
      const messageIndex = state.messages.findIndex((msg) => msg.id === id);
      if (messageIndex === -1) return state; // Message not found, no update needed
      
      const existingMsg = state.messages[messageIndex];
      // Only update if something actually changed
      const hasChanges = Object.keys(updates).some(
        (key) => existingMsg[key as keyof typeof existingMsg] !== updates[key as keyof typeof updates]
      );
      
      if (!hasChanges) return state; // No changes, return same state
      
      return {
        messages: state.messages.map((msg) =>
          msg.id === id ? { ...msg, ...updates } : msg
        ),
      };
    }),

  addToolCall: (messageId, toolCall) =>
    set((state) => {
      const messageIdStr = String(messageId);
      const existing = state.toolCallsByMessageId.get(messageIdStr) || [];
      const newMap = new Map(state.toolCallsByMessageId);
      newMap.set(messageIdStr, [...existing, toolCall]);
      return { toolCallsByMessageId: newMap };
    }),

  updateToolCall: (messageId, toolCallId, result) =>
    set((state) => {
      const messageIdStr = String(messageId);
      const existing = state.toolCallsByMessageId.get(messageIdStr) || [];
      const updated = existing.map((tc) =>
        tc.id === toolCallId ? { ...tc, result } : tc
      );
      const newMap = new Map(state.toolCallsByMessageId);
      newMap.set(messageIdStr, updated);
      return { toolCallsByMessageId: newMap };
    }),

  setMessages: (messages) => set({ messages }),

  setToolCallsForMessage: (messageId, toolCalls) =>
    set((state) => {
      const messageIdStr = String(messageId);
      const newMap = new Map(state.toolCallsByMessageId);
      newMap.set(messageIdStr, toolCalls);
      return { toolCallsByMessageId: newMap };
    }),

  setIsLoadingHistory: (loading) => set({ isLoadingHistory: loading }),

  setIsRequesting: (requesting) => set({ isRequesting: requesting }),

  clearConversation: () =>
    set({
      conversationId: null,
      messages: [],
      toolCallsByMessageId: new Map(),
      isLoadingHistory: false,
      isRequesting: false,
    }),
}));

