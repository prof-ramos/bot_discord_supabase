import os
import secrets
import time
from functools import wraps
from pathlib import Path
from typing import NamedTuple
import discord
from discord import app_commands
from discord.ext import commands

from ..config import Settings
from ..rag.pipeline import RagPipeline
from ..utils.logger import logger


class CommandResult(NamedTuple):
    success: bool
    reason: str | None = None


def log_command_execution(command_name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            start_time = time.time()
            user_id = str(interaction.user.id)
            logger.info(f"Recebido comando {command_name}", user_id=user_id)

            try:
                result = await func(self, interaction, *args, **kwargs)
                duration = time.time() - start_time

                if isinstance(result, CommandResult):
                    if result.success:
                        logger.log_command(user_id, command_name, success=True, duration=duration)
                    else:
                        logger.log_command(
                            user_id,
                            command_name,
                            success=False,
                            duration=duration,
                            reason=result.reason or "unspecified",
                        )
                else:
                    logger.log_command(user_id, command_name, success=True, duration=duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                if not getattr(e, "__logged__", False):
                    logger.log_error_with_traceback(
                        f"Erro ao processar comando {command_name}",
                        e,
                        user_id=user_id
                    )
                logger.log_command(user_id, command_name, success=False, duration=duration, reason="exception_occurred")
                raise

        return wrapper

    return decorator

# Constantes de segurança para uploads
ALLOWED_EXTENSIONS = {'.txt', '.md', '.pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class RagUser(commands.Cog):
    def __init__(self, bot: commands.Bot, settings: Settings, pipeline: RagPipeline):
        self.bot = bot
        self.settings = settings
        self.pipeline = pipeline
        os.makedirs(self.settings.uploads_dir, exist_ok=True)

    @app_commands.command(name="add_doc", description="Adicionar documento ao RAG (upload de arquivo)")
    @log_command_execution("add_doc")
    async def add_doc(self, interaction: discord.Interaction, title: str, file: discord.Attachment):
        user_id = str(interaction.user.id)
        logger.info("Recebido comando add_doc", user_id=user_id, file_name=file.filename, file_size=file.size)

        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            # Validação de tamanho do arquivo
            if file.size > MAX_FILE_SIZE:
                error_msg = f"Arquivo muito grande ({file.size / 1024 / 1024:.1f}MB), máximo é {MAX_FILE_SIZE / 1024 / 1024}MB"
                logger.warning(error_msg, user_id=user_id, file_name=file.filename, file_size=file.size)
                await interaction.followup.send(
                    f"❌ Arquivo muito grande (máx 10MB). Tamanho: {file.size / 1024 / 1024:.1f}MB",
                    ephemeral=True
                )
                return CommandResult(False, "file_too_large")

            # Sanitização do nome do arquivo (previne path traversal)
            safe_filename = Path(file.filename).name  # Remove componentes de diretório
            file_ext = Path(safe_filename).suffix.lower()

            # Validação de extensão
            if file_ext not in ALLOWED_EXTENSIONS:
                error_msg = f"Tipo de arquivo não permitido: {file_ext}"
                logger.warning(error_msg, user_id=user_id, file_name=file.filename, allowed_extensions=list(ALLOWED_EXTENSIONS))
                await interaction.followup.send(
                    f"❌ Tipo de arquivo não permitido. Extensões aceitas: {', '.join(ALLOWED_EXTENSIONS)}",
                    ephemeral=True
                )
                return CommandResult(False, "invalid_file_type")

            # Gera nome único para evitar colisões e ataques
            unique_filename = f"{secrets.token_hex(8)}_{safe_filename}"
            dest = Path(self.settings.uploads_dir) / unique_filename

            # Salva arquivo
            with open(dest, "wb") as f:
                f.write(await file.read())

            logger.info("Arquivo salvo temporariamente", user_id=user_id, original_filename=file.filename, saved_path=str(dest))

            doc_id = await self.pipeline.add_document(
                title=title,
                path=dest,
                metadata={
                    "uploaded_by": str(interaction.user.id),
                    "original_filename": safe_filename
                }
            )
            await interaction.followup.send(f"✅ Documento adicionado! id={doc_id}", ephemeral=True)
            logger.info("Documento adicionado com sucesso", user_id=user_id, doc_id=doc_id)
            return CommandResult(True)
        except Exception as e:
            logger.log_error_with_traceback(
                "Erro ao processar comando add_doc",
                e,
                user_id=user_id,
                file_name=getattr(file, 'filename', 'unknown')
            )
            setattr(e, "__logged__", True)
            await interaction.followup.send("❌ Erro ao processar documento. Tente novamente.", ephemeral=True)
            raise

    @app_commands.command(name="ask", description="Perguntar ao RAG")
    @log_command_execution("ask")
    async def ask(self, interaction: discord.Interaction, query: str, results: int = 4, threshold: float = 0.72):
        user_id = str(interaction.user.id)
        logger.info("Recebido comando ask", user_id=user_id, query_length=len(query), results=results, threshold=threshold)

        await interaction.response.defer(thinking=True)
        results = max(1, min(10, results))
        threshold = max(0.0, min(1.0, threshold))
        try:
            # hits = await self.pipeline.ask(query, match_count=results, match_threshold=threshold)
            # formatted = format_results_for_discord(hits, query)

            # Usando agora o modo LLM
            logger.info("Iniciando pipeline de RAG com LLM", user_id=user_id, query_preview=query[:50]+"..." if len(query) > 50 else query)
            pipeline_start = time.time()
            response = await self.pipeline.ask_with_llm(query, match_count=results, match_threshold=threshold)
            pipeline_duration = time.time() - pipeline_start

            answer = response.get("answer", "")
            sources = response.get("sources", [])

            logger.info("Pipeline de RAG concluído", user_id=user_id, sources_count=len(sources), pipeline_duration=pipeline_duration)

            # Monta resposta
            # 1. Resposta do LLM
            # 2. Fontes (preview)

            final_msg = f"🤖 **Resposta:**\n{answer}\n\n"

            if sources:
                final_msg += "**📚 Fontes utilizadas:**\n"
                for i, r in enumerate(sources[:3]):
                    preview = (r.get("chunk") or "")[:150].replace("\n", " ")
                    sim = r.get("similarity", 0) * 100
                    final_msg += f"- *({sim:.1f}%)* {preview}...\n"
            else:
                final_msg += "*Nenhuma fonte relevante encontrada.*"

            if len(final_msg) > 2000:
                final_msg = final_msg[:1997] + "..."

            await interaction.followup.send(final_msg)
            logger.info("Resposta enviada com sucesso", user_id=user_id, response_length=len(final_msg))
            return CommandResult(True)

        except Exception as e:
            logger.log_error_with_traceback(
                "Erro ao processar comando ask",
                e,
                user_id=user_id,
                query_preview=query[:50]+"..." if len(query) > 50 else query
            )
            await interaction.followup.send("❌ Erro ao processar consulta. Tente novamente.")
            setattr(e, "__logged__", True)
            raise


async def setup(bot: commands.Bot, settings: Settings, pipeline: RagPipeline):
    await bot.add_cog(RagUser(bot, settings, pipeline))
