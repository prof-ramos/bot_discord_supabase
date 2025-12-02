import pytest
from src.bot.rag.chunkers import chunk_text

def test_chunk_text_basic():
    text = "word " * 200
    chunks = chunk_text(text, max_words=50)
    assert len(chunks) == 4
    for chunk in chunks:
        assert len(chunk.split()) <= 50

def test_chunk_text_empty():
    assert chunk_text("") == []

def test_chunk_text_exact_limit():
    text = "word " * 100
    chunks = chunk_text(text, max_words=100)
    assert len(chunks) == 1
    assert len(chunks[0].split()) == 100

def test_chunk_text_small_limit():
    text = "one two three four"
    chunks = chunk_text(text, max_words=1)
    assert len(chunks) == 4
    assert chunks[0] == "one"
