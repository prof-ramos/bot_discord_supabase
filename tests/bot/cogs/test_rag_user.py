import pytest
from unittest.mock import AsyncMock, MagicMock
from src.bot.cogs.rag_user import RagUser
import discord

@pytest.fixture
def mock_bot():
    bot = AsyncMock()
    bot.rag_pipeline = AsyncMock()
    return bot

@pytest.fixture
def rag_user_cog(mock_bot):
    settings = MagicMock()
    pipeline = mock_bot.rag_pipeline
    return RagUser(mock_bot, settings, pipeline)

@pytest.fixture
def mock_interaction():
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.user = MagicMock(spec=discord.Member)
    interaction.user.mention = "@user"
    return interaction

@pytest.mark.asyncio
async def test_ask_command_success(rag_user_cog, mock_interaction):
    # Setup successful response from pipeline
    # The code expects a dict, not an object with attributes, based on `response.get("answer", "")`
    response_mock = {
        "answer": "This is the answer.",
        "sources": []
    }

    rag_user_cog.bot.rag_pipeline.ask_with_llm.return_value = response_mock

    # Invoke the command
    await rag_user_cog.ask.callback(rag_user_cog, mock_interaction, "my question")

    # Verification
    mock_interaction.response.defer.assert_called_once_with(thinking=True)
    rag_user_cog.bot.rag_pipeline.ask_with_llm.assert_called_once_with("my question", match_count=4, match_threshold=0.72)
    mock_interaction.followup.send.assert_called_once()

    # Check if the response contains the answer
    call_args = mock_interaction.followup.send.call_args
    assert "This is the answer." in call_args.args[0]

@pytest.mark.asyncio
async def test_ask_command_error(rag_user_cog, mock_interaction):
    # Setup error from pipeline
    rag_user_cog.bot.rag_pipeline.ask_with_llm.side_effect = Exception("Pipeline Error")

    # Invoke
    with pytest.raises(Exception):
        await rag_user_cog.ask.callback(rag_user_cog, mock_interaction, "my question")

    # Verification
    mock_interaction.followup.send.assert_called_with(
        "❌ Erro ao processar consulta. Tente novamente."
    )
