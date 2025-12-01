import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
from src.bot.rag.pipeline import RagPipeline
from src.bot.rag.models import SearchResult, RAGResponse
from src.bot.rag.exceptions import RAGBaseError

class TestRagPipeline(unittest.TestCase):
    def setUp(self):
        self.mock_store = AsyncMock()
        self.mock_embedder = AsyncMock()
        self.mock_llm = AsyncMock()
        self.pipeline = RagPipeline(self.mock_store, self.mock_embedder, self.mock_llm)

    @pytest.mark.asyncio
    @patch('src.bot.rag.pipeline.load_text_from_file')
    @patch('src.bot.rag.pipeline.chunk_text')
    async def test_add_document_success(self, mock_chunk, mock_load):
        mock_load.return_value = "Full text content"
        mock_chunk.return_value = ["chunk1", "chunk2"]
        self.mock_embedder.embed_many.return_value = [[0.1], [0.2]]
        self.mock_store.insert_document.return_value = "doc-123"

        doc_id = await self.pipeline.add_document("Test Title", "/path/to/file")

        self.assertEqual(doc_id, "doc-123")
        self.mock_store.insert_document.assert_called_once()
        self.mock_store.insert_chunks.assert_called_once()

    @pytest.mark.asyncio
    async def test_ask_success(self):
        self.mock_embedder.embed_text.return_value = [0.1, 0.2]
        expected_results = [
            SearchResult(id="1", document_id="d1", chunk="c1", similarity=0.9),
            SearchResult(id="2", document_id="d2", chunk="c2", similarity=0.8)
        ]
        self.mock_store.search.return_value = expected_results

        results = await self.pipeline.ask("query")

        self.assertEqual(results, expected_results)
        self.mock_embedder.embed_text.assert_called_with("query")
        self.mock_store.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_ask_with_llm_success(self):
        # Setup search results
        search_results = [
            SearchResult(id="1", document_id="d1", chunk="c1", similarity=0.9)
        ]
        self.mock_store.search.return_value = search_results
        self.mock_embedder.embed_text.return_value = [0.1]

        # Setup LLM response
        self.mock_llm.generate_answer.return_value = "Generated Answer"

        response = await self.pipeline.ask_with_llm("query")

        self.assertIsInstance(response, RAGResponse)
        self.assertEqual(response.answer, "Generated Answer")
        self.assertEqual(response.sources, search_results)

    @pytest.mark.asyncio
    async def test_ask_with_llm_no_results(self):
        self.mock_store.search.return_value = []
        self.mock_embedder.embed_text.return_value = [0.1]
        self.mock_llm.generate_answer.return_value = "No context answer"

        response = await self.pipeline.ask_with_llm("query")

        self.assertEqual(response.answer, "No context answer")
        self.assertEqual(response.sources, [])

    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self):
        self.mock_embedder.embed_text.side_effect = Exception("Embedder failed")

        with self.assertRaises(RAGBaseError):
            await self.pipeline.ask("query")
