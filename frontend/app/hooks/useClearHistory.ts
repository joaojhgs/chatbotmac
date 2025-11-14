import { useChatStore } from '../store/chatStore';
import { clearConversationId, generateConversationId, saveConversationId } from '../utils/conversation';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Hook to handle clearing conversation history
 */
export function useClearHistory() {
  const { conversationId, setConversationId, clearConversation } = useChatStore();

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
    // Clear localStorage first
    clearConversationId();
    // Clear store state
    clearConversation();
    // Generate and save new ID
    const newId = generateConversationId();
    saveConversationId(newId);
    // Set new ID in store (this will trigger useConversationHistory to reload)
    setConversationId(newId);
  };

  return { handleClearHistory };
}

