import { useEffect } from 'react';
import { useXChat } from '@ant-design/x';
import { useChatStore } from '../store/chatStore';
import type { XAgent } from '@ant-design/x/es/use-x-agent';
import type { MessageInfo } from '@ant-design/x/es/use-x-chat';
import type { SSEOutput } from '@ant-design/x/es/x-stream';

/**
 * Helper function to extract string content from useXChat message
 */
const extractMessageContent = (message: unknown): string => {
  if (typeof message === 'string') return message;
  if (typeof message === 'object' && message !== null && 'data' in message) {
    return String((message as { data: unknown }).data);
  }
  return String(message || '');
};

/**
 * Hook to sync useXChat messages with Zustand store
 */
export function useMessageSync(
  agent: XAgent<string, { message: string }, SSEOutput>,
  currentAssistantMessageIdRef: React.MutableRefObject<string | number | null>
) {
  const { onRequest, messages: xChatMessages } = useXChat({ agent });
  const { addMessage, updateMessage } = useChatStore();

  useEffect(() => {
    // Track messages we've processed in this effect run to prevent duplicates
    const processedIds = new Set<string>();

    xChatMessages.forEach((xMsg: MessageInfo<string>) => {
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
          const loadingMsg = currentStoreMessages.find(
            (m) => String(m.id) === loadingMsgId && m.status === 'loading'
          );

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
              content: extractMessageContent(xMsg.message),
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
          content: extractMessageContent(xMsg.message),
          status: xMsg.status === 'local' ? 'local' : xMsg.status === 'loading' ? 'loading' : 'done',
        });

        // Track assistant message ID for tool calls
        if (!isUser && xMsg.status === 'loading') {
          currentAssistantMessageIdRef.current = xMsg.id;
        }
      } else {
        // Only update if content or status actually changed
        const messageContent = extractMessageContent(xMsg.message);
        const contentChanged = existingMsg.content !== messageContent;
        const newStatus = xMsg.status === 'local' ? 'local' : xMsg.status === 'loading' ? 'loading' : 'done';
        const statusChanged = existingMsg.status !== newStatus;

        if (contentChanged || statusChanged) {
          updateMessage(xMsg.id, {
            content: messageContent,
            status: newStatus,
          });
        }
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [xChatMessages]); // Only depend on xChatMessages to avoid infinite loop

  return { onRequest };
}

