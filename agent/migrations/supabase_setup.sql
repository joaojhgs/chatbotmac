-- Supabase Database Setup for MacBook Air Chatbot
-- Run this SQL in your Supabase SQL Editor

-- Enable pgvector extension (required for vector similarity search)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create macbook_facts table
CREATE TABLE IF NOT EXISTS macbook_facts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(1536),  -- Dimension for text-embedding-3-small (1536) or text-embedding-3-large (3072)
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for vector similarity search using IVFFlat
-- Note: IVFFlat requires at least some data to be effective
-- You may want to create this index after populating some data
CREATE INDEX IF NOT EXISTS macbook_facts_embedding_idx 
ON macbook_facts 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create function for similarity search
CREATE OR REPLACE FUNCTION match_macbook_facts(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    metadata JSONB,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        macbook_facts.id,
        macbook_facts.content,
        macbook_facts.metadata,
        1 - (macbook_facts.embedding <=> query_embedding) AS similarity
    FROM macbook_facts
    WHERE macbook_facts.embedding IS NOT NULL
      AND 1 - (macbook_facts.embedding <=> query_embedding) > match_threshold
    ORDER BY macbook_facts.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_macbook_facts_updated_at
    BEFORE UPDATE ON macbook_facts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Grant necessary permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT, UPDATE ON macbook_facts TO authenticated;
-- GRANT EXECUTE ON FUNCTION match_macbook_facts TO authenticated;

-- Example: Insert a sample fact (you'll need to generate the embedding separately)
-- INSERT INTO macbook_facts (content, metadata) VALUES (
--     'The MacBook Air M3 features an 8-core CPU and up to 10-core GPU, with support for up to 24GB unified memory.',
--     '{"source": "Apple Official", "model": "M3", "category": "specifications"}'::jsonb
-- );


