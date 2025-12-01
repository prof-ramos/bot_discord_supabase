-- 0002_match_documents.sql
-- RPC para busca vetorial RAG (cosine similarity via pgvector <=>)

CREATE OR REPLACE FUNCTION public.match_documents(
  query_embedding vector(1536),
  match_threshold float,
  match_count int
)
RETURNS TABLE (
  id bigint,
  document_id uuid,
  chunk_id text,
  content text,
  similarity float
)
LANGUAGE sql STABLE
AS $$
  select
    embeddings.id,
    embeddings.document_id,
    embeddings.chunk_id,
    embeddings.content,
    1 - (embeddings.embedding <=> query_embedding) as similarity
  from public.embeddings
  where 1 - (embeddings.embedding <=> query_embedding) > match_threshold
  order by embeddings.embedding <=> query_embedding
  limit match_count;
$$;

COMMENT ON FUNCTION public.match_documents IS 'Busca semântica em chunks de documentos jurídicos para RAG. Use com embeddings ada-002 (1536 dim). Ex: match_documents(query_emb, 0.78, 5);';
