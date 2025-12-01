# Discord Bot + RAG on Supabase

## Project Overview

This is a Discord bot that implements Retrieval-Augmented Generation (RAG) using Supabase as the vector store. The bot allows users to upload documents, store their embeddings in Supabase using pgvector, and then ask questions that are answered using vector similarity search through the stored document chunks.

The project is built with Python and uses Discord.py for the bot interface, Supabase for vector storage and retrieval, and OpenAI/OpenRouter for embeddings and LLM responses.

### Key Technologies and Architecture

- **Python 3.12+**: Main programming language
- **Discord.py**: Framework for building the Discord bot
- **Supabase**: Database backend with pgvector extension for vector storage
- **OpenAI/OpenRouter**: For generating embeddings and LLM responses
- **uv**: Package manager and project runner
- **Streamlit**: Dashboard for monitoring and management

### Core Components

1. **Database Schema** (`supabase/schema.sql`):
   - `rag_documents`: Stores document metadata
   - `rag_chunks`: Stores document chunks with embeddings (vector(1536))
   - Vector index using IVFFlat with cosine similarity for fast retrieval
   - RPC function `rag_search_chunks` for vector search

2. **Bot Core** (`src/bot/`):
   - **Main**: Initializes bot, dependencies, and extensions
   - **Config**: Handles configuration loading from `config.yaml`
   - **RAG Pipeline** (`src/bot/rag/`): Handles document processing, embeddings, storage, and retrieval
   - **Commands** (`src/bot/cogs/`): User and admin slash commands
   - **Events** (`src/bot/events/`): Bot lifecycle events

3. **RAG Pipeline**:
   - Document loaders for various formats (currently .txt/.md)
   - Chunking strategies for document processing
   - Embedding generation using OpenAI
   - Vector storage and retrieval from Supabase

### Configuration

The project uses multiple configuration layers:
- `.env`: Environment variables for secrets and API keys
- `config.yaml`: Application-level configuration (based on `config.example.yaml`)

Key configuration aspects:
- LLM model selection and parameters
- RAG search parameters (match count, threshold, chunk size)
- Discord bot behavior settings
- Performance and logging settings
- Feature flags for experimental functionality

## Building and Running

### Prerequisites
- Python 3.12+
- `uv` package manager
- Supabase project with pgvector enabled
- Required API keys (Discord, Supabase, OpenAI/OpenRouter)

### Setup and Installation

1. **Install Dependencies**:
   ```bash
   uv sync
   ```

2. **Configure Environment**:
   ```bash
   # Create .env file from example
   cp .env.example .env
   # Edit .env with your actual credentials
   ```

3. **Configure Application**:
   ```bash
   # Create config file from example
   cp config.example.yaml config.yaml
   # Edit config.yaml as needed
   ```

4. **Apply Database Schema**:
   ```bash
   # Option 1: Using Supabase CLI
   supabase db push --db-url "<DIRECT_URL>" --include-all --yes
   # Option 2: Run SQL manually in Supabase SQL Editor
   # Use content from supabase/schema.sql
   ```

### Running the Application

#### Nota sobre run.sh

O arquivo `run.sh` é um wrapper de conveniência. Se não existir no seu repositório, você pode executar diretamente:

```bash
# Iniciar o bot
python -m src.bot.main

# Ingestion manual
python -m src.bot.rag.ingest

# Dashboard
streamlit run src/dashboard.py

# Main
python main.py
```

O projeto fornece o script `run.sh` como alternativa opcional com múltiplos modos de execução:

```bash
# Run the Discord bot (opcional)
./run.sh bot

# Run document ingestion (opcional)
./run.sh ingest

# Run Streamlit dashboard (opcional)
./run.sh dashboard

# Run main.py (opcional)
./run.sh main
```

### Discord Commands

The bot provides several slash commands:
- `/add_doc`: Upload documents to be processed into embeddings
- `/ask`: Ask questions using RAG retrieval
- `/rag_stats`: View RAG statistics (admin only)
- `/rag_reset`: Clear RAG tables (admin only)

## Development Conventions

### Code Structure
- `src/bot/`: Main bot application code
- `src/bot/rag/`: RAG-specific functionality
- `src/bot/cogs/`: Discord bot commands and functionality
- `src/bot/events/`: Discord event handlers
- `src/bot/utils/`: Utility functions
- `supabase/`: Database schema and migrations
- `data/uploads/`: Temporary storage for uploaded documents

### Configuration Management
- Secrets are managed through `.env` and are git-ignored
- Application settings use `config.yaml` for non-sensitive configuration
- Multiple LLM providers supported through OpenRouter

### Performance Optimization
The project includes comprehensive performance optimizations:
- Vector index tuning for Supabase free tier
- TOAST storage for large text fields
- JSONB metadata constraints and indexing
- Embedded caching strategies
- Query performance monitoring

### Testing and Quality Assurance
The project uses pytest for testing, with dependencies specified in `pyproject.toml` under the dev group.

## Performance and Monitoring

The project includes extensive performance optimization features:
- Vector index optimization with IVFFlat
- TOAST storage for large text fields
- Storage constraints for JSONB metadata
- Optional table partitioning for large datasets
- Performance monitoring views and dashboards
- Cache hit ratio optimization

## Security Considerations

### Variáveis de Ambiente
- Segredos são gerenciados via `.env` e ignorados no git via `.gitignore`
- Nunca faça commit de `.env` com credenciais reais
- Use vault ou secrets manager em produção

