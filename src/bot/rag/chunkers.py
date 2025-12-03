from typing import List


def chunk_text(text: str, max_words: int) -> List[str]:
    """
    Divide texto em chunks baseado em limite de palavras.

    Args:
        text: Texto a ser dividido em chunks
        max_words: Número máximo de palavras por chunk (configurable via settings.rag.chunk_max_words)

    Returns:
        Lista de chunks de texto
    """
    words = text.split()
    chunks: List[str] = []
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i : i + max_words]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks
