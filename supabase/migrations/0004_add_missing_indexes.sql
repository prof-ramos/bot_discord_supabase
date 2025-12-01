-- 0004_add_missing_indexes.sql
-- Add missing indexes for better query performance

-- JSONB metadata index for filtering and searching
CREATE INDEX IF NOT EXISTS idx_embeddings_metadata
ON public.embeddings
USING gin (metadata);

-- Composite index for status filtering with temporal ordering
CREATE INDEX IF NOT EXISTS idx_documents_status_created
ON public.documents (status, created_at DESC)
WHERE status = 'published';

-- Temporal index for embeddings queries
CREATE INDEX IF NOT EXISTS idx_embeddings_created_at
ON public.embeddings (created_at DESC);

-- Composite index to support RLS policy lookups
CREATE INDEX IF NOT EXISTS idx_documents_status_created_by
ON public.documents (status, created_by)
WHERE created_by IS NOT NULL;

-- Covering index for embeddings joins (reduces heap lookups)
CREATE INDEX IF NOT EXISTS idx_embeddings_document_id_covering
ON public.embeddings (document_id)
INCLUDE (id, chunk_id, created_at);

-- Index for version lookups
CREATE INDEX IF NOT EXISTS idx_document_versions_doc_label
ON public.document_versions (document_id, version_label);

-- Full-text search preparation (optional but useful for hybrid search)
ALTER TABLE public.documents
ADD COLUMN IF NOT EXISTS search_vector tsvector
GENERATED ALWAYS AS (
  setweight(to_tsvector('portuguese', coalesce(title, '')), 'A') ||
  setweight(to_tsvector('portuguese', coalesce(summary, '')), 'B') ||
  setweight(to_tsvector('portuguese', coalesce(category, '')), 'C')
) STORED;

CREATE INDEX IF NOT EXISTS idx_documents_search_vector
ON public.documents
USING gin (search_vector);

-- Index for tags array queries
CREATE INDEX IF NOT EXISTS idx_documents_tags_specific
ON public.documents
USING gin (tags)
WHERE tags <> '{}';

-- Update statistics for query planner
ANALYZE public.embeddings;
ANALYZE public.documents;
ANALYZE public.document_versions;

COMMENT ON INDEX idx_embeddings_metadata IS 'GIN index for JSONB metadata filtering';
COMMENT ON INDEX idx_documents_status_created IS 'Partial index for published documents ordered by creation date';
COMMENT ON INDEX idx_embeddings_document_id_covering IS 'Covering index to avoid heap lookups in joins';
COMMENT ON COLUMN public.documents.search_vector IS 'Generated TSVector for full-text search in Portuguese';
