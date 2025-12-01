from pathlib import Path
from pypdf import PdfReader
from pypdf.errors import PdfReadError


def load_text_from_file(path: Path) -> str:
    """Carrega texto de .txt/.md/.pdf."""
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    if path.suffix.lower() in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    elif path.suffix.lower() == ".pdf":
        return load_pdf_text(path)
    else:
        # Fallback minimal: tenta abrir como texto
        return path.read_text(encoding="utf-8", errors="ignore")


def load_pdf_text(path: Path) -> str:
    """Carrega texto de arquivo PDF."""
    try:
        reader = PdfReader(str(path))

        # Verifica se o PDF está criptografado
        if reader.is_encrypted:
            # Tenta descriptografar com senha vazia
            decrypt_result = reader.decrypt("")
            if decrypt_result == 0:
                raise RuntimeError(f"PDF está criptografado e não pode ser lido: {path}")

        # Extrai texto de todas as páginas usando list comprehension
        text = [page_text for page in reader.pages if (page_text := page.extract_text()) is not None]
        return "\n".join(text)
    except RuntimeError:
        raise
    except (PdfReadError, OSError) as e:
        raise RuntimeError(f"Erro ao processar PDF {path}: {str(e)}") from e
    except Exception:
        raise
