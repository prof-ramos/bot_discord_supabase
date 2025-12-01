-- 0006_table_partitioning.sql
-- Implement table partitioning for time-series data (embeddings table)
-- NOTE: Only apply this migration if you have > 100k embeddings or expect high growth

-- ============================================================================
-- OPTION 1: Range Partitioning by created_at (Time-based)
-- ============================================================================

-- This migration shows how to partition the embeddings table
-- Uncomment and run when your embeddings table grows > 100k rows

/*
-- Step 1: Rename existing table
ALTER TABLE public.embeddings RENAME TO embeddings_old;

-- Step 2: Create partitioned table
CREATE TABLE public.embeddings (
  id bigserial,
  document_id uuid NOT NULL,
  chunk_id text NOT NULL,
  content text NOT NULL,
  embedding vector(1536) NOT NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT embeddings_document_chunk_unique UNIQUE (document_id, chunk_id, created_at)
) PARTITION BY RANGE (created_at);

-- Step 3: Create partitions (quarterly for example)
CREATE TABLE embeddings_2024_q4 PARTITION OF public.embeddings
FOR VALUES FROM ('2024-10-01') TO ('2025-01-01');

CREATE TABLE embeddings_2025_q1 PARTITION OF public.embeddings
FOR VALUES FROM ('2025-01-01') TO ('2025-04-01');

CREATE TABLE embeddings_2025_q2 PARTITION OF public.embeddings
FOR VALUES FROM ('2025-04-01') TO ('2025-07-01');

CREATE TABLE embeddings_2025_q3 PARTITION OF public.embeddings
FOR VALUES FROM ('2025-07-01') TO ('2025-10-01');

CREATE TABLE embeddings_2025_q4 PARTITION OF public.embeddings
FOR VALUES FROM ('2025-10-01') TO ('2026-01-01');

-- Default partition for future data
CREATE TABLE embeddings_default PARTITION OF public.embeddings DEFAULT;

-- Step 4: Migrate data from old table
INSERT INTO public.embeddings
SELECT * FROM public.embeddings_old;

-- Step 5: Recreate indexes on partitioned table
CREATE INDEX idx_embeddings_document_id ON public.embeddings (document_id);
CREATE INDEX idx_embeddings_chunk ON public.embeddings (chunk_id);
CREATE INDEX idx_embeddings_metadata ON public.embeddings USING gin (metadata);
CREATE INDEX idx_embeddings_created_at ON public.embeddings (created_at DESC);

-- Vector indexes on each partition for better performance
CREATE INDEX idx_embeddings_vector_2024_q4 ON embeddings_2024_q4
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

CREATE INDEX idx_embeddings_vector_2025_q1 ON embeddings_2025_q1
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

CREATE INDEX idx_embeddings_vector_2025_q2 ON embeddings_2025_q2
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX idx_embeddings_vector_2025_q3 ON embeddings_2025_q3
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX idx_embeddings_vector_2025_q4 ON embeddings_2025_q4
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX idx_embeddings_vector_default ON embeddings_default
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Step 6: Recreate RLS policies
ALTER TABLE public.embeddings ENABLE ROW LEVEL SECURITY;

CREATE POLICY embeddings_read_published
  ON public.embeddings
  FOR SELECT
  TO authenticated
  USING (
    public.is_curator_or_admin()
    OR
    EXISTS (
      SELECT 1
      FROM public.documents d
      WHERE d.id = embeddings.document_id
        AND (
          d.status = 'published'
          OR d.created_by = auth.uid()
        )
    )
  );

CREATE POLICY embeddings_write_curators
  ON public.embeddings
  FOR ALL
  TO authenticated
  USING (
    public.is_curator_or_admin()
    OR EXISTS (
      SELECT 1
      FROM public.documents d
      WHERE d.id = embeddings.document_id
        AND d.created_by = auth.uid()
    )
  )
  WITH CHECK (
    public.is_curator_or_admin()
    OR EXISTS (
      SELECT 1
      FROM public.documents d
      WHERE d.id = embeddings.document_id
        AND d.created_by = auth.uid()
    )
  );

-- Step 7: Verify and cleanup
-- Verify counts match
DO $$
DECLARE
  old_count bigint;
  new_count bigint;
BEGIN
  SELECT COUNT(*) INTO old_count FROM public.embeddings_old;
  SELECT COUNT(*) INTO new_count FROM public.embeddings;

  IF old_count != new_count THEN
    RAISE EXCEPTION 'Migration failed: counts do not match (old: %, new: %)', old_count, new_count;
  END IF;

  RAISE NOTICE 'Migration successful: % rows migrated', new_count;
END $$;

-- After verification, drop old table (be careful!)
-- DROP TABLE public.embeddings_old CASCADE;

-- Step 8: Run ANALYZE on all partitions
ANALYZE public.embeddings;
*/

