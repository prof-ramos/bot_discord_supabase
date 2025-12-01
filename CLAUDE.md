# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Discord bot with RAG (Retrieval-Augmented Generation) using Supabase (pgvector) as the vector store. Discord serves as the interface; document indexing and semantic search happen in the database. The bot now includes LLM-powered response generation.

**Tech Stack:** Python 3.12+, Discord.py, Supabase (PostgreSQL + pgvector), OpenAI embeddings (text-embedding-ada-002), OpenRouter LLM (Grok 4.1 Fast), Streamlit dashboard

## Development Commands

### Running the Bot
```bash
# Start Discord bot
./run.sh bot
# or directly: uv run src/bot/main.py

# Ingest documents into RAG system
./run.sh ingest
# or directly: uv run src/ingest.py

# Run Streamlit dashboard
./run.sh dashboard
# or directly: streamlit run src/dashboard.py
```

### Database Operations
```bash
# Apply migrations (using direct URL from Supabase project settings)
supabase db push --db-url "<DIRECT_URL>" --include-all --yes

# Apply performance optimizations
./apply_optimizations.sh

# Check optimization status
uv run check_status.py
```

### Testing & Development
```bash
# Install dependencies (including dev dependencies)
uv sync

# Run tests (if available)
uv run pytest

# Create configuration files from templates
cp .env.example .env
cp config.example.yaml config.yaml

# Configure .env with your API keys:
# - DISCORD_TOKEN, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
# - OPENAI_API_KEY, OPENROUTER_API_KEY

# Configure config.yaml with:
# - LLM models (primary and fallback)
# - System prompt customization
# - RAG parameters, Discord behavior, etc.
```

## Architecture

### Core Components

**Bot Layer** (`src/bot/`)
- `main.py`: Bot initialization, loads cogs and event handlers
- `config.py`: Environment configuration loader
- `cogs/`: Discord slash commands
  - `rag_user.py`: User commands (`/ask`, `/add_doc`)
  - `rag_admin.py`: Admin commands (`/rag_stats`, `/rag_reset`)
- `events/`: Event handlers (`on_ready`, `on_message`)

**RAG Pipeline** (`src/bot/rag/`)
- `pipeline.py`: Orchestrates the full RAG flow (load → chunk → embed → store → LLM generation)
  - `add_document()`: Full ingestion pipeline
  - `ask()`: Vector search only (returns raw chunks)
  - `ask_with_llm()`: Vector search + LLM answer generation
- `loaders.py`: Document loading (`.txt`, `.md`)
- `chunkers.py`: Text chunking (sentence-based, word limit)
- `embeddings.py`: OpenAI embedding generation (text-embedding-ada-002)
- `llm.py`: LLM client for answer generation via OpenRouter (Grok 4.1 Fast)
- `supabase_store.py`: Vector storage and semantic search
- `supabase_client.py`: Supabase client initialization

**Standalone Scripts** (`src/`)
- `ingest.py`: Batch document ingestion with optimized batching (100 embeddings/request, 100 records/insert)
- `bot.py`: Alternative bot entry point (functionally equivalent to `bot/main.py`)
- `dashboard.py`: Streamlit performance dashboard

### Database Schema

**Key Tables:**
- `documents`: Document metadata (title, slug, category, status, tags, checksum)
- `document_versions`: Version history with checksums and storage keys
- `embeddings`: Vector embeddings (document_id, chunk_id, content, embedding vector(1536), metadata JSONB)
- `ingestion_runs`: Batch ingestion tracking
- `ingestion_items`: Individual file processing status

**Optimizations Applied:**
- IVFFlat index on embeddings (lists=200, optimized for ~2K embeddings)
- GIN index on metadata JSONB for fast filtering
- Partial indexes on status + created_at
- TOAST optimization for large text fields (EXTERNAL storage)
- RLS policies with service role bypass for bot operations

