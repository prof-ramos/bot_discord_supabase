-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table
CREATE TABLE IF NOT EXISTS public.rag_documents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title text NOT NULL,
    doc_type text NOT NULL DEFAULT 'upload',
    source_path text,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Chunks table with pgvector
CREATE TABLE IF NOT EXISTS public.rag_chunks (
    id bigserial PRIMARY KEY,
    document_id uuid REFERENCES public.rag_documents(id) ON DELETE CASCADE,
    chunk text NOT NULL,
    embedding vector(1536) NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Indexes and constraints
CREATE INDEX IF NOT EXISTS rag_chunks_doc_id_idx ON public.rag_chunks(document_id);
CREATE INDEX IF NOT EXISTS rag_chunks_created_at_idx ON public.rag_chunks(created_at DESC);
CREATE INDEX IF NOT EXISTS rag_documents_created_at_idx ON public.rag_documents(created_at DESC);

-- Vector index tuned for small datasets / free tier (lists=64, cosine)
DROP INDEX IF EXISTS rag_chunks_embedding_idx;
CREATE INDEX rag_chunks_embedding_idx
    ON public.rag_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 64);

-- Search function for Supabase RPC (used by the bot)
CREATE OR REPLACE FUNCTION public.rag_search_chunks(
    query_embedding vector(1536),
    match_count int DEFAULT 5,
    match_threshold float DEFAULT 0.72
)
RETURNS TABLE (
    id bigint,
    document_id uuid,
    chunk text,
    similarity float,
    metadata jsonb
)
LANGUAGE sql
STABLE
PARALLEL SAFE
AS $$
  SELECT
    c.id,
    c.document_id,
    c.chunk,
    1 - (c.embedding <=> query_embedding) AS similarity,
    c.metadata
  FROM public.rag_chunks c
  WHERE 1 - (c.embedding <=> query_embedding) > match_threshold
  ORDER BY c.embedding <=> query_embedding
  LIMIT match_count;
$$;

COMMENT ON FUNCTION public.rag_search_chunks IS
'Vector search over rag_chunks with cosine similarity. Use via Supabase RPC.';

