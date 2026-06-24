# ─────────────────────────────────────────────────────────────────────────────
# backend/src/modules/retrieval/baseRetriever.py
#
# Abstract Base Retriever Interface
#
# Architecture rule:
#   The LLM NEVER calls retrieval directly.
#   Retrieval is always a separate, pre-LLM step.
#   Concrete retrievers return RetrievedDocuments.
#   The LLM agent then reasons OVER these documents.
#
# Exports: BaseRetriever
# ─────────────────────────────────────────────────────────────────────────────

from abc import ABC, abstractmethod
from src.schemas.retrievalSchema import RetrievedDocuments


class BaseRetriever(ABC):
    """
    Abstract base class for all retriever implementations.

    Concrete subclasses must implement the `retrieve` method.
    The retrieve method is a pure utility — no LLM calls permitted here.
    LLM reasoning over retrieved content happens in agent nodes, not retrievers.
    """

    @abstractmethod
    def retrieve(self, query: str) -> RetrievedDocuments:
        """
        Retrieve documents relevant to the given query.

        Args:
            query: The search query (e.g., company name).

        Returns:
            RetrievedDocuments object with source documents and metadata.
        """
        raise NotImplementedError
