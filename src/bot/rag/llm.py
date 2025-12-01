from openai import AsyncOpenAI

class LLMClient:
    def __init__(self, api_key: str, model: str = "x-ai/grok-4.1-fast:free"):
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        self.model = model

    async def generate_answer(self, query: str, context: list[str]) -> str:
        """Gera uma resposta baseada na query e no contexto fornecido."""

        system_prompt = (
            "Você é um assistente útil e preciso. "
            "Use as informações de contexto abaixo para responder à pergunta do usuário. "
            "Se a resposta não estiver no contexto, diga que não sabe, mas tente ser útil. "
            "Responda no mesmo idioma da pergunta (provavelmente Português)."
        )

        context_str = "\n\n---\n\n".join(context)
        user_message = f"Contexto:\n{context_str}\n\nPergunta: {query}"

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
            return response.choices[0].message.content or "Desculpe, não consegui gerar uma resposta."
        except Exception as e:
            return f"Erro ao gerar resposta: {e}"
