# Guia de Configuração

Este documento explica como configurar o bot usando o arquivo `config.yaml`.

## Setup Inicial

1. Copie o arquivo de exemplo:
```bash
cp config.example.yaml config.yaml
```

2. Edite `config.yaml` conforme suas necessidades

## Principais Configurações

### 1. Modelos LLM

```yaml
llm:
  primary_model: "x-ai/grok-beta"           # Modelo principal
  fallback_model: "x-ai/grok-4.1-fast:free" # Usado se o principal falhar
  temperature: 0.7                           # Criatividade (0.0-1.0)
  max_tokens: 1000                           # Tamanho máximo da resposta
```

**Modelos disponíveis via OpenRouter:**
- `x-ai/grok-beta` - Mais recente e potente
- `x-ai/grok-4.1-fast:free` - Versão gratuita rápida
- `anthropic/claude-3.5-sonnet` - Claude Sonnet
- `openai/gpt-4-turbo` - GPT-4 Turbo
- `meta-llama/llama-3.1-70b-instruct` - Llama 3.1

Para ver todos os modelos: https://openrouter.ai/models

### 2. System Prompt

O system prompt define o comportamento do assistente:

```yaml
llm:
  system_prompt: |
    Você é um assistente jurídico especializado em Direito Administrativo brasileiro.

    Diretrizes:
    - Use as informações do contexto fornecido
    - Seja preciso e objetivo
    - Cite as fontes quando relevante
    - Se não souber, diga claramente
```

**Dicas para um bom system prompt:**
- Seja específico sobre o domínio (ex: jurídico, técnico, acadêmico)
- Defina o tom (formal, casual, técnico)
- Liste comportamentos desejados
- Especifique o formato de resposta

### 3. Parâmetros RAG

```yaml
rag:
  default_match_count: 5        # Quantos chunks buscar
  default_match_threshold: 0.75 # Similaridade mínima (0.0-1.0)
  max_context_chunks: 10        # Máximo de chunks no contexto LLM
  chunk_max_words: 500          # Tamanho dos chunks
```

**Ajuste fino:**
- **match_threshold alto (0.8-0.9)**: Respostas mais precisas, mas pode não encontrar nada
- **match_threshold baixo (0.6-0.7)**: Mais resultados, mas menos relevantes
- **match_count alto**: Mais contexto para o LLM, mas mais tokens gastos

### 4. Comportamento no Discord

```yaml
discord:
  sources_preview:
    slash_command: 3  # Quantas fontes mostrar no /ask
    mention: 2        # Quantas fontes em menções/DMs

  no_context_message: |
    Mensagem quando nada relevante é encontrado
```

### 5. Performance

```yaml
performance:
  enable_cache: true              # Cache de embeddings
  cache_ttl_seconds: 3600         # Tempo de vida do cache (1h)
  log_slow_queries: true          # Log de queries lentas
  slow_query_threshold_ms: 1000   # Limite para considerar lenta
```

### 6. Logging

```yaml
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  save_to_file: true
  log_file: "logs/bot.log"
```

**Níveis de log:**
- `DEBUG`: Tudo (use em desenvolvimento)
- `INFO`: Operações normais + avisos
- `WARNING`: Só avisos e erros
- `ERROR`: Só erros críticos

### 7. Feature Flags

```yaml
features:
  enable_hybrid_search: false      # Busca vetorial + full-text
  enable_thread_responses: false   # Respostas em threads Discord
  enable_analytics: true           # Telemetria e métricas
  development_mode: false          # Modo de desenvolvimento
```

Habilite features experimentais conforme necessário.

## Exemplos de Configuração

### Bot Jurídico (Padrão)
```yaml
llm:
  primary_model: "x-ai/grok-beta"
  temperature: 0.7
  system_prompt: |
    Assistente jurídico especializado em Direito Administrativo...

rag:
  default_match_threshold: 0.75  # Precisão moderada
  max_context_chunks: 10
```

### Bot de Atendimento (Informal)
```yaml
llm:
  primary_model: "x-ai/grok-beta"
  temperature: 0.9  # Mais criativo
  system_prompt: |
    Você é um assistente amigável e prestativo.
    Use linguagem casual e emoji quando apropriado...

discord:
  emojis:
    robot: "😊"
    thinking: "💭"
```

### Bot Técnico (Preciso)
```yaml
llm:
  primary_model: "anthropic/claude-3.5-sonnet"
  temperature: 0.3  # Mais determinístico
  system_prompt: |
    Você é um assistente técnico especializado.
    Forneça respostas precisas e bem fundamentadas...

rag:
  default_match_threshold: 0.85  # Alta precisão
  max_context_chunks: 15         # Mais contexto
```

## Troubleshooting

### Bot não responde
- Verifique se `OPENROUTER_API_KEY` está configurado no `.env`
- Teste o modelo manualmente em https://openrouter.ai/playground

### Respostas imprecisas
- Aumente `rag.default_match_threshold` (ex: 0.75 → 0.80)
- Ajuste o `system_prompt` para ser mais específico
- Revise a qualidade dos documentos ingeridos

### Respostas muito curtas
- Aumente `llm.max_tokens` (ex: 1000 → 2000)
- Ajuste o `system_prompt` para incentivar respostas detalhadas

### Bot muito lento
- Use modelo fallback mais rápido
- Reduza `rag.max_context_chunks`
- Habilite `performance.enable_cache`

## Boas Práticas

1. **Backup**: Mantenha backup do `config.yaml` antes de mudanças grandes
2. **Versionamento**: Comente mudanças importantes no próprio arquivo
3. **Testes**: Teste mudanças em ambiente de desenvolvimento primeiro
4. **Monitoramento**: Habilite logs para acompanhar comportamento
5. **Iteração**: Ajuste incrementalmente, não mude tudo de uma vez

## Referências

- [OpenRouter Models](https://openrouter.ai/models)
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)
- [Discord.py Documentation](https://discordpy.readthedocs.io/)