**Key Functions:**
- `match_documents(query_embedding, match_threshold, match_count, filter_status, filter_category, filter_tags)`: Enhanced semantic search with filters
- `hybrid_search_documents()`: Combines vector + full-text search
- `batch_match_documents()`: Multi-query optimization

### Performance Characteristics

**Current Database Stats** (as of initial setup):
- ~2,206 embeddings across 119 documents
- Expected search latency: <100ms (optimized), ~500ms (unoptimized)
- Storage: ~10-15MB with TOAST compression

**Optimization Strategy:**
- Batch embedding generation: 100 chunks per OpenAI API call
- Batch database inserts: 100 records per transaction
- IVFFlat index tuned for dataset size (lists ≈ √rows * 4)
- Service role bypasses RLS for 10x performance gain on bot queries

### Migration System

Migrations in `supabase/migrations/` follow numbered sequence:
- `0001_init_documents.sql`: Base schema (tables, enums, RLS)
- `0002_match_documents.sql`: Basic vector search function
- `0003_optimize_vector_index.sql`: Rebuild index with optimal parameters
- `0004_add_missing_indexes.sql`: GIN, partial, covering indexes
- `0005_storage_optimization.sql`: TOAST + autovacuum tuning
- `0006_table_partitioning.sql`: Table partitioning for scalability (optional - skip for small datasets <10K docs)
- `0007_optimize_match_function.sql`: Enhanced search with filters
- `0008_optimize_rls_policies.sql`: RLS bypass for service role
- `0009_performance_monitoring.sql`: Performance dashboard views

**Important:** Apply migrations sequentially. Use `apply_optimizations.sh` for automated deployment or run via Supabase Dashboard SQL Editor.

## Code Patterns

### RAG Query Flow (LLM-Enhanced)
1. User calls `/ask` command, mentions bot, or sends DM
2. Bot generates query embedding via OpenAI (text-embedding-ada-002)
3. RPC call to `match_documents()` with embedding vector
4. Supabase performs vector similarity search using IVFFlat index
5. Returns top-k most relevant chunks with metadata
6. **LLM generates natural language answer** from query + context chunks (via OpenRouter/Grok)
7. Bot sends formatted response with answer + source previews to Discord

**Note:** The bot now uses `ask_with_llm()` by default instead of raw chunk retrieval

### Document Ingestion Flow
1. Upload document via `/add_doc` or batch via `ingest.py`
2. File loaded and checksummed
3. Text chunked (max 500 words, sentence-aware)
4. Embeddings generated in batches (100 at a time)
5. Inserted to `documents` + `embeddings` tables
6. Tracking recorded in `ingestion_runs`/`ingestion_items`

### Batch Processing Pattern
```python
# Used extensively in ingest.py for performance
for i in range(0, len(items), BATCH_SIZE):
    batch = items[i:i + BATCH_SIZE]
    # Process batch in single API/DB call
```

## Configuration Notes

### Configuration Files

The project uses two configuration files:

1. **`.env`** - Sensitive credentials (API keys, tokens)
2. **`config.yaml`** - Application behavior and settings

**Environment Variables** (`.env`):
- `DISCORD_TOKEN`: Bot token from Discord Developer Portal
- `SUPABASE_URL`: Project URL (e.g., `https://xxx.supabase.co`)
- `SUPABASE_SERVICE_ROLE_KEY`: Service role key (bypasses RLS, use for backend)
- `SUPABASE_ANON_KEY`: Anon key (RLS-enforced, not currently used)
- `OPENAI_API_KEY`: For text-embedding-ada-002 embeddings
- `OPENROUTER_API_KEY`: For LLM answer generation (OpenRouter API)
- Optional: `UPLOADS_DIR`, `RAG_MATCH_THRESHOLD`, `RAG_MATCH_COUNT`

