-- 0003_performance_optimizations.sql
-- Otimizações de performance: indexes parciais, vector index melhorado (HNSW), composites.

-- 1. Partial indexes para queries comuns (published docs)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_published_status ON public.documents (
    status,
    published_at,
    category
)
WHERE
    status = 'published';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_curator ON public.documents (slug, created_at)
WHERE
    NOT(status = 'published');

-- 2. Embeddings: HNSW index (mais rápido que ivfflat para ANN search, Supabase/pgvector 0.5+)
-- Drop ivfflat se existe (recreate melhor)
DROP INDEX IF EXISTS public.idx_embeddings_vector;

CREATE INDEX CONCURRENTLY ON public.embeddings USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 3. Composites para joins comuns
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_embeddings_doc_time ON public.embeddings (document_id, created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ingestion_items_run_status ON public.ingestion_items (run_id, status);

-- 4. Stats function para monitoring
CREATE OR REPLACE FUNCTION public.get_db_stats()
RETURNS jsonb
LANGUAGE sql STABLE
AS $$
  SELECT jsonb_build_object(
    'documents', (SELECT count(*)::int FROM public.documents),
    'embeddings', (SELECT count(*)::int FROM public.embeddings),
    'ingestion_runs', (SELECT count(*)::int FROM public.ingestion_runs),
    'published_docs', (SELECT count(*)::int FROM public.documents WHERE status = 'published'),
    'vector_index_size', (SELECT pg_size_pretty(pg_relation_size('public.embeddings_embedding_idx')) )
  );
$$;

COMMENT ON FUNCTION public.get_db_stats IS 'Stats rápidas para dashboard/monitoring. Use: select get_db_stats();';

-- 5. Otimizar RLS helper (cacheable?)
-- Já bom, mas adicionar index em auth.users se necessário (Supabase gerencia)

-- 6. Vacuum/Analyze recomendação (run manual: VACUUM ANALYZE;)
-- Execute via Supabase SQL Editor após migration.

-- 7. RLS otimizada: Adicionar policy mais eficiente para embeddings (partial)
-- Existing policies já referenciam documents.status eficientemente com index novo.
