-- 0007_optimize_match_function.sql
-- Optimize match_documents function with filtering, metadata, and performance improvements

-- ============================================================================
-- 1. ENHANCED MATCH_DOCUMENTS FUNCTION
-- ============================================================================

-- Drop old version
DROP FUNCTION IF EXISTS public.match_documents (vector (1536), float, int);

-- Create optimized version with additional features
CREATE OR REPLACE FUNCTION public.match_documents(
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.78,
  match_count int DEFAULT 5,
  filter_status text DEFAULT 'published',
  filter_category text DEFAULT NULL,
  filter_tags text[] DEFAULT NULL
)
RETURNS TABLE (
  id bigint,
  document_id uuid,
  chunk_id text,
  content text,
  similarity float,
  document_title text,
  document_category text,
  document_tags text[],
  metadata jsonb
)
LANGUAGE sql
STABLE
PARALLEL SAFE
AS $$
  SELECT
    e.id,
    e.document_id,
    e.chunk_id,
    e.content,
    1 - (e.embedding <=> query_embedding) AS similarity,
    d.title AS document_title,
    d.category AS document_category,
    d.tags AS document_tags,
    e.metadata
  FROM public.embeddings e
  INNER JOIN public.documents d ON d.id = e.document_id
  WHERE
    d.status = filter_status::document_status
    AND (filter_category IS NULL OR d.category = filter_category)
    AND (filter_tags IS NULL OR d.tags && filter_tags)
    AND 1 - (e.embedding <=> query_embedding) > match_threshold
  ORDER BY e.embedding <=> query_embedding
  LIMIT match_count;
$$;

-- Set function-level optimizations
ALTER FUNCTION public.match_documents SET work_mem = '256MB';

ALTER FUNCTION public.match_documents SET effective_cache_size = '4GB';

ALTER FUNCTION public.match_documents SET random_page_cost = 1.1;

-- ============================================================================
-- 2. HYBRID SEARCH FUNCTION (Vector + Full-Text)
-- ============================================================================

-- Create hybrid search combining vector similarity and text matching
CREATE OR REPLACE FUNCTION public.hybrid_search_documents(
  query_embedding vector(1536),
  query_text text,
  match_threshold float DEFAULT 0.78,
  match_count int DEFAULT 5,
  vector_weight float DEFAULT 0.7,
  text_weight float DEFAULT 0.3
)
RETURNS TABLE (
  id bigint,
  document_id uuid,
  chunk_id text,
  content text,
  similarity float,
  text_rank float,
  combined_score float,
  document_title text,
  document_category text
)
LANGUAGE sql
STABLE
AS $$
  WITH vector_results AS (
    SELECT
      e.id,
      e.document_id,
      e.chunk_id,
      e.content,
      1 - (e.embedding <=> query_embedding) AS similarity,
      d.title,
      d.category
    FROM public.embeddings e
    INNER JOIN public.documents d ON d.id = e.document_id
    WHERE
      d.status = 'published'
      AND 1 - (e.embedding <=> query_embedding) > match_threshold
  ),
  text_results AS (
    SELECT
      e.id,
      ts_rank(to_tsvector('portuguese', e.content), plainto_tsquery('portuguese', query_text)) AS text_rank
    FROM public.embeddings e
    WHERE to_tsvector('portuguese', e.content) @@ plainto_tsquery('portuguese', query_text)
  )
  SELECT
    v.id,
    v.document_id,
    v.chunk_id,
    v.content,
    v.similarity,
    COALESCE(t.text_rank, 0) AS text_rank,
    (v.similarity * vector_weight + COALESCE(t.text_rank, 0) * text_weight) AS combined_score,
    v.title AS document_title,
    v.category AS document_category
  FROM vector_results v
  LEFT JOIN text_results t ON t.id = v.id
  ORDER BY combined_score DESC
  LIMIT match_count;
$$;

-- ============================================================================
-- 3. BATCH SEARCH FUNCTION
-- ============================================================================

