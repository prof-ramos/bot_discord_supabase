-- 0009_performance_monitoring.sql
-- Setup comprehensive performance monitoring and observability

-- ============================================================================
-- 1. ENABLE EXTENSIONS
-- ============================================================================

-- Enable pg_stat_statements for query performance tracking
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Enable pg_trgm for similarity searches (useful for debugging)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================================
-- 2. QUERY PERFORMANCE LOG TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.query_performance_log (
    id bigserial PRIMARY KEY,
    query_type text NOT NULL,
    execution_time_ms integer NOT NULL,
    result_count integer,
    user_id uuid,
    query_params jsonb,
    error_message text,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Add indexes for querying logs
CREATE INDEX idx_query_perf_log_created ON public.query_performance_log (created_at DESC);

CREATE INDEX idx_query_perf_log_type ON public.query_performance_log (query_type);

CREATE INDEX idx_query_perf_log_time ON public.query_performance_log (execution_time_ms DESC);

-- Add table settings
ALTER TABLE public.query_performance_log SET(
    autovacuum_vacuum_scale_factor = 0.02,
    autovacuum_analyze_scale_factor = 0.01
);

COMMENT ON
TABLE public.query_performance_log IS 'Performance tracking for search queries. Monitor execution times and identify slow queries.';

-- ============================================================================
-- 3. SLOW QUERY MONITORING VIEWS
-- ============================================================================

-- View for slow queries from pg_stat_statements
CREATE OR REPLACE VIEW public.slow_queries AS
SELECT
  queryid,
  substring(query, 1, 200) AS query_preview,
  calls,
  total_exec_time::numeric(10,2) AS total_time_ms,
  mean_exec_time::numeric(10,2) AS mean_time_ms,
  max_exec_time::numeric(10,2) AS max_time_ms,
  stddev_exec_time::numeric(10,2) AS stddev_time_ms,
  rows,
  100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0) AS cache_hit_ratio
FROM pg_stat_statements
WHERE mean_exec_time > 100  -- Queries averaging > 100ms
  AND query NOT LIKE '%pg_stat_statements%'  -- Exclude monitoring queries
ORDER BY mean_exec_time DESC
LIMIT 50;

COMMENT ON VIEW public.slow_queries IS 'Top 50 slowest queries with > 100ms average execution time. Use this to identify optimization opportunities.';

-- ============================================================================
-- 4. TABLE AND INDEX STATISTICS
-- ============================================================================

-- View for table sizes and bloat
CREATE OR REPLACE VIEW public.table_health_stats AS
SELECT
    schemaname,
    relname AS tablename,
    pg_size_pretty (
        pg_total_relation_size (schemaname || '.' || relname)
    ) AS total_size,
    pg_size_pretty (
        pg_relation_size (schemaname || '.' || relname)
    ) AS table_size,
    pg_size_pretty (
        pg_indexes_size (schemaname || '.' || relname)
    ) AS indexes_size,
    n_live_tup AS live_rows,
    n_dead_tup AS dead_rows,
    ROUND(
        100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0),
        2
    ) AS dead_row_percent,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE
    schemaname = 'public'
ORDER BY pg_total_relation_size (schemaname || '.' || relname) DESC;

COMMENT ON VIEW public.table_health_stats IS 'Monitor table health: size, bloat, vacuum status. Run VACUUM if dead_row_percent > 20%.';

-- View for index usage
CREATE OR REPLACE VIEW public.index_usage_stats AS
SELECT
    schemaname,
    relname AS tablename,
    indexrelname AS indexname,
    idx_scan AS index_scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched,
    pg_size_pretty (pg_relation_size (indexrelid)) AS index_size,
    CASE
        WHEN idx_scan = 0 THEN '⚠️  Unused'
        WHEN idx_scan < 100 THEN '⚠️  Low usage'
        ELSE '✅ Active'
    END AS usage_status
FROM pg_stat_user_indexes
WHERE
    schemaname = 'public'
ORDER BY idx_scan ASC, pg_relation_size (indexrelid) DESC;

COMMENT ON VIEW public.index_usage_stats IS 'Monitor index usage. Consider dropping unused indexes to save space and improve write performance.';

-- ============================================================================
-- 5. VECTOR INDEX STATISTICS
-- ============================================================================

