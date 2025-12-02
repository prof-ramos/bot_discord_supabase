import pytest
from src.bot.utils.formatters import format_results_for_discord
from src.bot.rag.models import SearchResult

def test_format_results_empty():
    result = format_results_for_discord([], "query")
    assert "Nada encontrado" in result
    assert "query" in result

def test_format_results_single():
    results = [{"chunk": "Content here", "similarity": 0.9}]
    output = format_results_for_discord(results, "query")
    assert "Content here" in output
    assert "90.0%" in output

def test_format_results_multiple_truncation():
    # Only top 3 should be shown
    results = [
        {"chunk": f"Content {i}", "similarity": 0.9}
        for i in range(5)
    ]
    output = format_results_for_discord(results, "query")
    assert "Content 0" in output
    assert "Content 1" in output
    assert "Content 2" in output
    assert "Content 3" not in output

def test_format_results_long_text_truncation():
    # Long text should be truncated in the message overall
    results = [{"chunk": "a" * 500, "similarity": 0.9}] * 3
    # The formatter truncates individual chunks to 300 chars, but also the whole body to 1900
    output = format_results_for_discord(results, "query")
    assert len(output) <= 2000
    assert "..." in output
