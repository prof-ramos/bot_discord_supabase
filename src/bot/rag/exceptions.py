class RAGBaseError(Exception):
    """Base exception for RAG errors."""
    pass

class DatabaseError(RAGBaseError):
    """Raised when a database operation fails."""
    pass

class LLMError(RAGBaseError):
    """Raised when an LLM operation fails."""
    pass

class EmbeddingError(RAGBaseError):
    """Raised when an embedding operation fails."""
    pass
