"""RAG module for retrieving IT documentation from PDFs."""

from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


class RAGRetriever:
    """Retrieves IT documentation from PDF files using simple keyword matching."""

    def __init__(self, pdf_dir: str = "rag", chunk_size: int = 500, chunk_overlap: int = 50):
        """Initialize RAG with PDFs from directory.

        Args:
            pdf_dir: Directory containing PDF files
            chunk_size: Size of text chunks for splitting
            chunk_overlap: Overlap between chunks
        """
        self.pdf_dir = pdf_dir
        self.chunks = []
        self._load_pdfs(chunk_size, chunk_overlap)

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

    def retrieve(self, query: str, top_k: int = 3) -> list[str]:
        """Retrieve relevant documentation for a query using keyword matching.

        Args:
            query: User question or topic
            top_k: Number of top results to return

        Returns:
            List of relevant document excerpts
        """
        if not self.chunks:
            return []

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
