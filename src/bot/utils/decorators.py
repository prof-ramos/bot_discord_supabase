import functools
import time
import asyncio
from typing import Callable, Any, Type
from ..utils.logger import logger
from ..rag.exceptions import RAGBaseError, DatabaseError

def async_log_execution_time(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to log the execution time of an async function.
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        func_name = func.__name__
        logger.debug(f"Starting execution of {func_name}")

        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"Finished execution of {func_name}", duration=duration)
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Failed execution of {func_name}", duration=duration, error=str(e))
            raise

    return wrapper

def async_handle_errors(exception_cls: Type[Exception] = RAGBaseError, error_message: str = "An error occurred") -> Callable[..., Any]:
    """
    Decorator to handle exceptions in async functions and wrap them in a custom exception.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except exception_cls:
                raise
            except Exception as e:
                logger.log_error_with_traceback(error_message, e, func_name=func.__name__)
                # If the exception is already a RAGBaseError (or subclass), re-raise it
                if isinstance(e, RAGBaseError):
                    raise
                # Otherwise wrap it
                raise exception_cls(f"{error_message}: {str(e)}") from e
        return wrapper
    return decorator