### RLS (Row Level Security)
- Políticas RLS devem estar habilitadas nas tabelas `rag_documents` e `rag_chunks`:
  ```sql
  -- Verificar se RLS está habilitado
  SELECT schemaname, tablename, rowsecurity FROM pg_tables WHERE tablename IN ('rag_documents', 'rag_chunks');

  -- Habilitar RLS (exemplo genérico)
  ALTER TABLE rag_documents ENABLE ROW LEVEL SECURITY;
  ALTER TABLE rag_chunks ENABLE ROW LEVEL SECURITY;
  ```
- Use a `SUPABASE_SERVICE_ROLE_KEY` apenas para operações privilegiadas no backend
- A `SUPABASE_ANON_KEY` é destinada a operações públicas com limitações de segurança

### Diferença entre chaves Supabase
- **anon key**: Chave pública, usada para operações de cliente com permissões limitadas
- **service_role key**: Chave privada com permissões completas, usada apenas no backend

### Operações que exigem service_role key
- Criação/modificação de esquema
- Inserções privilegiadas em `rag_documents` e `rag_chunks`
- Operações administrativas (stats, reset)
- Geração de embeddings e busca vetorial quando usando permissões elevadas

### Validação de Entrada
- Limite o tamanho de arquivos para upload (padrão: 10MB)
- Aceite apenas formatos: `.txt`, `.md`, `.pdf`
- Sanitização de nomes de arquivos para prevenir path traversal
- Verificação de conteúdo para evitar scripts maliciosos
- Validação de extensão e tipo MIME dos arquivos

### Proteção contra ataques
- Implementar rate limiting para prevenir abuso
- Validar e sanitizar todas as consultas vetoriais
- Monitorar uso de API keys e configurar alertas
- Log de atividades suspeitas

### Performance & Storage Optimization
- **TOAST**: Used for large text fields to optimize main table storage
- **JSONB Indexing**: Metadata fields are indexed for fast filtering
- **Caching**: Implement caching strategies for frequent queries
- **Monitoring**: Track query performance and vector search latency

## Troubleshooting

### Erro: "pgvector extension not enabled"
- **Causa**: A extensão pgvector não foi ativada no projeto Supabase
- **Verificação**: Acesse o Supabase Dashboard > SQL Editor e execute:
  ```sql
  SELECT extname FROM pg_extension WHERE extname = 'vector';
  ```
- **Solução**: Execute o seguinte comando no SQL Editor:
  ```sql
  CREATE EXTENSION IF NOT EXISTS vector;
  ```

### Erro: "slow search performance"
- **Causa**: Índice vetorial não foi criado adequadamente ou está desatualizado
- **Verificação**: Execute no SQL Editor:
  ```sql
  SELECT * FROM pg_stat_user_indexes WHERE indexrelname = 'rag_chunks_embedding_idx';
  ```
- **Solução**: Consulte `supabase/schema.sql` para recriar o índice IVFFlat:
  ```sql
  DROP INDEX IF EXISTS rag_chunks_embedding_idx;
  CREATE INDEX rag_chunks_embedding_idx
      ON public.rag_chunks
      USING ivfflat (embedding vector_cosine_ops)
      WITH (lists = 64);  -- Ajuste conforme o número de embeddings: sqrt(total_rows)
  ```

### Erro: "401 Unauthorized" ao conectar ao Discord
- **Verificação**: Confirme se o Bot token no arquivo `.env` está correto:
  ```
  DISCORD_TOKEN=seu_token_aqui
  ```
- **Verificação**: Verifique se o bot tem permissão de ler/escrever mensagens no servidor
- **Solução**: Gere um novo token em Discord Developer Portal e atualize o `.env`

### Cache hit ratio baixo
- **Causa**: Embeddings não estão sendo reutilizados devido a variações nas consultas
- **Verificação**: Verifique a quantidade de chunks no banco vs. requisições:
  ```sql
  SELECT COUNT(*) FROM rag_chunks;
  ```
- **Otimização**: Aumentar `match_count` e ajustar `match_threshold` em `config.yaml` se disponível:
  ```yaml
  rag:
    default_match_count: 5        # Aumente se precisar de mais contexto
    default_match_threshold: 0.75 # Ajuste para controlar a similaridade mínima
  ```

### Erro: "No such file or directory" ao processar uploads
- **Causa**: Caminho de upload configurado incorretamente ou permissões de arquivo
- **Verificação**: Verifique a configuração do diretório de uploads:
  ```python
  # No arquivo de configuração, verifique:
  uploads_dir: "data/uploads"  # deve existir e ter permissões adequadas
  ```
- **Solução**: Crie o diretório e verifique permissões:
  ```bash
  mkdir -p data/uploads
  chmod 755 data/uploads
  ```

### Erro: "RLS policies blocking access"
- **Causa**: Políticas de segurança (Row Level Security) estão bloqueando operações
- **Verificação**: Verifique se RLS está habilitado para tabelas:
  ```sql
  SELECT schemaname, tablename, rowsecurity FROM pg_tables WHERE tablename IN ('rag_documents', 'rag_chunks');
  ```
- **Solução**: Use a `SUPABASE_SERVICE_ROLE_KEY` para operações privilegiadas no backend, ou configure políticas apropriadas para o usuário autenticado

### Erro: "Embedding generation failed"
- **Causa**: Problemas com API Key do OpenAI ou cota excedida
- **Verificação**: Verifique se as credenciais estão corretas:
  ```
  OPENAI_API_KEY=sk-...  # ou OPENROUTER_API_KEY
  ```
- **Solução**: Atualize a API key ou verifique o uso da conta OpenAI/OpenRouter
