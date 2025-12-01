-- Check Optimization Status
-- Run this to verify which optimizations have been applied

\echo '════════════════════════════════════════════════════════════'
\echo '  SUPABASE OPTIMIZATION STATUS CHECK'
\echo '════════════════════════════════════════════════════════════'
\echo ''

-- 1. Check if new indexes exist (from 0003, 0004)
\echo '1. INDEX STATUS:'
SELECT
  CASE
    WHEN EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_embeddings_vector')
    THEN '✅ Vector index exists'
    ELSE '❌ Vector index missing - Run 0003'
  END AS vector_index,
  CASE
    WHEN EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_embeddings_metadata')
    THEN '✅ Metadata index exists'
    ELSE '❌ Metadata index missing - Run 0004'
  END AS metadata_index,
  CASE
    WHEN EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_documents_status_created')
    THEN '✅ Status index exists'
    ELSE '❌ Status index missing - Run 0004'
  END AS status_index,
  CASE
    WHEN EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_embeddings_document_id_covering')
    THEN '✅ Covering index exists'
    ELSE '❌ Covering index missing - Run 0004'
  END AS covering_index;

\echo ''
\echo '2. STORAGE OPTIMIZATION STATUS:'

-- Check TOAST settings (from 0005)
SELECT
  CASE
    WHEN attstorage = 'e' THEN '✅ EXTERNAL storage (optimized)'
    WHEN attstorage = 'x' THEN '⚠️  EXTENDED storage (default)'
    WHEN attstorage = 'm' THEN 'MAIN storage'
    ELSE 'PLAIN storage'
  END AS content_storage_strategy
FROM pg_attribute
WHERE attrelid = 'public.embeddings'::regclass
  AND attname = 'content';

-- Check if validation function exists
SELECT
  CASE
    WHEN EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'validate_embedding_metadata')
    THEN '✅ Metadata validation function exists'
    ELSE '❌ Validation function missing - Run 0005'
  END AS validation_function;

-- Check if metadata constraint exists
SELECT
  CASE
    WHEN EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_embeddings_metadata_valid')
    THEN '✅ Metadata constraint applied'
    ELSE '❌ Constraint missing - Run 0005'
  END AS metadata_constraint;

\echo ''
\echo '3. FUNCTION STATUS:'

-- Check if optimized functions exist (from 0007)
SELECT
  CASE
    WHEN EXISTS (
      SELECT 1 FROM pg_proc p
      JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'public'
        AND p.proname = 'match_documents'
        AND array_length(p.proargtypes::oid[], 1) >= 4
    )
    THEN '✅ Enhanced match_documents exists'
    ELSE '⚠️  Basic match_documents only - Run 0007'
  END AS match_function,
  CASE
    WHEN EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'hybrid_search_documents')
    THEN '✅ Hybrid search exists'
    ELSE '❌ Hybrid search missing - Run 0007'
  END AS hybrid_search;

\echo ''
\echo '4. RLS POLICY STATUS:'

-- Check if optimized policies exist (from 0008)
SELECT
  CASE
    WHEN EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'embeddings_service_role_all')
    THEN '✅ Service role bypass policy exists'
    ELSE '❌ Service role policy missing - Run 0008'
  END AS service_role_policy,
  CASE
    WHEN EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'current_user_id')
    THEN '✅ Optimized helper functions exist'
    ELSE '❌ Helper functions missing - Run 0008'
  END AS helper_functions;

\echo ''
\echo '5. MONITORING STATUS:'

-- Check if monitoring views exist (from 0009)
SELECT
  CASE
    WHEN EXISTS (SELECT 1 FROM pg_views WHERE viewname = 'performance_dashboard')
    THEN '✅ Performance dashboard exists'
    ELSE '❌ Dashboard missing - Run 0009'
  END AS dashboard,
  CASE
    WHEN EXISTS (SELECT 1 FROM pg_views WHERE viewname = 'table_storage_stats')
    THEN '✅ Storage stats view exists'
    ELSE '❌ Storage stats missing - Run 0005/0009'
  END AS storage_stats,
  CASE
    WHEN EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'query_performance_log')
    THEN '✅ Performance log table exists'
    ELSE '❌ Performance log missing - Run 0009'
  END AS perf_log;

\echo ''
\echo '6. CURRENT PERFORMANCE METRICS:'

-- Show current database stats
SELECT
  COUNT(*) AS total_embeddings,
  pg_size_pretty(pg_total_relation_size('public.embeddings')) AS embeddings_total_size,
  pg_size_pretty(pg_relation_size('public.embeddings')) AS embeddings_table_size,
  pg_size_pretty(
    pg_total_relation_size('public.embeddings') -
    pg_relation_size('public.embeddings')
  ) AS embeddings_toast_and_indexes
FROM public.embeddings;

-- Show documents count
SELECT COUNT(*) AS total_documents
FROM public.documents;

\echo ''
\echo '7. TOAST COMPRESSION CHECK:'

-- Check if data is being TOASTed
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
  pg_size_pretty(
    pg_total_relation_size(schemaname||'.'||tablename) -
    pg_relation_size(schemaname||'.'||tablename)
  ) AS external_size,
  ROUND(
    100.0 * (pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) /
    NULLIF(pg_total_relation_size(schemaname||'.'||tablename), 0),
    1
  ) AS external_percent
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('embeddings', 'documents')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

\echo ''
\echo '8. LAST ANALYZE TIMES:'

SELECT
  schemaname,
  relname AS tablename,
  last_analyze,
  last_autoanalyze,
  CASE
    WHEN last_analyze > NOW() - INTERVAL '7 days' OR last_autoanalyze > NOW() - INTERVAL '7 days'
    THEN '✅ Recently analyzed'
    WHEN last_analyze IS NOT NULL OR last_autoanalyze IS NOT NULL
    THEN '⚠️  Needs ANALYZE'
    ELSE '❌ Never analyzed'
  END AS analyze_status
FROM pg_stat_user_tables
WHERE schemaname = 'public'
  AND relname IN ('embeddings', 'documents');

\echo ''
\echo '════════════════════════════════════════════════════════════'
\echo '  SUMMARY'
\echo '════════════════════════════════════════════════════════════'
\echo ''
\echo 'To apply missing optimizations, run:'
\echo '  ./apply_optimizations.sh'
\echo ''
\echo 'Or apply migrations individually:'
\echo '  psql $DATABASE_URL -f supabase/migrations/0003_optimize_vector_index.sql'
\echo '  psql $DATABASE_URL -f supabase/migrations/0004_add_missing_indexes.sql'
\echo '  psql $DATABASE_URL -f supabase/migrations/0005_storage_optimization.sql'
\echo '  psql $DATABASE_URL -f supabase/migrations/0007_optimize_match_function.sql'
\echo '  psql $DATABASE_URL -f supabase/migrations/0008_optimize_rls_policies.sql'
\echo '  psql $DATABASE_URL -f supabase/migrations/0009_performance_monitoring.sql'
\echo ''
\echo 'For detailed help, see: OPTIMIZATION_GUIDE.md'
\echo '════════════════════════════════════════════════════════════'
