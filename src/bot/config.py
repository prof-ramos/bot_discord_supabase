import os
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class LLMConfig:
    """Configuração de LLM (Large Language Model) carregada do config.yaml.

    Attributes:
        primary_model: Modelo LLM principal a ser usado (ex: 'x-ai/grok-4.1-fast:free')
        fallback_model: Modelo LLM alternativo em caso de falha do primário
        temperature: Temperatura de geração (0.0-2.0, maior = mais criativo)
        max_tokens: Número máximo de tokens na resposta gerada
        system_prompt: Prompt de sistema que define o comportamento do LLM
    """
    primary_model: str
    fallback_model: str
    temperature: float
    max_tokens: int
    system_prompt: str


@dataclass
class RAGConfig:
    """Configuração do pipeline RAG (Retrieval-Augmented Generation).

    Attributes:
        default_match_count: Número padrão de chunks a retornar nas buscas (ex: 5)
        default_match_threshold: Threshold mínimo de similaridade (0.0-1.0, ex: 0.75)
        max_context_chunks: Máximo de chunks a incluir no contexto do LLM
        chunk_max_words: Tamanho máximo de cada chunk em palavras (ex: 500)
        chunk_strategy: Estratégia de chunking ('sentence_based' ou 'fixed')
    """
    default_match_count: int
    default_match_threshold: float
    max_context_chunks: int
    chunk_max_words: int
    chunk_strategy: str


@dataclass
class OpenAIConfig:
    """Configuração da API OpenAI para embeddings.

    Attributes:
        embedding_model: Modelo de embedding a ser usado (ex: 'text-embedding-3-small')
        max_concurrent_requests: Limite de requisições simultâneas para controle de rate limit
    """
    embedding_model: str
    max_concurrent_requests: int


@dataclass
class DiscordConfig:
    """Configuração de comportamento do bot Discord.

    Attributes:
        command_prefix: Prefixo para comandos texto (ex: '!')
        operation_timeout: Timeout em segundos para operações do bot (ex: 60)
        max_response_length: Tamanho máximo da resposta em caracteres (limite Discord: 2000)
        no_context_message: Mensagem exibida quando não há contexto relevante
        sources_preview: Dict com número de previews de fontes para 'slash_command' e 'mention'
        emojis: Dict com emojis usados nas respostas (ex: {'thinking': '🤔'})
    """
    command_prefix: str
    operation_timeout: int
    max_response_length: int
    no_context_message: str
    sources_preview: dict  # Contains 'slash_command' and 'mention' keys
    emojis: dict


@dataclass
class PerformanceConfig:
    """Configuração de performance e caching.

    Attributes:
        enable_cache: Habilita caching de embeddings e respostas LLM
        cache_ttl_seconds: Tempo de vida do cache em segundos (ex: 3600 = 1h)
        log_slow_queries: Registra queries lentas nos logs
        slow_query_threshold_ms: Threshold em ms para considerar query lenta (ex: 1000)
        rate_limit: Dict com limites de taxa ('embeddings_per_minute', 'llm_requests_per_minute')
    """
    enable_cache: bool
    cache_ttl_seconds: int
    log_slow_queries: bool
    slow_query_threshold_ms: int
    rate_limit: dict  # Contains 'embeddings_per_minute' and 'llm_requests_per_minute'


@dataclass
class FilesConfig:
    """Configuração de manipulação de arquivos.

    Attributes:
        uploads_dir: Diretório para salvar uploads (ex: 'data/uploads')
        allowed_extensions: Lista de extensões permitidas (ex: ['.txt', '.md', '.pdf'])
        max_file_size_mb: Tamanho máximo de arquivo em MB (ex: 10)
        cleanup_after_processing: Remove arquivos temporários após processamento
    """
    uploads_dir: str
    allowed_extensions: List[str]
    max_file_size_mb: int
    cleanup_after_processing: bool


