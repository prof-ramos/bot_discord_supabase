import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.bot.rag.supabase_store import SupabaseStore
from src.bot.rag.models import Document, Chunk, SearchResult
from src.bot.rag.exceptions import DatabaseError

@pytest.fixture
def mock_client():
    return MagicMock()

@pytest.fixture
def store(mock_client):
    with patch('src.bot.rag.supabase_store.get_supabase_client', return_value=mock_client):
        yield SupabaseStore("url", "key")

@pytest.mark.asyncio
async def test_insert_document_success(store, mock_client):
    document = Document(title="Test Doc", doc_type="test", source_path="/path/to/doc")

    # Mock the chain of calls: client.table().insert().execute()
    mock_execute = MagicMock()
    mock_execute.data = [{"id": "doc-123"}]

    mock_insert = MagicMock()
    mock_insert.execute.return_value = mock_execute

    mock_table = MagicMock()
    mock_table.insert.return_value = mock_insert

    mock_client.table.return_value = mock_table

    result = await store.insert_document(document)

    assert result == "doc-123"
    mock_client.table.assert_called_with("rag_documents")
    mock_table.insert.assert_called_once()

@pytest.mark.asyncio
async def test_insert_chunks_success(store, mock_client):
    chunks = [
        Chunk(document_id="doc-123", content="chunk1", embedding=[0.1, 0.2]),
        Chunk(document_id="doc-123", content="chunk2", embedding=[0.3, 0.4])
    ]

    mock_execute = MagicMock()

    mock_insert = MagicMock()
    mock_insert.execute.return_value = mock_execute

    mock_table = MagicMock()
    mock_table.insert.return_value = mock_insert

    mock_client.table.return_value = mock_table

    result = await store.insert_chunks(chunks)

    assert result == 2
    mock_client.table.assert_called_with("rag_chunks")
    mock_table.insert.assert_called_once()

@pytest.mark.asyncio
async def test_search_success(store, mock_client):
    query_embedding = [0.1, 0.2]

    mock_execute = MagicMock()
    mock_execute.data = [
        {"id": "1", "document_id": "doc-1", "content": "chunk1", "similarity": 0.9},
        {"id": "2", "document_id": "doc-2", "content": "chunk2", "similarity": 0.8}
    ]

    mock_rpc_call = MagicMock()
    mock_rpc_call.execute.return_value = mock_execute

    mock_client.rpc.return_value = mock_rpc_call

    results = await store.search(query_embedding, match_count=2, match_threshold=0.5)

    assert len(results) == 2
    assert isinstance(results[0], SearchResult)
    assert results[0].chunk == "chunk1"
    assert results[0].similarity == 0.9

@pytest.mark.asyncio
async def test_database_error(store, mock_client):
    document = Document(title="Test Doc", doc_type="test")

    # Simulate an exception during database operation
    mock_client.table.side_effect = Exception("DB Connection Failed")

    with pytest.raises(DatabaseError):
        await store.insert_document(document)
