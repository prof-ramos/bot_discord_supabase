import pytest
from unittest.mock import MagicMock, AsyncMock
from src.bot.rag.pipeline import RagPipeline
from src.bot.rag.models import SearchResult, RAGResponse
from src.bot.rag.exceptions import RAGBaseError

@pytest.fixture
def mock_store():
    return AsyncMock()

@pytest.fixture
def mock_embedder():
    return AsyncMock()

@pytest.fixture
def mock_llm():
    return AsyncMock()

@pytest.fixture
def pipeline(mock_store, mock_embedder, mock_llm):
    return RagPipeline(mock_store, mock_embedder, mock_llm)

@pytest.mark.asyncio
async def test_add_document_success(pipeline, mock_store, mock_embedder, mocker):
    mock_load = mocker.patch('src.bot.rag.pipeline.load_text_from_file', return_value="Full text content")
    mock_chunk = mocker.patch('src.bot.rag.pipeline.chunk_text', return_value=["chunk1", "chunk2"])

    mock_embedder.embed_many.return_value = [[0.1], [0.2]]
    mock_store.insert_document.return_value = "doc-123"

    doc_id = await pipeline.add_document("Test Title", "/path/to/file")

    assert doc_id == "doc-123"
    mock_store.insert_document.assert_called_once()
    mock_store.insert_chunks.assert_called_once()

@pytest.mark.asyncio
async def test_ask_success(pipeline, mock_store, mock_embedder):
    mock_embedder.embed_text.return_value = [0.1, 0.2]
    expected_results = [
        SearchResult(id="1", document_id="d1", chunk="c1", similarity=0.9),
        SearchResult(id="2", document_id="d2", chunk="c2", similarity=0.8)
    ]
    mock_store.search.return_value = expected_results

    results = await pipeline.ask("query")

    assert results == expected_results
    mock_embedder.embed_text.assert_called_with("query")
    mock_store.search.assert_called_once()

@pytest.mark.asyncio
async def test_ask_with_llm_success(pipeline, mock_store, mock_embedder, mock_llm):
    # Setup search results
    search_results = [
        SearchResult(id="1", document_id="d1", chunk="c1", similarity=0.9)
    ]
    mock_store.search.return_value = search_results
    mock_embedder.embed_text.return_value = [0.1]

    # Setup LLM response
    mock_llm.generate_answer.return_value = "Generated Answer"

    response = await pipeline.ask_with_llm("query")

    assert isinstance(response, RAGResponse)
    assert response.answer == "Generated Answer"
    assert response.sources == search_results

@pytest.mark.asyncio
async def test_ask_with_llm_no_results(pipeline, mock_store, mock_embedder, mock_llm):
    mock_store.search.return_value = []
    mock_embedder.embed_text.return_value = [0.1]
    mock_llm.generate_answer.return_value = "No context answer"

    response = await pipeline.ask_with_llm("query")

    assert response.answer == "No context answer"
    assert response.sources == []

@pytest.mark.asyncio
async def test_pipeline_error_handling(pipeline, mock_embedder):
    mock_embedder.embed_text.side_effect = Exception("Embedder failed")

    with pytest.raises(RAGBaseError):
        await pipeline.ask("query")