-- View for vector index health
CREATE OR REPLACE VIEW public.vector_index_stats AS
SELECT
    i.indexrelname AS indexname,
    i.relname AS tablename,
    pg_size_pretty (
        pg_relation_size (i.indexrelid)
    ) AS index_size,
    i.idx_scan AS scans,
    s.n_live_tup AS table_rows,
    -- IVFFlat optimal lists: sqrt(rows) or rows/1000
    CASE
        WHEN s.n_live_tup < 10000 THEN FLOOR(SQRT(s.n_live_tup))
        ELSE FLOOR(s.n_live_tup / 1000.0)
    END AS recommended_lists,
    s.last_analyze,
    CASE
        WHEN s.last_analyze IS NULL THEN '❌ Never analyzed'
        WHEN s.last_analyze < NOW() - INTERVAL '7 days' THEN '⚠️  Needs ANALYZE'
        ELSE '✅ Recently analyzed'
    END AS analyze_status
FROM
    pg_stat_user_indexes i
    JOIN pg_stat_user_tables s ON s.relid = i.relid
WHERE
    i.indexrelname LIKE '%vector%'
    AND i.schemaname = 'public';

-- ... (skipping to get_maintenance_recommendations)

-- Check for unused indexes
RETURN QUERY
  SELECT
    '🟢 Low' AS priority,
    'Consider dropping ' || indexrelname AS action,
    'Index scans: ' || idx_scan::text || ', Size: ' || pg_size_pretty(pg_relation_size(indexrelid)) AS reason,
    '-- DROP INDEX IF EXISTS ' || schemaname || '.' || indexrelname || ';  -- Verify before dropping!' AS command
  FROM pg_stat_user_indexes
  WHERE schemaname = 'public'
    AND idx_scan < 10
    AND pg_relation_size(indexrelid) > 1024 * 1024  -- > 1MB
    AND indexrelname NOT LIKE '%_pkey'  -- Don't suggest dropping primary keys
  ORDER BY pg_relation_size(indexrelid) DESC;

COMMENT ON VIEW public.vector_index_stats IS 'Monitor vector index health and get recommendations for optimal list count. Run ANALYZE regularly!';

-- ============================================================================
-- 6. SEARCH PERFORMANCE METRICS
-- ============================================================================

-- Aggregate search performance over time
CREATE OR REPLACE VIEW public.search_performance_summary AS
SELECT
  query_type,
  DATE_TRUNC('hour', created_at) AS hour,
  COUNT(*) AS query_count,
  AVG(execution_time_ms)::numeric(10,2) AS avg_time_ms,
  MIN(execution_time_ms) AS min_time_ms,
  MAX(execution_time_ms) AS max_time_ms,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY execution_time_ms)::numeric(10,2) AS median_time_ms,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_time_ms)::numeric(10,2) AS p95_time_ms,
  PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY execution_time_ms)::numeric(10,2) AS p99_time_ms,
  COUNT(*) FILTER (WHERE error_message IS NOT NULL) AS error_count
FROM public.query_performance_log
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY query_type, DATE_TRUNC('hour', created_at)
ORDER BY hour DESC, query_type;

COMMENT ON VIEW public.search_performance_summary IS 'Hourly search performance metrics with percentiles. Monitor p95 and p99 for SLA compliance.';

-- ============================================================================
-- 7. CACHE HIT RATIO MONITORING
-- ============================================================================

-- Database-wide cache statistics
CREATE OR REPLACE VIEW public.cache_hit_stats AS
SELECT
    'Database' AS level,
    SUM(heap_blks_read) AS blocks_read,
    SUM(heap_blks_hit) AS blocks_hit,
    ROUND(
        100.0 * SUM(heap_blks_hit) / NULLIF(
            SUM(heap_blks_hit) + SUM(heap_blks_read),
            0
        ),
        2
    ) AS cache_hit_ratio,
    CASE
        WHEN ROUND(
            100.0 * SUM(heap_blks_hit) / NULLIF(
                SUM(heap_blks_hit) + SUM(heap_blks_read),
                0
            ),
            2
        ) >= 99 THEN '✅ Excellent'
        WHEN ROUND(
            100.0 * SUM(heap_blks_hit) / NULLIF(
                SUM(heap_blks_hit) + SUM(heap_blks_read),
                0
            ),
            2
        ) >= 95 THEN '✅ Good'
        WHEN ROUND(
            100.0 * SUM(heap_blks_hit) / NULLIF(
                SUM(heap_blks_hit) + SUM(heap_blks_read),
                0
            ),
            2
        ) >= 90 THEN '⚠️  Fair'
        ELSE '❌ Poor - Increase shared_buffers'
    END AS status
FROM pg_statio_user_tables
WHERE
    schemaname = 'public';

COMMENT ON VIEW public.cache_hit_stats IS 'Database cache hit ratio. Aim for > 99%. If < 95%, consider increasing shared_buffers.';

