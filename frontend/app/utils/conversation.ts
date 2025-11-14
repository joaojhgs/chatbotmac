/**
 * Conversation ID management utilities.
 * Handles localStorage persistence and generation of conversation IDs.
 */

const CONVERSATION_ID_KEY = 'macbook_chatbot_conversation_id';

/**
 * Generate a new conversation ID (UUID v4).
 */
export function generateConversationId(): string {
  // Simple UUID v4 generator
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * Get conversation ID from localStorage or generate a new one.
 */
export function getConversationId(): string {
  if (typeof window === 'undefined') {
    return generateConversationId();
  }

  const stored = localStorage.getItem(CONVERSATION_ID_KEY);
  if (stored) {
    return stored;
  }

  const newId = generateConversationId();
  saveConversationId(newId);
  return newId;
}

/**
 * Save conversation ID to localStorage.
 */
export function saveConversationId(conversationId: string): void {
  if (typeof window === 'undefined') {
    return;
  }
  localStorage.setItem(CONVERSATION_ID_KEY, conversationId);
}

/**
 * Clear conversation ID from localStorage.
 */
export function clearConversationId(): void {
  if (typeof window === 'undefined') {
    return;
  }
  localStorage.removeItem(CONVERSATION_ID_KEY);
}

