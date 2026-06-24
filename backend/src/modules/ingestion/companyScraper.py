# ─────────────────────────────────────────────────────────────────────────────
# backend/src/modules/ingestion/companyScraper.py
#
# Legacy Company Scraper — simple fallback utility
#
# NOTE: The primary retrieval mechanism is CompanyRetriever in
# backend/src/modules/retrieval/companyRetriever.py which returns structured
# RetrievedDocuments. This file is a simpler fallback that returns a plain
# string — kept for compatibility and simple use cases.
#
# In demo mode: returns "" immediately, zero network calls.
# In production: would scrape company homepage (not yet implemented).
#
# Exports: scrapeCompany
# ─────────────────────────────────────────────────────────────────────────────

from src.core.appConfig import settings


def scrapeCompany(companyName: str) -> str:
    """
    Simple company context scraper (legacy interface).

    In demo mode: Returns an empty string immediately. No network calls.
    In production: Would search + scrape company website. Not yet implemented.

    Args:
        companyName: The company name as provided by the user.

    Returns:
        Company context string (200-300 words) or "" in demo mode.
    """
    if settings.is_demo:
        return ""

    # Production implementation — web scrape placeholder
    # TODO: Implement actual web scraping in production mode.
    # Use the CompanyRetriever (retrieval layer) for structured retrieval instead.
    raise NotImplementedError(
        "Production company scraping is not yet implemented. "
        "Use CompanyRetriever for structured retrieval."
    )
