"""Tests for src.rag.RAGRetriever."""

from src.rag import RAGRetriever


def test_retrieves_relevant_chunk_for_known_topic():
    retriever = RAGRetriever(pdf_dir="rag")
    context = retriever.format_context("VPN troubleshooting connection issues")
    assert "VPN" in context or "vpn" in context.lower()


def test_returns_empty_for_unrelated_query():
    retriever = RAGRetriever(pdf_dir="rag")
    context = retriever.format_context("xyzzy nonexistent gibberish topic qwzx")
    assert context == ""


def test_empty_dir_yields_no_chunks():
    retriever = RAGRetriever(pdf_dir="tests")
    assert retriever.chunks == []
    assert retriever.format_context("anything") == ""
