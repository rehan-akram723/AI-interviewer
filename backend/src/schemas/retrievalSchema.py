# ─────────────────────────────────────────────────────────────────────────────
# backend/src/schemas/retrievalSchema.py
#
# Pydantic models for the retrieval layer.
# RetrievedDocuments is the contract between CompanyRetriever and
# CompanyResearchAgent. The LLM only sees these structured documents —
# it never performs retrieval itself.
# ─────────────────────────────────────────────────────────────────────────────

from pydantic import BaseModel, Field
from typing import List
from datetime import datetime, timezone


class RetrievedDocument(BaseModel):
    """A single document fetched by the retrieval layer."""
    source: str
    """URL or human-readable description of the source (e.g., 'acme.com/about')."""

    content: str
    """Raw retrieved text content."""

    doc_type: str
    """Category: 'website' | 'news' | 'summary' | 'placeholder'."""

    retrieved_at: str
    """ISO 8601 timestamp of when this document was fetched."""


class RetrievedDocuments(BaseModel):
    """
    Container returned by any BaseRetriever implementation.
    Consumed directly by CompanyResearchAgent — the LLM reasons over
    these documents without performing any retrieval itself.

    In demo mode: documents=[] and demo_mode=True.
    The agent checks demo_mode and skips LLM summarisation if True.
    """
    company_name: str
    documents: List[RetrievedDocument] = Field(default_factory=list)
    demo_mode: bool = False
