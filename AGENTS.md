# AGENTS.md - Coding Guidelines for Discord RAG Bot

## Build/Lint/Test Commands
- **Install deps**: `uv sync`
- **Run all tests**: `uv run pytest`
- **Run single test**: `uv run pytest tests/bot/rag/test_pipeline.py::test_ask_function -v`
- **Lint**: `uv run ruff check .` (if ruff installed)
- **Format**: `uv run ruff format .`
- **Type check**: `uv run mypy src/` (if mypy configured)

## Code Style Guidelines
- **Python version**: 3.12+ with type hints everywhere
- **Imports**: Standard library first, then third-party, then local. Use absolute imports.
- **Naming**: snake_case for functions/variables, PascalCase for classes, UPPER_CASE for constants
- **Async**: Use async/await for I/O operations; avoid blocking calls in async functions
- **Error handling**: Custom exceptions in `exceptions.py`, comprehensive try/catch with logging
- **Docstrings**: Google-style docstrings for all public functions
- **Testing**: pytest with fixtures, 90%+ coverage, mock external APIs
- **Performance**: Generators for large data, batch operations for DB/API calls
- **Security**: Never log secrets, validate inputs, use service role keys for backend ops

## Agent Rules
- **python-pro**: Advanced Python features, async/await, performance optimization, comprehensive testing
- **ai-engineer**: LLM integrations, RAG systems, prompt engineering, vector search, monitoring</content>
<parameter name="filePath">AGENTS.md