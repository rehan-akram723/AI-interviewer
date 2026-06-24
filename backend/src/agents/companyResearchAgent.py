# ─────────────────────────────────────────────────────────────────────────────
# backend/src/agents/companyResearchAgent.py
#
# Company Research Agent — LangGraph node function
#
# Two-step pipeline (retrieval separated from LLM reasoning):
#   Step 1: Call companyRetriever.retrieve() → RetrievedDocuments
#           (Pure utility — no LLM call here)
#   Step 2: If documents available → LLM summarises company context
#           If demo mode or no documents → return empty company_context
#
# Architecture rule enforced here:
#   The LLM reads supplied documents. It does NOT search the web itself.
#   This separation prevents hallucination of company facts.
#
# LangGraph contract:
#   Input:  Full InterviewSession state dict
#   Output: {"company_context": str, "step_log": [...appended]}
#
# Exports: companyResearchAgent
# ─────────────────────────────────────────────────────────────────────────────

from src.modules.retrieval.companyRetriever import companyRetriever
from src.core.llmClient import callLlm
from src.core.appConfig import settings


_RESEARCH_SYSTEM_PROMPT = """\
You are a research analyst preparing a briefing for an interview panel. \
Summarise company information concisely and accurately from provided documents only.
"""

_RESEARCH_PROMPT_TEMPLATE = """\
Based ONLY on the following company documents, write a 200-300 word company briefing \
for an interview panel. Cover: company mission, key products/services, culture, \
recent notable events, and anything relevant to the role of '{targetRole}'.

Do NOT invent information not present in the documents. If information is limited, \
say so briefly and work with what is available.

COMPANY: {companyName}

RETRIEVED DOCUMENTS:
---
{documentsText}
---

Write the briefing now:
"""


def companyResearchAgent(state: dict) -> dict:
    """
    LangGraph node: Company Research Agent.

    Step 1: Retrieve company documents via companyRetriever (no LLM).
    Step 2: Pass documents to LLM for summarisation and briefing.
            In demo mode: documents list is empty → skip LLM, return "".

    Reads from state:
        state["candidate"]["target_company"] — company name
        state["candidate"]["target_role"]    — role context for the briefing

    Returns:
        {
            "company_context": str,  # "" in demo mode
            "step_log": [...appended]
        }
    """
    stepLog = list(state.get("step_log", []))

    companyName: str = state.get("candidate", {}).get("target_company", "")
    targetRole: str = state.get("candidate", {}).get("target_role", "the target role")

    if not companyName.strip():
        stepLog.append("[companyResearchAgent] No company name provided — skipping.")
        return {"company_context": "", "step_log": stepLog}

    # ── Step 1: Retrieve Documents (no LLM) ───────────────────────────────────
    stepLog.append(f"[companyResearchAgent] Retrieving documents for: '{companyName}'")
    retrieved = companyRetriever.retrieve(companyName)

    if retrieved.demo_mode or not retrieved.documents:
        stepLog.append(
            "[companyResearchAgent] Demo mode or no documents retrieved — "
            "company_context set to '' (no LLM hallucination)."
        )
        return {"company_context": "", "step_log": stepLog}

    # ── Step 2: LLM Summarisation (production only, documents available) ──────
    stepLog.append(
        f"[companyResearchAgent] {len(retrieved.documents)} document(s) retrieved. "
        "Calling LLM for summarisation..."
    )

    # Concatenate document content with source attribution
    documentParts = []
    for doc in retrieved.documents:
        documentParts.append(
            f"[Source: {doc.source} | Type: {doc.doc_type}]\n{doc.content}"
        )
    documentsText = "\n\n---\n\n".join(documentParts)

    prompt = _RESEARCH_PROMPT_TEMPLATE.format(
        companyName=companyName,
        targetRole=targetRole,
        documentsText=documentsText,
    )

    companyContext: str = callLlm(
        prompt=prompt,
        systemPrompt=_RESEARCH_SYSTEM_PROMPT,
        temperature=0.3,
        maxTokens=512,
        jsonMode=False,
    )

    stepLog.append(
        f"[companyResearchAgent] Company context generated. "
        f"Length: {len(companyContext)} chars."
    )

    return {
        "company_context": companyContext.strip(),
        "step_log": stepLog,
    }
