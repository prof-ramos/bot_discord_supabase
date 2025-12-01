#!/usr/bin/env python3
"""
Quick status check for Supabase optimizations
Usage: uv run check_status.py
"""

import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not all([SUPABASE_URL, SUPABASE_SERVICE_KEY]):
    print("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")
    exit(1)

# Initialize client
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

print("╔════════════════════════════════════════════════════════════╗")
print("║         SUPABASE OPTIMIZATION STATUS CHECK                ║")
print("╚════════════════════════════════════════════════════════════╝")
print()

# Check 1: Basic counts
print("📊 DATABASE OVERVIEW:")
try:
    # Count embeddings
    result = supabase.table("embeddings").select("id", count="exact").limit(1).execute()
    embeddings_count = result.count
    print(f"  • Embeddings: {embeddings_count:,}")

    # Count documents
    result = supabase.table("documents").select("id", count="exact").limit(1).execute()
    documents_count = result.count
    print(f"  • Documents: {documents_count:,}")

except Exception as e:
    print(f"  ❌ Error: {e}")

print()

# Check 2: Test optimized function
print("🔍 FUNCTION CHECK:")
try:
    # Test if enhanced match_documents exists
    test_embedding = [0.0] * 1536
    result = supabase.rpc("match_documents", {
        "query_embedding": test_embedding,
        "match_threshold": 0.78,
        "match_count": 1
    }).execute()

    if result.data is not None:
        print("  ✅ Basic match_documents working")

        # Check if enhanced version (with filters)
        result = supabase.rpc("match_documents", {
            "query_embedding": test_embedding,
            "match_threshold": 0.78,
            "match_count": 1,
            "filter_status": "published"
        }).execute()

        if result.data is not None:
            print("  ✅ Enhanced match_documents (with filters) working")
        else:
            print("  ⚠️  Basic match_documents only - Apply 0007 migration")

except Exception as e:
    error_msg = str(e)
    if "filter_status" in error_msg or "argument" in error_msg:
        print("  ⚠️  Basic match_documents only - Apply 0007 migration")
    else:
        print(f"  ❌ Error: {e}")

print()

# Check 3: Test monitoring views
print("📈 MONITORING STATUS:")
try:
    # Try to query performance dashboard
    result = supabase.rpc("", {}).execute()  # This will fail, but we'll use table() instead
except:
    pass

try:
    # Check if we can access performance log
    result = supabase.table("query_performance_log").select("*").limit(1).execute()
    print("  ✅ Performance logging enabled")
except Exception as e:
    if "relation" in str(e).lower() or "not found" in str(e).lower():
        print("  ❌ Performance monitoring not set up - Apply 0009 migration")
    else:
        print(f"  ⚠️  Could not check: {e}")

print()

# Check 4: Storage optimization
print("💾 STORAGE CHECK:")
print("  Run this SQL query in Supabase Dashboard to check:")
print("  SELECT * FROM table_storage_stats;")
print()

# Check 5: Recommendations
print("🎯 RECOMMENDATIONS:")

if embeddings_count == 0:
    print("  • No embeddings found. Run ingestion first:")
    print("    uv run src/ingest.py")
elif embeddings_count < 100:
    print("  • Very few embeddings. Consider running ingestion:")
    print("    uv run src/ingest.py")
else:
    print("  • Good data volume for testing optimizations")

print()
print("📚 NEXT STEPS:")
print("  1. Apply optimizations: ./apply_optimizations.sh")
print("  2. Or check SQL status: psql $DATABASE_URL -f check_optimization_status.sql")
print("  3. Read guide: OPTIMIZATION_GUIDE.md")
print()
print("════════════════════════════════════════════════════════════")
