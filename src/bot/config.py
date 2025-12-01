import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    discord_token: str
    supabase_url: str
    supabase_service_key: str
    openai_api_key: str
    openrouter_api_key: str
    uploads_dir: str = "data/uploads"
    match_threshold: float = 0.75
    match_count: int = 5


def load_settings() -> Settings:
    discord_token = os.getenv("DISCORD_TOKEN", "")
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")

    if not all([discord_token, supabase_url, supabase_service_key, openai_api_key, openrouter_api_key]):
        missing = [
            name
            for name, val in [
                ("DISCORD_TOKEN", discord_token),
                ("SUPABASE_URL", supabase_url),
                ("SUPABASE_SERVICE_ROLE_KEY", supabase_service_key),
                ("OPENAI_API_KEY", openai_api_key),
                ("OPENROUTER_API_KEY", openrouter_api_key),
            ]
            if not val
        ]
        raise RuntimeError(f"Variáveis faltando no .env: {', '.join(missing)}")

    uploads_dir = os.getenv("UPLOADS_DIR", "data/uploads")
    match_threshold = float(os.getenv("RAG_MATCH_THRESHOLD", 0.75))
    match_count = int(os.getenv("RAG_MATCH_COUNT", 5))

    return Settings(
        discord_token=discord_token,
        supabase_url=supabase_url,
        supabase_service_key=supabase_service_key,
        openai_api_key=openai_api_key,
        openrouter_api_key=openrouter_api_key,
        uploads_dir=uploads_dir,
        match_threshold=match_threshold,
        match_count=match_count,
    )
