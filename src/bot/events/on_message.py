import discord
from discord.ext import commands
from ..rag.pipeline import RagPipeline

async def setup(bot: commands.Bot, pipeline: RagPipeline):
    @bot.event
    async def on_message(message: discord.Message):
        # Ignora mensagens do próprio bot
        if message.author == bot.user:
            return

        # Verifica se deve responder:
        # 1. É DM
        # 2. Menciona o bot na guilda

        should_respond = False
        if isinstance(message.channel, discord.DMChannel):
            should_respond = True
        elif bot.user in message.mentions:
            should_respond = True

        if should_respond:
            # Processa como pergunta ao RAG
            # Mostra "digitando..."
            async with message.channel.typing():
                try:
                    # Remove a menção do texto se houver
                    query = message.content.replace(f"<@{bot.user.id}>", "").strip()
                    if not query:
                         await message.reply("Olá! Como posso ajudar?")
                         return

                    response = await pipeline.ask_with_llm(query)
                    answer = response.get("answer", "")
                    sources = response.get("sources", [])

                    # Formata resposta simples (sem embed complexo, similar ao slash command)
                    final_msg = f"{answer}\n\n"

                    if sources:
                        final_msg += "**Fontes:**\n"
                        for i, r in enumerate(sources[:2]): # Limita a 2 fontes para não poluir chat
                            preview = (r.get("chunk") or "")[:100].replace("\n", " ")
                            sim = r.get("similarity", 0) * 100
                            final_msg += f"- *({sim:.0f}%)* {preview}...\n"

                    if len(final_msg) > 2000:
                        final_msg = final_msg[:1997] + "..."

                    await message.reply(final_msg)

                except Exception as e:
                    await message.reply(f"Ocorreu um erro ao processar sua mensagem: {e}")

        # Processa comandos normais (se houver prefix commands)
        await bot.process_commands(message)
