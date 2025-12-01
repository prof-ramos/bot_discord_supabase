import pytest
from pathlib import Path
from src.bot.rag.loaders import load_text_from_file


def test_load_various_formats(tmp_path):
    """Test that the loader handles different file formats correctly."""

    # Test TXT file
    txt_path = tmp_path / "test.txt"
    txt_path.write_text("This is a test text file.")

    # Test MD file
    md_path = tmp_path / "test.md"
    md_path.write_text("# Header\n\nThis is a test markdown file.")

    # Verify TXT loading
    txt_result = load_text_from_file(txt_path)
    assert "This is a test text file." in txt_result

    # Verify MD loading
    md_result = load_text_from_file(md_path)
    assert "# Header" in md_result
    assert "This is a test markdown file." in md_result


def test_error_handling(tmp_path):
    """Test error handling for non-existent files."""
    nonexistent_path = tmp_path / "nonexistent_file.txt"
    assert not nonexistent_path.exists()

    with pytest.raises(FileNotFoundError):
        load_text_from_file(nonexistent_path)