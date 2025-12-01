from typing import List


def chunk_text(text: str, max_words: int = 180) -> List[str]:
    """
    Divide texto em chunks pequenos para free tier (palavras).
    Simples, mas eficiente o suficiente para RAG inicial.
    """
    words = text.split()
    chunks: List[str] = []
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i : i + max_words]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks
