import pytest

from conftest import make_pdf
from documind.ingestion import PDFExtractionError, chunk_documents, load_pdf_bytes
from documind.ingestion.loader import clean_text


def test_clean_text_joins_hyphenation_and_whitespace():
    assert clean_text("infor-\nmation   here\n\n\n\nnext") == "information here\n\nnext"


def test_load_pdf_one_doc_per_page_with_metadata(solar_pdf):
    docs = load_pdf_bytes(solar_pdf, "solar.pdf")
    assert len(docs) == 2
    assert [d.metadata["page"] for d in docs] == [1, 2]
    assert all(d.metadata["source"] == "solar.pdf" for d in docs)
    assert all(d.metadata["total_pages"] == 2 for d in docs)
    assert "photovoltaic" in docs[0].page_content


def test_blank_pages_are_skipped():
    docs = load_pdf_bytes(make_pdf(["Hello world", " "]), "x.pdf")
    assert len(docs) == 1


def test_invalid_pdf_raises():
    with pytest.raises(PDFExtractionError):
        load_pdf_bytes(b"not a pdf at all", "bad.pdf")


def test_chunks_respect_size_and_keep_page(solar_pdf):
    docs = load_pdf_bytes(solar_pdf, "solar.pdf")
    chunks = chunk_documents(docs, chunk_size=80, chunk_overlap=10)
    assert len(chunks) > len(docs)
    assert all(len(c.page_content) <= 80 for c in chunks)
    assert {c.metadata["page"] for c in chunks} == {1, 2}
    ids = [c.metadata["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids))


def test_chunk_ids_are_deterministic(solar_pdf):
    docs = load_pdf_bytes(solar_pdf, "solar.pdf")
    a = [c.metadata["chunk_id"] for c in chunk_documents(docs, 100, 10)]
    b = [c.metadata["chunk_id"] for c in chunk_documents(docs, 100, 10)]
    assert a == b
