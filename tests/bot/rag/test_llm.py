import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.bot.rag.llm import LLMClient
from src.bot.rag.exceptions import RAGBaseError

@pytest.fixture
def mock_openai_client():
    with patch('src.bot.rag.llm.AsyncOpenAI') as mock:
        yield mock

@pytest.fixture
def llm_client(mock_openai_client):
    return LLMClient(api_key="test-key")

@pytest.mark.asyncio
async def test_generate_answer_success(llm_client):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Test Answer"))]
    llm_client.client.chat.completions.create = AsyncMock(return_value=mock_response)

    answer = await llm_client.generate_answer("Query", ["Context 1", "Context 2"])

    assert answer == "Test Answer"
    llm_client.client.chat.completions.create.assert_called_once()

    # Verify call arguments to ensure context is passed correctly
    call_args = llm_client.client.chat.completions.create.call_args
    assert "Context 1" in call_args.kwargs['messages'][1]['content']
    assert "Query" in call_args.kwargs['messages'][1]['content']

@pytest.mark.asyncio
async def test_generate_answer_no_content(llm_client):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=None))]
    llm_client.client.chat.completions.create = AsyncMock(return_value=mock_response)

    answer = await llm_client.generate_answer("Query", ["Context"])

    assert answer == "Desculpe, não consegui gerar uma resposta."

@pytest.mark.asyncio
async def test_generate_answer_error(llm_client):
    llm_client.client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))

    with pytest.raises(Exception, match="API Error"):
        await llm_client.generate_answer("Query", ["Context"])
