from pathlib import Path


def load_text_from_file(path: Path) -> str:
    """Carrega texto simples de .txt/.md. Para PDF, converta antes."""
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    if path.suffix.lower() in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")

    # Fallback minimal: tenta abrir como texto
    return path.read_text(encoding="utf-8", errors="ignore")