@dataclass
class Settings:
    """Configuração unificada combinando secrets do .env e settings do config.yaml.

    Esta classe centraliza todas as configurações da aplicação, separando:
    - Secrets sensíveis (API keys, tokens) vindos do .env
    - Configurações de runtime vindas do config.yaml

    Attributes:
        discord_token: Token do bot Discord (do .env)
        supabase_url: URL do projeto Supabase (do .env)
        supabase_service_key: Service role key do Supabase (do .env)
        openai_api_key: API key da OpenAI para embeddings (do .env)
        openrouter_api_key: API key do OpenRouter para LLM (do .env)
        llm: Configuração do LLM (do config.yaml)
        rag: Configuração do pipeline RAG (do config.yaml)
        openai: Configuração da OpenAI (do config.yaml)
        discord: Configuração do Discord (do config.yaml)
        performance: Configuração de performance (do config.yaml)
        files: Configuração de arquivos (do config.yaml)
    """
    # Secrets from .env
    discord_token: str
    supabase_url: str
    supabase_service_key: str
    openai_api_key: str
    openrouter_api_key: str

    # Runtime config from config.yaml
    llm: LLMConfig
    rag: RAGConfig
    openai: OpenAIConfig
    discord: DiscordConfig
    performance: PerformanceConfig
    files: FilesConfig


def load_settings() -> Settings:
    """Carrega configurações unificadas do .env e config.yaml.

    Este loader centraliza toda a configuração da aplicação:
    1. Carrega secrets sensíveis do arquivo .env (API keys, tokens)
    2. Carrega configurações de runtime do config.yaml
    3. Valida que todas as variáveis obrigatórias estão presentes
    4. Retorna objeto Settings unificado e tipado

    Returns:
        Settings: Objeto com todas as configurações carregadas e validadas

    Raises:
        RuntimeError: Se config.yaml não existir ou variáveis .env obrigatórias estiverem faltando
        yaml.YAMLError: Se config.yaml tiver sintaxe inválida
        KeyError: Se config.yaml estiver faltando seções obrigatórias

    Example:
        >>> settings = load_settings()
        >>> print(settings.llm.primary_model)
        'x-ai/grok-4.1-fast:free'
    """
    # Load YAML config
    config_path = Path(__file__).parent.parent.parent / "config.yaml"
    if not config_path.exists():
        raise RuntimeError(
            f"Arquivo de configuração não encontrado: {config_path}\n"
            f"Crie o arquivo config.yaml a partir do config.example.yaml"
        )

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise RuntimeError(f"Erro ao parsear config.yaml: {e}")

    # Validate required env vars
    required_env = {
        "DISCORD_TOKEN": os.getenv("DISCORD_TOKEN"),
        "SUPABASE_URL": os.getenv("SUPABASE_URL"),
        "SUPABASE_SERVICE_ROLE_KEY": os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY"),
    }

    missing = [name for name, val in required_env.items() if not val]
    if missing:
        raise RuntimeError(
            f"Variáveis de ambiente obrigatórias faltando no .env: {', '.join(missing)}\n"
            f"Crie o arquivo .env a partir do .env.example e preencha as variáveis"
        )

    # Validate required YAML sections
    required_sections = ["llm", "rag", "openai", "discord", "performance", "files"]
    missing_sections = [s for s in required_sections if s not in config]
    if missing_sections:
        raise RuntimeError(
            f"Seções obrigatórias faltando no config.yaml: {', '.join(missing_sections)}"
        )

    return Settings(
        # Secrets from .env
        discord_token=required_env["DISCORD_TOKEN"],
        supabase_url=required_env["SUPABASE_URL"],
        supabase_service_key=required_env["SUPABASE_SERVICE_ROLE_KEY"],
        openai_api_key=required_env["OPENAI_API_KEY"],
        openrouter_api_key=required_env["OPENROUTER_API_KEY"],

        # Config from YAML
        llm=LLMConfig(**config["llm"]),
        rag=RAGConfig(**config["rag"]),
        openai=OpenAIConfig(**config["openai"]),
        discord=DiscordConfig(**config["discord"]),
        performance=PerformanceConfig(**config["performance"]),
        files=FilesConfig(**config["files"]),
    )
