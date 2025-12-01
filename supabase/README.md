# Supabase: documentos jurídicos

Arquitetura para ingestão de documentos, versionamento e uso em RAG.

## Tabelas
- `documents`: metadados principais (status, checksum, categoria, tags, autor).
- `document_versions`: histórico/versionamento e ponte para storage (`storage_key`).
- `ingestion_runs` / `ingestion_items`: controle de execuções em lote.
- `topics` / `document_topics`: taxonomia opcional N:N.
- `embeddings`: chunks e vetores (dim=1536, ajuste conforme modelo).

## RLS e papéis
- Claim JWT `role`: `admin` > `curator` > `reader`. Ausente = `anon`.
- `documents` / `document_versions` / `embeddings`: leitores veem apenas `published`; curators/admin/autor têm acesso total.
- `ingestion_runs` / `ingestion_items`: restrito a curators/admin.
- `topics` / `document_topics`: leitura aberta; escrita por curators/admin.
- Service role sempre ignora RLS (para pipelines de backend).

## Migrations
1. Garanta Supabase CLI configurado (`supabase/config.toml` fora deste repo).
2. Rodar local: `supabase db push` ou `psql "$SUPABASE_DB_URL" -f supabase/migrations/0001_init_documents.sql`.
3. Após popular `embeddings`, rode `ANALYZE embeddings;` para ativar ivfflat com performance.

## Tipos TypeScript
Gere tipos alinhados ao schema para uso no app/bots:
```
supabase gen types typescript --local > supabase/types/database.ts
```
Certifique-se de apontar para a instância com o migration aplicado.

## Fluxo de ingestão sugerido
1) Registrar `documents` (status `pending`/`validated`), salvar `source_path`, `checksum`, `size_bytes`.  
2) Subir arquivo ao storage e registrar em `document_versions.storage_key`.  
3) Aprovar publicações movendo `status` para `published` e setando `published_at`.  
4) Gerar chunks/embeddings e inserir em `embeddings` com `chunk_id` estável.  
5) Logar execuções em `ingestion_runs`/`ingestion_items` (sucesso/erro).

## Notas
- Ajuste a dimensão do vetor (`vector(1536)`) conforme o modelo escolhido.
- Nomes de arquivos devem seguir `snake_case` (veja `data/README.md` para checklist).
- Inclua `role` no JWT de usuários para diferenciar `reader`/`curator`/`admin`; sem isso, usuários autenticados ficam limitados à política de leitor.
