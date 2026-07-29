"""RAG module for retrieving IT documentation from PDFs.

Uses Upstash Vector + HuggingFace embeddings when UPSTASH_VECTOR_REST_URL /
UPSTASH_VECTOR_REST_TOKEN are set; falls back to local keyword matching
otherwise (no vector DB needed for local dev/tests).
"""

import os
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

_VECTOR_URL = os.getenv("UPSTASH_VECTOR_REST_URL")
_VECTOR_TOKEN = os.getenv("UPSTASH_VECTOR_REST_TOKEN")


class RAGRetriever:
    """Retrieves IT documentation from PDF files."""

    def __init__(self, pdf_dir: str = "rag", chunk_size: int = 500, chunk_overlap: int = 50):
        """Initialize RAG with PDFs from directory.

        Args:
            pdf_dir: Directory containing PDF files
            chunk_size: Size of text chunks for splitting
            chunk_overlap: Overlap between chunks
        """
        self.pdf_dir = pdf_dir
        self.chunks = []
        self._index = None
        self._embeddings = None
        self._load_pdfs(chunk_size, chunk_overlap)

        if self.chunks and _VECTOR_URL and _VECTOR_TOKEN:
            from upstash_vector import Index
            from langchain_huggingface import HuggingFaceEndpointEmbeddings

            self._index = Index(url=_VECTOR_URL, token=_VECTOR_TOKEN)
            self._embeddings = HuggingFaceEndpointEmbeddings(
                model="sentence-transformers/all-MiniLM-L6-v2"
            )
            self._index_chunks()

    def _index_chunks(self):
        """Embed and upsert all chunks into Upstash Vector (idempotent by id)."""
        texts = [chunk.page_content for chunk in self.chunks]
        vectors = self._embeddings.embed_documents(texts)
        self._index.upsert(
            vectors=[
                (str(i), vector, {"text": text})
                for i, (vector, text) in enumerate(zip(vectors, texts))
            ]
        )

    def _score_chunk(self, chunk: any, query: str) -> float:
        """Score chunk relevance to query using keyword matching."""
        query_lower = query.lower()
        content_lower = chunk.page_content.lower()

        # Count keyword matches
        score = 0
        keywords = query_lower.split()
        for keyword in keywords:
            if len(keyword) > 3:  # Only count meaningful words
                score += content_lower.count(keyword)

        return score

    def _load_pdfs(self, chunk_size: int, chunk_overlap: int):
        """Load PDFs from directory and split into chunks."""
        pdf_files = list(Path(self.pdf_dir).glob("*.pdf"))
        if not pdf_files:
            return

        documents = []
        for pdf_file in pdf_files:
            try:
                loader = PyPDFLoader(str(pdf_file))
                documents.extend(loader.load())
            except Exception:
                # Skip PDFs that can't be loaded
                pass

        if not documents:
            return

        # Split documents into chunks
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )
        self.chunks = splitter.split_documents(documents)

    def retrieve(self, query: str, top_k: int = 3) -> list[str]:
        """Retrieve relevant documentation for a query.

        Uses vector similarity search when Upstash Vector is configured,
        otherwise falls back to keyword matching.

        Args:
            query: User question or topic
            top_k: Number of top results to return

        Returns:
            List of relevant document excerpts
        """
        if not self.chunks:
            return []

        if self._index is not None:
            query_vector = self._embeddings.embed_query(query)
            results = self._index.query(
                vector=query_vector, top_k=top_k, include_metadata=True
            )
            return [r.metadata["text"] for r in results]

        # Score and rank chunks
        scored_chunks = [(chunk, self._score_chunk(chunk, query)) for chunk in self.chunks]
        scored_chunks.sort(key=lambda x: x[1], reverse=True)

        # Return top non-zero results
        results = [chunk.page_content for chunk, score in scored_chunks[:top_k] if score > 0]
        return results

    def format_context(self, query: str) -> str:
        """Get formatted context for a query to inject into LLM prompt.

        Args:
            query: User question

        Returns:
            Formatted context string or empty if no docs found
        """
        docs = self.retrieve(query)
        if not docs:
            return ""

        context = "[RELEVANT DOCUMENTATION]\n\n"
        for i, doc in enumerate(docs, 1):
            context += f"**Reference {i}:**\n{doc}\n\n"
        return context
