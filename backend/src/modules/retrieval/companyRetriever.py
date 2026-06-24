# ─────────────────────────────────────────────────────────────────────────────
# backend/src/modules/retrieval/companyRetriever.py
#
# Company Retriever — Structured document retrieval for company research
#
# Responsibilities:
#   Demo mode:       Returns empty RetrievedDocuments immediately. Zero network calls.
#   Production mode: Fetches company homepage + about page + recent news articles.
#                    Returns structured RetrievedDocuments with sources.
#
# Architecture rule:
#   This is a PURE UTILITY — no LLM calls here.
#   The CompanyResearchAgent consumes the output and THEN calls the LLM.
#   The LLM reasons over supplied documents, never pretends to search the web.
#
# Exports: CompanyRetriever, companyRetriever (singleton)
# ─────────────────────────────────────────────────────────────────────────────

from datetime import datetime, timezone
from typing import List, Optional

from src.modules.retrieval.baseRetriever import BaseRetriever
from src.schemas.retrievalSchema import RetrievedDocuments, RetrievedDocument
from src.core.appConfig import settings


class CompanyRetriever(BaseRetriever):
    """
    Retrieves structured company information before passing to CompanyResearchAgent.

    Demo mode behaviour:
        - Returns RetrievedDocuments(documents=[], demo_mode=True) immediately.
        - No network calls, no imports of scraping libraries.

    Production mode behaviour (not yet fully implemented):
        - Fetches company homepage text
        - Fetches "About" page if found
        - Retrieves recent news/press releases
        - Returns list of RetrievedDocument objects with source URLs

    Important: The CompanyResearchAgent LLM reads these documents.
    It does NOT perform retrieval itself.
    """

    def retrieve(self, query: str) -> RetrievedDocuments:
        """
        Retrieve company documents for the given company name.

        Args:
            query: Company name (e.g., "Acme Corp", "Google DeepMind").

        Returns:
            RetrievedDocuments with documents list and demo_mode flag.
        """
        if settings.is_demo:
            return self._demoResponse(query)

        return self._productionRetrieve(query)

    def _demoResponse(self, companyName: str) -> RetrievedDocuments:
        """
        Returns an empty RetrievedDocuments immediately.
        No network calls. No scraping libraries loaded.
        """
        return RetrievedDocuments(
            company_name=companyName,
            documents=[],
            demo_mode=True,
        )

    def _productionRetrieve(self, companyName: str) -> RetrievedDocuments:
        """
        Production retrieval — fetches company website and recent news.

        TODO: Implement full web scraping using httpx + BeautifulSoup.
        Currently raises NotImplementedError to prevent accidental production use
        without implementation.
        """
        # Production implementation placeholder
        # When implemented, this should:
        # 1. Search for company homepage via DuckDuckGo or similar
        # 2. Fetch homepage + /about page text using httpx
        # 3. Search news APIs for recent company mentions
        # 4. Return list of RetrievedDocument objects
        raise NotImplementedError(
            f"Production retrieval for '{companyName}' is not yet implemented. "
            "Set APP_MODE=demo to use demo mode."
        )


# ── Module-level singleton ─────────────────────────────────────────────────────
# Import this everywhere. Never instantiate CompanyRetriever() again.
companyRetriever = CompanyRetriever()
