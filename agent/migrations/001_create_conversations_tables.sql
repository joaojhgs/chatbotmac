-- Migration: Create conversations, messages, and tool_calls tables
-- Run this SQL in your Supabase SQL Editor

-- Create conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create messages table
CREATE TABLE IF NOT EXISTS messages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT fk_conversation FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- Create tool_calls table
CREATE TABLE IF NOT EXISTS tool_calls (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    tool_name VARCHAR(100) NOT NULL,
    input JSONB DEFAULT '{}',
    result TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT fk_message FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tool_calls_message_id ON tool_calls(message_id);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_conversation_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE conversations
    SET updated_at = NOW()
    WHERE id = NEW.conversation_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to update conversation updated_at when messages are inserted
CREATE TRIGGER update_conversation_on_message_insert
    AFTER INSERT ON messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_updated_at();

-- Create function to get conversation history with tool calls
CREATE OR REPLACE FUNCTION get_conversation_history(
    p_conversation_id UUID,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    message_id UUID,
    role VARCHAR,
    content TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    tool_calls JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id AS message_id,
        m.role,
        m.content,
        m.created_at,
        COALESCE(
            (
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'id', tc.id,
                        'tool_name', tc.tool_name,
                        'input', tc.input,
                        'result', tc.result,
                        'created_at', tc.created_at
                    )
                )
                FROM tool_calls tc
                WHERE tc.message_id = m.id
            ),
            '[]'::jsonb
        ) AS tool_calls
    FROM messages m
    WHERE m.conversation_id = p_conversation_id
    ORDER BY m.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

