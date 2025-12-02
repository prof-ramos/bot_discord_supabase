import pytest
import asyncio
from unittest.mock import MagicMock, patch
from src.bot.utils.decorators import async_log_execution_time, async_handle_errors
from src.bot.rag.exceptions import RAGBaseError

@pytest.mark.asyncio
async def test_async_log_execution_time(caplog):
    @async_log_execution_time
    async def sample_func():
        await asyncio.sleep(0.01)
        return "success"

    with caplog.at_level("DEBUG"):
        result = await sample_func()

    assert result == "success"
    assert "Starting execution of sample_func" in caplog.text
    assert "Finished execution of sample_func" in caplog.text

@pytest.mark.asyncio
async def test_async_log_execution_time_error(caplog):
    @async_log_execution_time
    async def failing_func():
        raise ValueError("oops")

    with caplog.at_level("ERROR"):
        with pytest.raises(ValueError):
            await failing_func()

    assert "Failed execution of failing_func" in caplog.text

@pytest.mark.asyncio
async def test_async_handle_errors_success():
    @async_handle_errors()
    async def sample_func():
        return "success"

    result = await sample_func()
    assert result == "success"

@pytest.mark.asyncio
async def test_async_handle_errors_converts_exception():
    @async_handle_errors(exception_cls=RAGBaseError, error_message="Wrapped Error")
    async def failing_func():
        raise ValueError("original error")

    with pytest.raises(RAGBaseError) as exc_info:
        await failing_func()

    assert "Wrapped Error" in str(exc_info.value)
    assert "original error" in str(exc_info.value)

@pytest.mark.asyncio
async def test_async_handle_errors_reraises_correct_type():
    @async_handle_errors(exception_cls=RAGBaseError)
    async def failing_func():
        raise RAGBaseError("Already correct type")

    with pytest.raises(RAGBaseError) as exc_info:
        await failing_func()

    assert "Already correct type" in str(exc_info.value)