-- ============================================================================
-- OPTION 2: Helper Functions for Managing Partitions
-- ============================================================================

-- Function to automatically create new partitions
CREATE OR REPLACE FUNCTION public.create_embeddings_partition(
  start_date date,
  end_date date,
  partition_name text
)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
  EXECUTE format(
    'CREATE TABLE IF NOT EXISTS %I PARTITION OF public.embeddings FOR VALUES FROM (%L) TO (%L)',
    partition_name,
    start_date,
    end_date
  );

  -- Create vector index on new partition
  EXECUTE format(
    'CREATE INDEX IF NOT EXISTS idx_%I_vector ON %I USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)',
    partition_name,
    partition_name
  );

  RAISE NOTICE 'Created partition % for range % to %', partition_name, start_date, end_date;
END;
$$;

-- Function to list all partitions
CREATE OR REPLACE VIEW public.embeddings_partitions AS
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
  (SELECT COUNT(*) FROM pg_class WHERE relname = tablename) AS exists
FROM pg_tables
WHERE tablename LIKE 'embeddings_%' OR tablename = 'embeddings'
ORDER BY tablename;

-- ============================================================================
-- AUTOMATIC PARTITION MAINTENANCE
-- ============================================================================

-- Function to check if we need new partitions
CREATE OR REPLACE FUNCTION public.check_partition_needed()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  next_quarter_start date;
  next_quarter_end date;
  partition_name text;
BEGIN
  -- Calculate next quarter
  next_quarter_start := date_trunc('quarter', CURRENT_DATE + interval '3 months')::date;
  next_quarter_end := (next_quarter_start + interval '3 months')::date;
  partition_name := 'embeddings_' || to_char(next_quarter_start, 'YYYY_q"q"');

  -- Check if partition exists
  IF NOT EXISTS (
    SELECT 1 FROM pg_tables WHERE tablename = partition_name
  ) THEN
    PERFORM public.create_embeddings_partition(
      next_quarter_start,
      next_quarter_end,
      partition_name
    );
  END IF;
END;
$$;

-- ============================================================================
-- COMMENTS AND DOCUMENTATION
-- ============================================================================

COMMENT ON FUNCTION public.create_embeddings_partition IS
'Helper function to create new quarterly partitions for embeddings table. Usage: SELECT create_embeddings_partition(''2026-01-01''::date, ''2026-04-01''::date, ''embeddings_2026_q1'')';

COMMENT ON FUNCTION public.check_partition_needed IS
'Checks if a new partition is needed for the next quarter and creates it automatically. Run this monthly via cron.';

COMMENT ON VIEW public.embeddings_partitions IS
'Lists all partitions of the embeddings table with their sizes';

-- ============================================================================
-- NOTES FOR IMPLEMENTATION
-- ============================================================================

/*
WHEN TO USE PARTITIONING:
- You have > 100,000 embeddings
- You expect > 1M embeddings in the future
- Your queries often filter by created_at
- You need to archive old data efficiently

BENEFITS:
- Faster queries (partition pruning)
- Easier data archival (drop old partitions)
- Better index performance (smaller indexes per partition)
- Parallel query execution across partitions

DRAWBACKS:
- More complex maintenance
- Requires planning partition boundaries
- Unique constraints must include partition key

TO IMPLEMENT:
1. Backup your database first!
2. Uncomment the migration code above
3. Test on a staging environment
4. Run during low-traffic period
5. Verify data integrity
6. Set up cron job to run check_partition_needed() monthly

MAINTENANCE:
- Run weekly: ANALYZE public.embeddings;
- Run monthly: SELECT check_partition_needed();
- Monitor partition sizes: SELECT * FROM embeddings_partitions;
- Archive old partitions: DROP TABLE embeddings_2024_q1; (after backup!)
*/