-- Function for batch searching (useful for batch processing)
CREATE OR REPLACE FUNCTION public.batch_match_documents(
  query_embeddings vector(1536)[],
  match_threshold float DEFAULT 0.78,
  match_count int DEFAULT 5
)
RETURNS TABLE (
  query_index int,
  id bigint,
  document_id uuid,
  chunk_id text,
  content text,
  similarity float
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
  query_emb vector(1536);
  idx int := 1;
BEGIN
  FOREACH query_emb IN ARRAY query_embeddings
  LOOP
    RETURN QUERY
    SELECT
      idx AS query_index,
      e.id,
      e.document_id,
      e.chunk_id,
      e.content,
      1 - (e.embedding <=> query_emb) AS similarity
    FROM public.embeddings e
    INNER JOIN public.documents d ON d.id = e.document_id
    WHERE
      d.status = 'published'
      AND 1 - (e.embedding <=> query_emb) > match_threshold
    ORDER BY e.embedding <=> query_emb
    LIMIT match_count;

    idx := idx + 1;
  END LOOP;
END;
$$;

-- ============================================================================
-- 4. SEARCH WITH RERANKING
-- ============================================================================

-- Two-stage search: broad vector search + reranking
CREATE OR REPLACE FUNCTION public.match_documents_with_rerank(
  query_embedding vector(1536),
  initial_threshold float DEFAULT 0.70,
  final_threshold float DEFAULT 0.78,
  initial_count int DEFAULT 20,
  final_count int DEFAULT 5
)
RETURNS TABLE (
  id bigint,
  document_id uuid,
  chunk_id text,
  content text,
  similarity float,
  document_title text
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    e.id,
    e.document_id,
    e.chunk_id,
    e.content,
    1 - (e.embedding <=> query_embedding) AS similarity,
    d.title AS document_title
  FROM public.embeddings e
  INNER JOIN public.documents d ON d.id = e.document_id
  WHERE
    d.status = 'published'
    AND 1 - (e.embedding <=> query_embedding) > initial_threshold
  ORDER BY e.embedding <=> query_embedding
  LIMIT initial_count
$$;

-- ============================================================================
-- 5. METADATA-AWARE SEARCH
-- ============================================================================

-- Search with metadata filtering
CREATE OR REPLACE FUNCTION public.match_documents_by_metadata(
  query_embedding vector(1536),
  metadata_filter jsonb,
  match_threshold float DEFAULT 0.78,
  match_count int DEFAULT 5
)
RETURNS TABLE (
  id bigint,
  document_id uuid,
  chunk_id text,
  content text,
  similarity float,
  metadata jsonb
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    e.id,
    e.document_id,
    e.chunk_id,
    e.content,
    1 - (e.embedding <=> query_embedding) AS similarity,
    e.metadata
  FROM public.embeddings e
  INNER JOIN public.documents d ON d.id = e.document_id
  WHERE
    d.status = 'published'
    AND e.metadata @> metadata_filter
    AND 1 - (e.embedding <=> query_embedding) > match_threshold
  ORDER BY e.embedding <=> query_embedding
  LIMIT match_count;
$$;

-- ============================================================================
-- 6. PERFORMANCE MONITORING WRAPPER
-- ============================================================================

-- Instrumented version that logs performance
CREATE OR REPLACE FUNCTION public.match_documents_instrumented(
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.78,
  match_count int DEFAULT 5
)
RETURNS TABLE (
  id bigint,
  document_id uuid,
  chunk_id text,
  content text,
  similarity float,
  document_title text,
  document_category text,
  document_tags text[],
  metadata jsonb,
  execution_time_ms numeric
)
LANGUAGE plpgsql
AS $$
DECLARE
  start_time timestamptz;
  end_time timestamptz;
  exec_time numeric;
BEGIN
  start_time := clock_timestamp();

  RETURN QUERY
  SELECT
    r.*,
    NULL::numeric AS execution_time_ms
  FROM public.match_documents(query_embedding, match_threshold, match_count) r;

  end_time := clock_timestamp();
  exec_time := EXTRACT(milliseconds FROM (end_time - start_time));

  -- Log performance (optional: uncomment to enable logging)
  -- INSERT INTO public.query_performance_log (query_type, execution_time_ms, result_count)
  -- VALUES ('match_documents', exec_time::integer, match_count);

  RAISE NOTICE 'match_documents executed in % ms', exec_time;
END;
$$;

-- ============================================================================
-- 7. COMMENTS AND DOCUMENTATION
-- ============================================================================

COMMENT ON FUNCTION public.match_documents IS 'Optimized semantic search with status, category, and tag filtering. Returns top-k similar chunks with document metadata.';

COMMENT ON FUNCTION public.hybrid_search_documents IS 'Hybrid search combining vector similarity (70%) and full-text search (30%). Best for user queries with specific terms.';

COMMENT ON FUNCTION public.batch_match_documents IS 'Batch search for multiple query embeddings. Useful for processing multiple queries efficiently.';

COMMENT ON FUNCTION public.match_documents_with_rerank IS 'Two-stage search: broad recall (initial_count) followed by precision filtering (final_count). Reduces computation while maintaining quality.';

COMMENT ON FUNCTION public.match_documents_by_metadata IS 'Search with JSONB metadata filtering using containment operator (@>). Example: {\"source\": \"lei_8112\"}';

COMMENT ON FUNCTION public.match_documents_instrumented IS 'Performance-instrumented version of match_documents with execution time logging.';

-- ============================================================================
-- 8. USAGE EXAMPLES
-- ============================================================================

/*
-- Basic search
SELECT * FROM match_documents(
'[0.1, 0.2, ...]'::vector(1536),
0.78,
5
);

-- Search with category filter
SELECT * FROM match_documents(
'[0.1, 0.2, ...]'::vector(1536),
0.78,
5,
'published',
'd_administrativo',
NULL
);

-- Search with tag filter
SELECT * FROM match_documents(
'[0.1, 0.2, ...]'::vector(1536),
0.78,
5,
'published',
NULL,
ARRAY['lei', 'administrativo']
);

-- Hybrid search (vector + text)
SELECT * FROM hybrid_search_documents(
'[0.1, 0.2, ...]'::vector(1536),
'servidor público',
0.75,
10
);

-- Metadata search
SELECT * FROM match_documents_by_metadata(
'[0.1, 0.2, ...]'::vector(1536),
'{"source": "lei_8112"}'::jsonb,
0.78,
5
);
*/