**Application Settings** (`config.yaml`):
- **LLM Configuration**: Primary/fallback models, temperature, max_tokens, system prompt
- **RAG Parameters**: Match count/threshold, chunking strategy, context limits
- **Discord Behavior**: Response format, emojis, timeouts, source previews
- **Database**: Connection pool, query timeout, vector index settings
- **Performance**: Caching, rate limiting, slow query logging
- **File Processing**: Upload directory, allowed extensions, size limits
- **Logging**: Level, format, file rotation settings
- **Feature Flags**: Enable/disable experimental features

The `config.yaml` allows runtime customization without code changes. Critical settings like the system prompt and model selection can be adjusted per deployment.

**Discord Bot Permissions:**
- Requires slash commands enabled
- Admin commands check `administrator` or `manage_guild` permissions
- Intents: `messages`, `guilds` (default intents enabled)
- Bot responds to: DMs, mentions in guilds, `/ask` slash command

## Data Flow

**Document Storage:**
- Original files: `data/` directory (markdown files organized by category)
- Uploads: `data/uploads/` (temporary, gitignored)
- Embeddings: Stored in Supabase `embeddings` table
- Metadata: Stored in `documents` table with JSONB tags/metadata

**Semantic Search Process:**
- Query → embedding(1536) → IVFFlat scan → cosine similarity → top-k results
- Filters applied via metadata JSONB (GIN indexed)
- Results include chunk content + document context

## Bot Interaction Modes

The bot supports three interaction methods:

1. **Slash Command (`/ask`)**: Explicit RAG query with configurable parameters
   - Syntax: `/ask query:"question" results:4 threshold:0.72`
   - Shows LLM answer + top source previews
   - Parameters: `results` (1-10), `threshold` (0.0-1.0)

2. **Direct Mention**: Tag bot in any channel (`@BotName question`)
   - Processes message as RAG query
   - Shows LLM answer + 2 source previews (condensed for chat)
   - Removes mention from query text before processing

3. **Direct Message (DM)**: Send questions directly to bot
   - All DMs automatically processed as RAG queries
   - Same LLM-powered responses as mentions

**LLM Integration:**
- Model: Grok 4.1 Fast via OpenRouter (free tier: `x-ai/grok-4.1-fast:free`)
- Base URL: `https://openrouter.ai/api/v1`
- System prompt: Portuguese-language assistant with context grounding
- Fallback: If no relevant context found, LLM attempts to answer without RAG context
- Error handling: Returns user-friendly error messages on API failures

**Dual-API Architecture:**
- **OpenAI**: Used exclusively for embeddings (text-embedding-ada-002)
- **OpenRouter**: Used exclusively for LLM text generation (Grok 4.1 Fast)
- This separation allows using free/cheaper LLM providers while maintaining high-quality embeddings

## Known Behaviors

**Chunking Strategy:**
- Splits on sentence boundaries (preserves semantic coherence)
- Max 500 words per chunk (configurable via `MAX_CHUNK_WORDS`)
- Overlap not implemented (each sentence appears in exactly one chunk)

**Index Tuning:**
- IVFFlat `lists` parameter set to 200 (optimal for ~2K embeddings)
- Should be recalculated when dataset grows significantly (lists ≈ √rows * 4)
- Trade-off: lower lists = slower insert, faster query; higher lists = faster insert, slower query

**Error Handling:**
- Batch operations fall back to individual processing on failure
- Failed ingestions tracked in `ingestion_items.status='failed'`
- Zero vectors used as placeholder for failed embeddings (rare edge case)

## Performance Optimization Status

Current state tracked in `READY_TO_APPLY.md` and `OPTIMIZATION_SUMMARY.md`:
- Base schema applied (0001, 0002)
- Performance optimizations partially applied (0003-0009)
- Run `uv run check_status.py` to verify current optimization state
- Full optimization expected to reduce query time by 5-10x

**Monitoring:**
- Performance dashboard: `SELECT * FROM performance_dashboard;`
- Query logs: `query_performance_log` table
- Storage stats: `table_storage_stats` view