-- ============================================================================
-- 8. CONNECTION AND ACTIVITY MONITORING
-- ============================================================================

-- Active queries and connections
CREATE OR REPLACE VIEW public.active_connections AS
SELECT
  pid,
  usename AS username,
  application_name,
  client_addr,
  state,
  query_start,
  state_change,
  EXTRACT(EPOCH FROM (NOW() - query_start))::integer AS query_duration_seconds,
  substring(query, 1, 200) AS query_preview,
  CASE
    WHEN state = 'idle' THEN '✅ Idle'
    WHEN EXTRACT(EPOCH FROM (NOW() - query_start)) > 30 THEN '⚠️  Long running'
    ELSE '✅ Active'
  END AS status
FROM pg_stat_activity
WHERE datname = current_database()
  AND pid != pg_backend_pid()
ORDER BY query_start DESC NULLS LAST;

COMMENT ON VIEW public.active_connections IS 'Monitor active database connections and long-running queries. Kill long queries with: SELECT pg_terminate_backend(pid);';

-- ============================================================================
-- 9. LOGGING HELPER FUNCTIONS
-- ============================================================================

-- Function to log search performance
CREATE OR REPLACE FUNCTION public.log_search_performance(
  p_query_type text,
  p_execution_time_ms integer,
  p_result_count integer DEFAULT NULL,
  p_query_params jsonb DEFAULT NULL,
  p_error_message text DEFAULT NULL
)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
  INSERT INTO public.query_performance_log (
    query_type,
    execution_time_ms,
    result_count,
    user_id,
    query_params,
    error_message
  )
  VALUES (
    p_query_type,
    p_execution_time_ms,
    p_result_count,
    public.current_user_id(),
    p_query_params,
    p_error_message
  );
END;
$$;

COMMENT ON FUNCTION public.log_search_performance IS 'Log search query performance. Usage: SELECT log_search_performance(''match_documents'', 150, 5, ''{"threshold": 0.78}''::jsonb);';

-- ============================================================================
-- 10. AUTOMATED MAINTENANCE FUNCTIONS
-- ============================================================================

-- Function to recommend maintenance actions
CREATE OR REPLACE FUNCTION public.get_maintenance_recommendations()
RETURNS TABLE (
  priority text,
  action text,
  reason text,
  command text
)
LANGUAGE plpgsql
AS $$
BEGIN
  -- Check for tables needing VACUUM
  RETURN QUERY
  SELECT
    '🔴 High' AS priority,
    'VACUUM ' || schemaname || '.' || tablename AS action,
    'Dead row ratio: ' || ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2)::text || '%' AS reason,
    'VACUUM ANALYZE ' || schemaname || '.' || tablename || ';' AS command
  FROM pg_stat_user_tables
  WHERE schemaname = 'public'
    AND n_dead_tup > 1000
    AND 100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0) > 20
  ORDER BY n_dead_tup DESC;

  -- Check for tables needing ANALYZE
  RETURN QUERY
  SELECT
    '🟡 Medium' AS priority,
    'ANALYZE ' || schemaname || '.' || tablename AS action,
    'Last analyzed: ' || COALESCE(last_analyze::text, 'Never') AS reason,
    'ANALYZE ' || schemaname || '.' || tablename || ';' AS command
  FROM pg_stat_user_tables
  WHERE schemaname = 'public'
    AND (last_analyze IS NULL OR last_analyze < NOW() - INTERVAL '7 days')
  ORDER BY last_analyze NULLS FIRST;

  -- Check for unused indexes
  RETURN QUERY
  SELECT
    '🟢 Low' AS priority,
    'Consider dropping ' || indexrelname AS action,
    'Index scans: ' || idx_scan::text || ', Size: ' || pg_size_pretty(pg_relation_size(indexrelid)) AS reason,
    '-- DROP INDEX IF EXISTS ' || schemaname || '.' || indexrelname || ';  -- Verify before dropping!' AS command
  FROM pg_stat_user_indexes
  WHERE schemaname = 'public'
    AND idx_scan < 10
    AND pg_relation_size(indexrelid) > 1024 * 1024  -- > 1MB
    AND indexrelname NOT LIKE '%_pkey'  -- Don't suggest dropping primary keys
  ORDER BY pg_relation_size(indexrelid) DESC;
END;
$$;

COMMENT ON FUNCTION public.get_maintenance_recommendations IS 'Get automated maintenance recommendations. Run: SELECT * FROM get_maintenance_recommendations();';

-- ============================================================================
-- 11. PERFORMANCE DASHBOARD VIEW
-- ============================================================================

