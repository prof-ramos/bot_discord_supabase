-- 0005_storage_optimization.sql
-- Optimize storage: TEXT field compression, JSONB constraints, TOAST settings

-- ============================================================================
-- 1. TEXT FIELD OPTIMIZATION
-- ============================================================================

-- Set TOAST storage strategy for large text fields
-- EXTERNAL: Store large values in separate TOAST table, compress
-- EXTENDED (default): Try to compress and move to TOAST if still large
-- MAIN: Try to keep in main table, compress but allow TOAST
-- PLAIN: No compression, no TOAST (for small values)

-- Optimize embeddings.content (large text chunks)
ALTER TABLE public.embeddings
ALTER COLUMN content SET STORAGE EXTERNAL;

-- Optimize documents fields
ALTER TABLE public.documents
ALTER COLUMN summary SET STORAGE EXTENDED;

-- Set compression threshold (values > 2KB will be compressed)
ALTER TABLE public.embeddings
SET (toast_tuple_target = 2048);

ALTER TABLE public.documents
SET (toast_tuple_target = 2048);

-- ============================================================================
-- 2. JSONB METADATA CONSTRAINTS AND OPTIMIZATION
-- ============================================================================

-- Add validation function for metadata structure
CREATE OR REPLACE FUNCTION public.validate_embedding_metadata(metadata jsonb)
RETURNS boolean
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
  -- Enforce metadata schema
  -- Expected fields: source_page, section, confidence, etc.

  -- Check that metadata is an object, not array or primitive
  IF jsonb_typeof(metadata) != 'object' THEN
    RETURN FALSE;
  END IF;

  -- Limit metadata size (prevent abuse)
  IF length(metadata::text) > 10000 THEN
    RETURN FALSE;
  END IF;

  -- Add more specific validations as needed
  RETURN TRUE;
END;
$$;

-- Add check constraint for metadata validation
ALTER TABLE public.embeddings
ADD CONSTRAINT check_embeddings_metadata_valid
CHECK (validate_embedding_metadata(metadata));

-- Set default empty object instead of NULL for new rows
ALTER TABLE public.embeddings
ALTER COLUMN metadata SET DEFAULT '{}'::jsonb;

-- Update existing NULLs to empty objects
UPDATE public.embeddings
SET metadata = '{}'::jsonb
WHERE metadata IS NULL;

-- Add NOT NULL constraint after cleanup
ALTER TABLE public.embeddings
ALTER COLUMN metadata SET NOT NULL;

-- ============================================================================
-- 3. CONTENT LENGTH CONSTRAINTS
-- ============================================================================

-- Add constraint to prevent excessively large chunks
ALTER TABLE public.embeddings
ADD CONSTRAINT check_content_length
CHECK (length(content) <= 50000);

-- Add constraint for document summary
ALTER TABLE public.documents
ADD CONSTRAINT check_summary_length
CHECK (summary IS NULL OR length(summary) <= 5000);

-- ============================================================================
-- 4. ADDITIONAL STORAGE OPTIMIZATIONS
-- ============================================================================

-- Enable row-level compression for better storage efficiency
ALTER TABLE public.embeddings
SET (fillfactor = 90);

ALTER TABLE public.documents
SET (fillfactor = 95);

-- Set autovacuum parameters for better space reclamation
ALTER TABLE public.embeddings
SET (
  autovacuum_vacuum_scale_factor = 0.05,
  autovacuum_analyze_scale_factor = 0.02,
  autovacuum_vacuum_cost_limit = 1000
);

ALTER TABLE public.documents
SET (
  autovacuum_vacuum_scale_factor = 0.1,
  autovacuum_analyze_scale_factor = 0.05
);

-- ============================================================================
-- 5. ADD METADATA HELPER FUNCTIONS
-- ============================================================================

-- Function to extract common metadata fields
CREATE OR REPLACE FUNCTION public.get_embedding_metadata_field(
  embedding_metadata jsonb,
  field_name text
)
RETURNS text
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
AS $$
  SELECT embedding_metadata ->> field_name;
$$;

-- Create indexed expression for common metadata queries
CREATE INDEX IF NOT EXISTS idx_embeddings_metadata_source
ON public.embeddings ((metadata->>'source'))
WHERE metadata ? 'source';

CREATE INDEX IF NOT EXISTS idx_embeddings_metadata_section
ON public.embeddings ((metadata->>'section'))
WHERE metadata ? 'section';

-- ============================================================================
-- 6. STATISTICS AND COMMENTS
-- ============================================================================

-- Update table statistics
ANALYZE public.embeddings;
ANALYZE public.documents;

-- Add helpful comments
COMMENT ON CONSTRAINT check_embeddings_metadata_valid ON public.embeddings IS
'Validates metadata structure: must be JSONB object, max 10KB size';

COMMENT ON CONSTRAINT check_content_length ON public.embeddings IS
'Limits chunk content to 50,000 characters to prevent storage bloat';

COMMENT ON FUNCTION public.validate_embedding_metadata IS
'Validates embedding metadata structure and size constraints';

-- Show storage statistics query for monitoring
CREATE OR REPLACE VIEW public.table_storage_stats AS
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
  pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS external_size,
  pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) AS indexes_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

COMMENT ON VIEW public.table_storage_stats IS
'Monitor table storage breakdown: table vs TOAST vs indexes';
