"""
Runner autônomo para testar o fluxo /ask enquanto o bot está rodando.

O script executa consultas de teste em loop, chamando diretamente o pipeline RAG
para validar embeddings + Supabase (sem depender da camada Discord).
"""

import asyncio
import os
import time
from datetime import datetime
from typing import List

from src.bot.config import load_settings
from src.bot.rag.embeddings import EmbeddingsProvider
from src.bot.rag.supabase_store import SupabaseStore
from src.bot.rag.pipeline import RagPipeline
from src.bot.utils.logger import BotLogger


# Prompts padrão para os testes; você pode ajustar via AUTOTEST_PROMPTS (CSV).
DEFAULT_PROMPTS = [
    "Quais são as regras para férias de servidores públicos?",
    "Como funciona a licença médica para funcionários estatutários?",
    "Prazo para recurso administrativo em decisão disciplinar?",
]


def load_prompts() -> List[str]:
    raw = os.getenv("AUTOTEST_PROMPTS", "")
    if not raw.strip():
        return DEFAULT_PROMPTS
    return [p.strip() for p in raw.split(",") if p.strip()]


async def build_pipeline():
    settings = load_settings()
    store = SupabaseStore(settings.supabase_url, settings.supabase_service_key)
    embedder = EmbeddingsProvider(api_key=settings.openai_api_key)
    # LLM não é necessário para testar o /ask (focamos em embeddings + Supabase)
    return RagPipeline(store=store, embedder=embedder, llm=None), settings


async def run_once(pipeline: RagPipeline, prompts: List[str], logger: BotLogger, match_count: int, match_threshold: float):
    for prompt in prompts:
        started = time.time()
        try:
            results = await pipeline.ask(prompt, match_count=match_count, match_threshold=match_threshold)
            duration = time.time() - started
            logger.info(
                "Autotest /ask concluído",
                prompt=prompt[:80] + ("..." if len(prompt) > 80 else ""),
                results=len(results),
                duration=f"{duration:.2f}s",
            )
        except Exception as e:
            duration = time.time() - started
            logger.log_error_with_traceback(
                "Autotest /ask falhou",
                e,
                prompt=prompt[:80] + ("..." if len(prompt) > 80 else ""),
                duration=f"{duration:.2f}s",
            )


async def main():
    logger = BotLogger(name="RAG_Bot_Autotest", log_file="logs/auto_tester.log")

    prompts = load_prompts()
    interval = int(os.getenv("AUTOTEST_INTERVAL", "300"))  # em segundos
    runs = int(os.getenv("AUTOTEST_RUNS", "0"))  # 0 = infinito

    pipeline, settings = await build_pipeline()
    match_count = int(os.getenv("AUTOTEST_MATCH_COUNT", settings.match_count))
    match_threshold = float(os.getenv("AUTOTEST_MATCH_THRESHOLD", settings.match_threshold))

    logger.info(
        "Iniciando runner de autotestes /ask",
        prompts=len(prompts),
        interval_seconds=interval,
        runs=("infinito" if runs == 0 else runs),
        match_count=match_count,
        match_threshold=match_threshold,
    )

    iteration = 0
    while True:
        iteration += 1
        logger.info("Rodando suíte de autoteste", iteration=iteration, timestamp=datetime.utcnow().isoformat())
        await run_once(pipeline, prompts, logger, match_count, match_threshold)

        if runs and iteration >= runs:
            logger.info("Finalizando autotestes (limite de execuções atingido)", iterations=iteration)
            break

        await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(main())
