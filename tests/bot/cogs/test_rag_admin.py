import pytest
from unittest.mock import AsyncMock, MagicMock
from src.bot.cogs.rag_admin import RagAdmin
import discord

@pytest.fixture
def mock_bot():
    return AsyncMock()

@pytest.fixture
def mock_pipeline():
    pipeline = AsyncMock()
    # Assuming stats() returns a dict
    pipeline.stats = AsyncMock(return_value={"documents": 10, "chunks": 50})
    return pipeline

@pytest.fixture
def rag_admin_cog(mock_bot, mock_pipeline):
    # Cog init expects bot, settings, pipeline
    settings = MagicMock()
    return RagAdmin(mock_bot, settings, mock_pipeline)

@pytest.fixture
def mock_interaction():
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    # Mock user for permission checks if needed (though we bypass decorators usually when testing callback directly)
    interaction.user = MagicMock(spec=discord.Member)
    interaction.guild = MagicMock()
    return interaction

@pytest.mark.asyncio
async def test_rag_stats(rag_admin_cog, mock_interaction, mock_pipeline):
    await rag_admin_cog.rag_stats.callback(rag_admin_cog, mock_interaction)

    mock_interaction.response.defer.assert_called_with(ephemeral=True)
    mock_pipeline.stats.assert_called_once()
    mock_interaction.followup.send.assert_called_with("📊 Docs: 10, Chunks: 50", ephemeral=True)

# Testing the reset command involves UI views which is complex to mock fully.
# We can skip it or try a partial test.
