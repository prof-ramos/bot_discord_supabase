from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class DocumentMetadata(BaseModel):
    """Metadata for a document."""
    source: Optional[str] = None
    author: Optional[str] = None
    created_at: Optional[datetime] = None
    extra: Dict[str, Any] = Field(default_factory=dict)

class Document(BaseModel):
    """Represents a document in the RAG system."""
    id: Optional[str] = None
    title: str
    content: Optional[str] = None # Content might not be stored directly in rag_documents, but useful for transport
    doc_type: str
    source_path: Optional[str] = None
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    created_at: Optional[datetime] = None

class Chunk(BaseModel):
    """Represents a text chunk with its embedding."""
    id: Optional[str] = None
    document_id: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SearchResult(BaseModel):
    """Represents a search result from the vector store."""
    id: str
    document_id: str
    chunk: str
    similarity: float
    metadata: Dict[str, Any] = Field(default_factory=dict)

class RAGResponse(BaseModel):
    """Represents the final response from the RAG pipeline."""
    answer: str
    sources: List[SearchResult]
    query: str
    execution_time: float
