import { useState, useEffect } from 'react';
import { useChatStore } from '../store/chatStore';
import type { SuggestionsResponse } from '../types/chat';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Hook to load and manage prompt suggestions
 */
export function useSuggestions() {
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const { conversationId, isRequesting } = useChatStore();

  useEffect(() => {
    const loadSuggestions = async () => {
      // Always use API endpoint, even when there's no conversation
      if (!conversationId || isRequesting) {
        return;
      }

      try {
        const response = await fetch(`${API_URL}/conversations/${conversationId}/suggestions`);
        if (response.ok) {
          const data = (await response.json()) as SuggestionsResponse;
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

  return { suggestions, showSuggestions, setShowSuggestions };
}

