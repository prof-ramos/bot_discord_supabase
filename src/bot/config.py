import os
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class LLMConfig:
    """LLM configuration from config.yaml"""
    primary_model: str
    fallback_model: str
    temperature: float
    max_tokens: int
    system_prompt: str


@dataclass
class RAGConfig:
    """RAG pipeline configuration from config.yaml"""
    default_match_count: int
    default_match_threshold: float
    max_context_chunks: int
    chunk_max_words: int
    chunk_strategy: str


@dataclass
class DiscordConfig:
    """Discord bot behavior configuration from config.yaml"""
    command_prefix: str
    operation_timeout: int
    max_response_length: int
    no_context_message: str
    sources_preview: dict  # Contains 'slash_command' and 'mention' keys
    emojis: dict


@dataclass
class PerformanceConfig:
    """Performance and caching configuration from config.yaml"""
    enable_cache: bool
    cache_ttl_seconds: int
    log_slow_queries: bool
    slow_query_threshold_ms: int
    rate_limit: dict  # Contains 'embeddings_per_minute' and 'llm_requests_per_minute'


@dataclass
class FilesConfig:
    """File handling configuration from config.yaml"""
    uploads_dir: str
    allowed_extensions: List[str]
    max_file_size_mb: int
    cleanup_after_processing: bool


@dataclass
class Settings:
    """Unified configuration combining .env secrets and config.yaml settings"""
    # Secrets from .env
    discord_token: str
    supabase_url: str
    supabase_service_key: str
    openai_api_key: str
    openrouter_api_key: str

    # Runtime config from config.yaml
    llm: LLMConfig
    rag: RAGConfig
    discord: DiscordConfig
    performance: PerformanceConfig
    files: FilesConfig


def load_settings() -> Settings:
    """Load unified settings from .env and config.yaml"""

    # Load YAML config
    config_path = Path(__file__).parent.parent.parent / "config.yaml"
    if not config_path.exists():
        raise RuntimeError(f"Configuration file not found: {config_path}")

    with open(config_path) as f:
        config = yaml.safe_load(f)

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
        raise RuntimeError(f"Variáveis faltando no .env: {', '.join(missing)}")

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
        discord=DiscordConfig(**config["discord"]),
        performance=PerformanceConfig(**config["performance"]),
        files=FilesConfig(**config["files"]),
    )