-- Comprehensive performance dashboard
CREATE OR REPLACE VIEW public.performance_dashboard AS
SELECT
  'Database Size' AS metric,
  pg_size_pretty(pg_database_size(current_database())) AS value,
  NULL AS status
UNION ALL
SELECT
  'Cache Hit Ratio',
  ROUND(
    100.0 * SUM(heap_blks_hit) / NULLIF(SUM(heap_blks_hit) + SUM(heap_blks_read), 0),
    2
  )::text || '%',
  CASE
    WHEN ROUND(100.0 * SUM(heap_blks_hit) / NULLIF(SUM(heap_blks_hit) + SUM(heap_blks_read), 0), 2) >= 99 THEN '✅'
    WHEN ROUND(100.0 * SUM(heap_blks_hit) / NULLIF(SUM(heap_blks_hit) + SUM(heap_blks_read), 0), 2) >= 95 THEN '✅'
    ELSE '⚠️'
  END
FROM pg_statio_user_tables
WHERE schemaname = 'public'
UNION ALL
SELECT
  'Active Connections',
  COUNT(*)::text,
  CASE WHEN COUNT(*) > 50 THEN '⚠️' ELSE '✅' END
FROM pg_stat_activity
WHERE datname = current_database()
UNION ALL
SELECT
  'Embeddings Count',
  COUNT(*)::text,
  '📊'
FROM public.embeddings
UNION ALL
SELECT
  'Documents Count',
  COUNT(*)::text,
  '📚'
FROM public.documents
UNION ALL
SELECT
  'Avg Search Time (24h)',
  ROUND(AVG(execution_time_ms))::text || 'ms',
  CASE
    WHEN AVG(execution_time_ms) < 100 THEN '✅'
    WHEN AVG(execution_time_ms) < 500 THEN '⚠️'
    ELSE '❌'
  END
FROM public.query_performance_log
WHERE created_at > NOW() - INTERVAL '24 hours';

COMMENT ON VIEW public.performance_dashboard IS 'Quick performance overview dashboard. Monitor key metrics at a glance.';

-- ============================================================================
-- 12. GRANT PERMISSIONS
-- ============================================================================

-- Grant read access to monitoring views (authenticated users)
GRANT SELECT ON public.query_performance_log TO authenticated;

GRANT SELECT ON public.slow_queries TO authenticated;

GRANT SELECT ON public.table_health_stats TO authenticated;

GRANT SELECT ON public.index_usage_stats TO authenticated;

GRANT SELECT ON public.vector_index_stats TO authenticated;

GRANT SELECT ON public.search_performance_summary TO authenticated;

GRANT SELECT ON public.cache_hit_stats TO authenticated;

GRANT SELECT ON public.active_connections TO authenticated;

GRANT SELECT ON public.performance_dashboard TO authenticated;

-- ============================================================================
-- 13. USAGE INSTRUCTIONS
-- ============================================================================

/*
MONITORING QUERIES:

-- 1. Quick performance overview
SELECT * FROM performance_dashboard;

-- 2. Check for slow queries
SELECT * FROM slow_queries LIMIT 10;

-- 3. Table health check
SELECT * FROM table_health_stats;

-- 4. Index usage
SELECT * FROM index_usage_stats WHERE usage_status LIKE '⚠️%';

-- 5. Vector index health
SELECT * FROM vector_index_stats;

-- 6. Search performance (last 24h)
SELECT * FROM search_performance_summary
WHERE hour > NOW() - INTERVAL '24 hours'
ORDER BY hour DESC;

-- 7. Cache hit ratio
SELECT * FROM cache_hit_stats;

-- 8. Active connections
SELECT * FROM active_connections;

-- 9. Maintenance recommendations
SELECT * FROM get_maintenance_recommendations();

-- 10. Manual performance logging (from application)
SELECT log_search_performance(
'match_documents',
150,
5,
'{"threshold": 0.78, "match_count": 5}'::jsonb
);

MAINTENANCE SCHEDULE:

Daily:
- SELECT * FROM performance_dashboard;
- SELECT * FROM slow_queries LIMIT 10;

Weekly:
- SELECT * FROM get_maintenance_recommendations();
- ANALYZE public.embeddings;
- ANALYZE public.documents;

Monthly:
- VACUUM ANALYZE public.embeddings;
- VACUUM ANALYZE public.documents;
- Review index usage: SELECT * FROM index_usage_stats;

ALERTS TO SET UP:
- Alert if avg search time > 500ms
- Alert if cache hit ratio < 95%
- Alert if dead row percent > 20%
- Alert if active connections > 80
*/
