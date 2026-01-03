-- Migration: Create RAG search function for Segundo Cérebro
-- Date: 2026-01-03

-- Enable pgvector extension (if not exists)
CREATE EXTENSION IF NOT EXISTS vector;

-- Ensure rag_knowledge table exists with proper structure
CREATE TABLE IF NOT EXISTS rag_knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI text-embedding-3-small
    project_key TEXT,
    tags TEXT[],
    source TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for vector similarity search
CREATE INDEX IF NOT EXISTS rag_knowledge_embedding_idx
ON rag_knowledge USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create index for category filtering
CREATE INDEX IF NOT EXISTS rag_knowledge_category_idx ON rag_knowledge(category);

-- Create index for project_key filtering
CREATE INDEX IF NOT EXISTS rag_knowledge_project_idx ON rag_knowledge(project_key);

-- Function: Search RAG knowledge base using cosine similarity
CREATE OR REPLACE FUNCTION search_rag_knowledge(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 5,
    filter_category text DEFAULT NULL,
    filter_project text DEFAULT NULL,
    filter_tags text[] DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    category text,
    title text,
    content text,
    project_key text,
    tags text[],
    source text,
    similarity float,
    created_at timestamptz
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        rk.id,
        rk.category,
        rk.title,
        rk.content,
        rk.project_key,
        rk.tags,
        rk.source,
        1 - (rk.embedding <=> query_embedding) AS similarity,
        rk.created_at
    FROM rag_knowledge rk
    WHERE
        -- Similarity threshold
        1 - (rk.embedding <=> query_embedding) > match_threshold
        -- Category filter
        AND (filter_category IS NULL OR rk.category = filter_category)
        -- Project filter
        AND (filter_project IS NULL OR rk.project_key = filter_project)
        -- Tags filter (any tag matches)
        AND (filter_tags IS NULL OR rk.tags && filter_tags)
    ORDER BY similarity DESC
    LIMIT match_count;
END;
$$;

-- Grant permissions
GRANT EXECUTE ON FUNCTION search_rag_knowledge TO anon, authenticated, service_role;
GRANT ALL ON TABLE rag_knowledge TO anon, authenticated, service_role;
