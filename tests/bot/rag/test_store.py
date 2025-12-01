import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
from src.bot.rag.supabase_store import SupabaseStore
from src.bot.rag.models import Document, Chunk, SearchResult
from src.bot.rag.exceptions import DatabaseError

class TestSupabaseStore(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        with patch('src.bot.rag.supabase_store.get_supabase_client', return_value=self.mock_client):
            self.store = SupabaseStore("url", "key")

    @pytest.mark.asyncio
    async def test_insert_document_success(self):
        document = Document(title="Test Doc", doc_type="test", source_path="/path/to/doc")

        # Mock the chain of calls: client.table().insert().execute()
        mock_execute = MagicMock()
        mock_execute.data = [{"id": "doc-123"}]

        mock_insert = MagicMock()
        mock_insert.execute.return_value = mock_execute

        mock_table = MagicMock()
        mock_table.insert.return_value = mock_insert

        self.mock_client.table.return_value = mock_table

        result = await self.store.insert_document(document)

        self.assertEqual(result, "doc-123")
        self.mock_client.table.assert_called_with("rag_documents")
        mock_table.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_insert_chunks_success(self):
        chunks = [
            Chunk(document_id="doc-123", content="chunk1", embedding=[0.1, 0.2]),
            Chunk(document_id="doc-123", content="chunk2", embedding=[0.3, 0.4])
        ]

        mock_execute = MagicMock()

        mock_insert = MagicMock()
        mock_insert.execute.return_value = mock_execute

        mock_table = MagicMock()
        mock_table.insert.return_value = mock_insert

        self.mock_client.table.return_value = mock_table

        result = await self.store.insert_chunks(chunks)

        self.assertEqual(result, 2)
        self.mock_client.table.assert_called_with("rag_chunks")
        mock_table.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_success(self):
        query_embedding = [0.1, 0.2]

        mock_execute = MagicMock()
        mock_execute.data = [
            {"id": "1", "document_id": "doc-1", "content": "chunk1", "similarity": 0.9},
            {"id": "2", "document_id": "doc-2", "content": "chunk2", "similarity": 0.8}
        ]

        mock_rpc_call = MagicMock()
        mock_rpc_call.execute.return_value = mock_execute

        self.mock_client.rpc.return_value = mock_rpc_call

        results = await self.store.search(query_embedding, match_count=2, match_threshold=0.5)

        self.assertEqual(len(results), 2)
        self.assertIsInstance(results[0], SearchResult)
        self.assertEqual(results[0].chunk, "chunk1")
        self.assertEqual(results[0].similarity, 0.9)

    @pytest.mark.asyncio
    async def test_database_error(self):
        document = Document(title="Test Doc", doc_type="test")

        # Simulate an exception during database operation
        self.mock_client.table.side_effect = Exception("DB Connection Failed")

        with self.assertRaises(DatabaseError):
            await self.store.insert_document(document)
