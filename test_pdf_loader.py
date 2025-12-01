import pytest
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, StreamObject
from src.bot.rag.loaders import load_text_from_file, load_pdf_text


def test_load_text_from_file_txt(tmp_path):
    """Test loading text from a .txt file."""
    temp_path = tmp_path / "test_file.txt"
    temp_path.write_text("Test content for txt file")

    result = load_text_from_file(temp_path)
    assert "Test content for txt file" in result


def test_load_text_from_file_md(tmp_path):
    """Test loading text from a .md file."""
    temp_path = tmp_path / "test_file.md"
    temp_path.write_text("# Test Markdown\n\nContent here")

    result = load_text_from_file(temp_path)
    assert "# Test Markdown" in result


def test_load_text_from_file_nonexistent(tmp_path):
    """Test loading from a nonexistent file raises FileNotFoundError."""
    nonexistent_path = tmp_path / "this_file_definitely_does_not_exist.txt"
    assert not nonexistent_path.exists()
    with pytest.raises(FileNotFoundError):
        load_text_from_file(nonexistent_path)


@pytest.fixture
def pdf_with_text(tmp_path):
    """Create a small PDF containing known text for extraction tests."""
    expected_text = "Hello PDF content for testing"
    pdf_path = tmp_path / "test_with_content.pdf"

    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=200)

    stream = StreamObject()
    stream._data = f"BT /F1 12 Tf 50 150 Td ({expected_text}) Tj ET".encode("utf-8")
    content_ref = writer._add_object(stream)

    font = DictionaryObject()
    font[NameObject("/Type")] = NameObject("/Font")
    font[NameObject("/Subtype")] = NameObject("/Type1")
    font[NameObject("/BaseFont")] = NameObject("/Helvetica")
    font_ref = writer._add_object(font)

    resources = DictionaryObject()
    resources[NameObject("/Font")] = DictionaryObject({NameObject("/F1"): font_ref})
    page[NameObject("/Resources")] = resources
    page[NameObject("/Contents")] = content_ref

    with open(pdf_path, "wb") as f:
        writer.write(f)

    return pdf_path, expected_text


def test_load_pdf_text(pdf_with_text):
    """Test the load_pdf_text function extracts known PDF content."""
    pdf_path, expected_text = pdf_with_text

    result = load_pdf_text(pdf_path)
    assert isinstance(result, str)
    assert result.strip()
    assert expected_text in result


def test_load_text_from_file_pdf(pdf_with_text):
    """Test loading text from a PDF file via load_text_from_file helper."""
    pdf_path, expected_text = pdf_with_text

    result = load_text_from_file(pdf_path)
    assert isinstance(result, str)
    assert result.strip()
    assert expected_text in result


def test_load_unsupported_file_type(tmp_path):
    """Test loading an unsupported file type."""
    temp_path = tmp_path / "test.unsupported"
    temp_path.write_text("This is an unsupported file type")

    # Should try to read as text anyway (fallback behavior)
    result = load_text_from_file(temp_path)
    assert "This is an unsupported file type" in result
