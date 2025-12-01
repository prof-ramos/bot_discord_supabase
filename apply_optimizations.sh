#!/bin/bash

# Apply Supabase Performance Optimizations
# This script applies all optimization migrations in the correct order

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     SUPABASE PERFORMANCE OPTIMIZATION INSTALLER           ║"
echo "║                                                            ║"
echo "║  This script will apply all performance optimizations     ║"
echo "║  to your Supabase database.                               ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo "Please create .env from .env.example and configure your settings"
    exit 1
fi

# Load environment variables
source .env

# Add libpq to PATH for psql (macOS Homebrew)
export PATH="/opt/homebrew/opt/libpq/bin:$PATH"


# Check required variables
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
    echo -e "${RED}❌ Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set${NC}"
    exit 1
fi

echo -e "${BLUE}📋 Configuration:${NC}"
echo "  Supabase URL: $SUPABASE_URL"
echo "  Service Key: ${SUPABASE_SERVICE_ROLE_KEY:0:20}..."
echo ""

# Ask for confirmation
echo -e "${YELLOW}⚠️  This will apply the following optimizations:${NC}"
echo "  1. Vector index optimization"
echo "  2. Missing indexes"
echo "  3. Storage optimization (TEXT, JSONB, TOAST)"
echo "  4. Enhanced search functions"
echo "  5. RLS policy optimization"
echo "  6. Performance monitoring setup"
echo ""
echo "  ${BLUE}Note: Partitioning (0006) will be skipped by default${NC}"
echo "        Enable it manually if you have > 100k embeddings"
echo ""

read -p "Continue? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Create backup recommendation
echo ""
echo -e "${YELLOW}💡 Recommendation: Backup your database first!${NC}"
read -p "Have you backed up your database? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}⚠️  Please backup first. Aborting.${NC}"
    exit 0
fi

# Function to apply migration
apply_migration() {
    local file=$1
    local description=$2

    echo ""
    echo -e "${BLUE}➜ Applying: $description${NC}"
    echo "  File: $file"

    if [ ! -f "$file" ]; then
        echo -e "${RED}  ❌ File not found: $file${NC}"
        return 1
    fi

    # Prioritize Supabase CLI (handles auth/connection better), fallback to psql
    if command -v supabase &> /dev/null; then
        echo "  Using Supabase CLI..."
        OUTPUT=$(supabase db execute -f "$file" 2>&1)
        if echo "$OUTPUT" | grep -i -q "error"; then
            echo -e "${RED}  ❌ Failed${NC}"
            echo -e "${RED}$OUTPUT${NC}"
            return 1
        fi
    elif command -v psql &> /dev/null; then
        echo "  Using psql (remote DB)..."
        PROJECT_REF=$(echo $SUPABASE_URL | sed -E 's|https://([^.]+)\.supabase\.co|\1|')
        DB_URL="postgresql://postgres:$SUPABASE_SERVICE_ROLE_KEY@db.$PROJECT_REF.supabase.co:5432/postgres"
        OUTPUT=$(psql "$DB_URL" -f "$file" -v ON_ERROR_STOP=1 -q 2>&1)
        if echo "$OUTPUT" | grep -iq "error\\|fatal\\|failed"; then
            echo -e "${RED}  ❌ Failed${NC}"
            echo -e "${RED}$OUTPUT${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}  ⚠️  Neither 'psql' nor 'supabase' CLI found${NC}"
        echo "  Install psql: brew install libpq"
        echo "  Or apply manually via Supabase Dashboard SQL Editor"
        read -p "Press Enter when done (manual apply)..."
        return 0
    fi

    echo -e "${GREEN}  ✅ Success${NC}"
    return 0
}

# Apply migrations in order
MIGRATIONS_DIR="supabase/migrations"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Starting migration process..."
echo "════════════════════════════════════════════════════════════"

# 0003: Vector index optimization
apply_migration "$MIGRATIONS_DIR/0003_optimize_vector_index.sql" \
    "Vector Index Optimization"

# 0004: Missing indexes
apply_migration "$MIGRATIONS_DIR/0004_add_missing_indexes.sql" \
    "Missing Indexes"

# 0005: Storage optimization
apply_migration "$MIGRATIONS_DIR/0005_storage_optimization.sql" \
    "Storage Optimization (TEXT, JSONB, TOAST)"

# 0007: Optimized functions
apply_migration "$MIGRATIONS_DIR/0007_optimize_match_function.sql" \
    "Enhanced Search Functions"

# 0008: RLS optimization
apply_migration "$MIGRATIONS_DIR/0008_optimize_rls_policies.sql" \
    "RLS Policy Optimization"

# 0009: Monitoring
apply_migration "$MIGRATIONS_DIR/0009_performance_monitoring.sql" \
    "Performance Monitoring Setup"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Post-migration tasks..."
echo "════════════════════════════════════════════════════════════"

# Run ANALYZE
echo ""
echo -e "${BLUE}➜ Running ANALYZE on tables...${NC}"
if command -v psql &> /dev/null; then
    PROJECT_REF=$(echo $SUPABASE_URL | sed -E 's|https://([^.]+)\.supabase\.co|\1|')
    DB_URL="postgresql://postgres:$SUPABASE_SERVICE_ROLE_KEY@db.$PROJECT_REF.supabase.co:5432/postgres"
    psql "$DB_URL" -c "ANALYZE embeddings; ANALYZE documents;"
    echo -e "${GREEN}  ✅ Success${NC}"
elif command -v supabase &> /dev/null; then
    supabase db execute --sql "ANALYZE embeddings; ANALYZE documents;"
    echo -e "${GREEN}  ✅ Success${NC}"
else
    echo -e "${YELLOW}  ⚠️  Please run manually:${NC}"
    echo "  ANALYZE embeddings;"
    echo "  ANALYZE documents;"
fi

# Success message
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    ✅ COMPLETED!                           ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}All optimizations applied successfully!${NC}"
echo ""
echo "📊 Next Steps:"
echo ""
echo "1. Verify installation:"
echo "   Run: SELECT * FROM performance_dashboard;"
echo ""
echo "2. Update your application code:"
echo "   cp src/bot_optimized.py src/bot.py"
echo "   cp src/ingest_optimized.py src/ingest.py"
echo ""
echo "3. Test the bot:"
echo "   uv run src/bot.py"
echo ""
echo "4. Monitor performance:"
echo "   Check: supabase/migrations/README.md"
echo "   Guide: OPTIMIZATION_GUIDE.md"
echo ""
echo "Expected improvements:"
echo "  • Vector search: 500-1000ms → 50-100ms (10x faster)"
echo "  • Storage usage: 30-40% reduction"
echo "  • Bot response: 1.5-2s → 200-400ms (5-8x faster)"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo ""

# Optional: Run verification
read -p "Run verification query? (y/N) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if command -v psql &> /dev/null; then
        PROJECT_REF=$(echo $SUPABASE_URL | sed -E 's|https://([^.]+)\.supabase\.co|\1|')
        DB_URL="postgresql://postgres:$SUPABASE_SERVICE_ROLE_KEY@db.$PROJECT_REF.supabase.co:5432/postgres"
        psql "$DB_URL" -c "SELECT * FROM performance_dashboard;"
    elif command -v supabase &> /dev/null; then
        supabase db execute --sql "SELECT * FROM performance_dashboard;"
    fi
fi


echo ""
echo "Done! 🚀"
