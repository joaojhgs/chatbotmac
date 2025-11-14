import { useChatStore } from '../store/chatStore';
import { clearConversationId, generateConversationId, saveConversationId } from '../utils/conversation';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Hook to handle clearing conversation history
 */
export function useClearHistory() {
  const { conversationId, setConversationId, clearConversation } = useChatStore();

  const handleClearHistory = async () => {
    const oldConversationId = conversationId;
    
    // Clear store state first (messages, tool calls, etc.)
    clearConversation();
    
    // Clear localStorage
    clearConversationId();
    
    // Generate and save new ID immediately
    const newId = generateConversationId();
    saveConversationId(newId);
    
    // Set new ID in store BEFORE deleting old conversation
    // This ensures useConversationHistory uses the new ID
    setConversationId(newId);
    
    // Delete old conversation from backend (if it exists)
    if (oldConversationId) {
      try {
        await fetch(`${API_URL}/conversations/${oldConversationId}`, {
          method: 'DELETE',
        });
      } catch (error) {
        console.error('Failed to delete conversation:', error);
      }
    }
  };

  return { handleClearHistory };
}

