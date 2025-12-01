# Discord Bot + RAG no Supabase

Bot Discord com Supabase (pgvector) como store do RAG. Discord é só a porta de entrada; indexação e busca ficam no banco.

## Requisitos
- Python 3.12+
- `uv` instalado
- Supabase com pgvector
- `.env` com: `DISCORD_TOKEN`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY` (LLM via OpenRouter), `UPLOADS_DIR` (opcional, padrão `data/uploads`), `RAG_MATCH_THRESHOLD` (opcional, padrão `0.75`), `RAG_MATCH_COUNT` (opcional, padrão `5`)

## Setup
```bash
# deps
uv sync

# aplicar schema do RAG no Supabase (direct URL do seu projeto)
supabase db push --db-url "<DIRECT_URL>" --include-all --yes
# ou rodar o conteúdo de supabase/schema.sql no SQL Editor

# rodar bot
./run.sh bot
```

## Configuração
- O LLM é acessado via OpenRouter; defina `OPENROUTER_API_KEY` para habilitar chamadas.
- `UPLOADS_DIR` controla onde os uploads temporários são salvos (padrão `data/uploads`).
- `RAG_MATCH_THRESHOLD` e `RAG_MATCH_COUNT` ajustam o comportamento da busca vetorial.

## Comandos (slash)
- `/add_doc` — upload -> chunks -> embeddings -> Supabase
- `/ask` — busca vetorial via RPC `rag_search_chunks`
- `/rag_stats` — conta docs/chunks (admin/manage_guild)
- `/rag_reset` — limpa tabelas do RAG (admin/manage_guild)

## Estrutura
- `supabase/schema.sql` — `rag_documents`, `rag_chunks`, índice IVFFlat (lists=64), função `rag_search_chunks`
- `supabase/seed.sql` — seed opcional
- `src/bot/main.py` — inicia bot e injeta pipeline
- `src/bot/rag/` — loaders, chunkers, embeddings, store, pipeline
- `src/bot/cogs/` — comandos user/admin; `events/` — on_ready/on_message

## Notas
- Loader atual lê .txt/.md; PDFs precisam conversão/extensão.
- Uploads temporários em `data/uploads/` (ignorada no git).
- Índice vetorial ajustado para free tier (lists=64); se >10k chunks, aumente lists conforme crescer.

## Segurança
- `.env` já ignorado em `.gitignore`. Não faça push com segredos.
