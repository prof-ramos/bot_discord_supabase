-- 0002_match_documents.sql
-- RPC para busca vetorial RAG (cosine similarity via pgvector <=>)
--
-- IMPORTANTE: Esta função busca na tabela rag_chunks, que é a tabela
-- usada pelo código Python atual (supabase_store.py).
-- Compatível com o schema simples definido em schema.sql

CREATE OR REPLACE FUNCTION public.match_documents(
  query_embedding vector(1536),
  match_threshold float,
  match_count int
)
RETURNS TABLE (
  id bigint,
  document_id uuid,
  content text,
  similarity float,
  metadata jsonb
)
LANGUAGE sql STABLE
AS $$
  select
    c.id,
    c.document_id,
    c.chunk as content,
    1 - (c.embedding <=> query_embedding) as similarity,
    c.metadata
  from public.rag_chunks c
  where 1 - (c.embedding <=> query_embedding) > match_threshold
  order by c.embedding <=> query_embedding
  limit match_count;
$$;

COMMENT ON FUNCTION public.match_documents IS 'Busca semântica em chunks de documentos para RAG. Retorna chunks de rag_chunks ordenados por similaridade de cosseno. Use com embeddings ada-002 (1536 dim). Ex: match_documents(query_emb, 0.78, 5);';
