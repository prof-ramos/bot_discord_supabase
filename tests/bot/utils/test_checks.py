import pytest
from unittest.mock import MagicMock, AsyncMock
from src.bot.utils.checks import is_rag_admin
import discord

@pytest.fixture
def mock_interaction():
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.response = AsyncMock()
    interaction.user = MagicMock(spec=discord.Member)
    interaction.guild = MagicMock()
    return interaction

def extract_predicate(check_decorator):
    # app_commands.check returns a decorator.
    # If we apply it to a coroutine function, it attaches the check to __discord_app_commands_checks__.

    async def dummy_coro():
        pass

    decorated = check_decorator(dummy_coro)

    if hasattr(decorated, '__discord_app_commands_checks__'):
        return decorated.__discord_app_commands_checks__[0]

    raise ValueError("Could not extract predicate from check decorator")

@pytest.mark.asyncio
async def test_is_rag_admin_success_administrator(mock_interaction):
    mock_interaction.user.guild_permissions.administrator = True
    mock_interaction.user.guild_permissions.manage_guild = False

    check = is_rag_admin()
    predicate = extract_predicate(check)

    result = await predicate(mock_interaction)
    assert result is True

@pytest.mark.asyncio
async def test_is_rag_admin_success_manage_guild(mock_interaction):
    mock_interaction.user.guild_permissions.administrator = False
    mock_interaction.user.guild_permissions.manage_guild = True

    check = is_rag_admin()
    predicate = extract_predicate(check)

    result = await predicate(mock_interaction)
    assert result is True

@pytest.mark.asyncio
async def test_is_rag_admin_fail_no_perms(mock_interaction):
    mock_interaction.user.guild_permissions.administrator = False
    mock_interaction.user.guild_permissions.manage_guild = False

    check = is_rag_admin()
    predicate = extract_predicate(check)

    result = await predicate(mock_interaction)
    assert result is False
    mock_interaction.response.send_message.assert_called_with(
        "❌ Você não tem permissão para ações de administração RAG.",
        ephemeral=True
    )

@pytest.mark.asyncio
async def test_is_rag_admin_fail_dm(mock_interaction):
    mock_interaction.guild = None

    check = is_rag_admin()
    predicate = extract_predicate(check)

    result = await predicate(mock_interaction)
    assert result is False
    mock_interaction.response.send_message.assert_called_with(
        "❌ Comando apenas disponível em servidores",
        ephemeral=True
    )
