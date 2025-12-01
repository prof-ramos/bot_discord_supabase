-- 0003_optimize_vector_index.sql
-- Optimize IVFFlat vector index for better performance

-- Drop existing index
DROP INDEX IF EXISTS idx_embeddings_vector;

-- Recreate with optimized list count
-- Formula: sqrt(total_rows) for datasets < 1M rows
-- For 10k rows: lists = 100
-- For 100k rows: lists = 316
-- For 500k rows: lists = 707
-- Starting with 200 as a balanced default

-- Increase maintenance_work_mem for index creation
SET maintenance_work_mem = '128MB';

CREATE INDEX idx_embeddings_vector ON public.embeddings USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 200);

-- CRITICAL: Run ANALYZE after index creation for optimal query planning
ANALYZE public.embeddings;

-- Add statistics target for better query planning
ALTER TABLE public.embeddings
ALTER COLUMN embedding
SET
    STATISTICS 1000;

COMMENT ON INDEX idx_embeddings_vector IS 'IVFFlat index for vector similarity search. Adjust lists parameter as data grows: sqrt(rows) for < 1M rows, rows/1000 for larger datasets. Re-run ANALYZE after bulk inserts.';
