# ─────────────────────────────────────────────────────────────────────────────
# backend/src/graph/edges.py
#
# Conditional Routing Edge Functions — LangGraph conditional edge callables
#
# These are the pure routing functions consumed by the LangGraph
# add_conditional_edges() calls. They read state and return a node name
# string (or END) telling the graph where to route next.
#
# Exported functions:
#   shouldGenerateFollowup(state) — primary routing edge after followUpAgent
#
# Design notes:
#   • These functions must be stateless and side-effect-free — they only READ
#     state and return a routing string. Never write to state here.
#   • The interviewGraph.py already contains routeAfterFollowUp and
#     routeAfterConductor as inline functions. shouldGenerateFollowup here
#     is the canonical, named export that both the graph builder and the
#     integration tests import from a single location.
#   • Any new conditional edge added to either setupGraph or reportGraph
#     should be defined here and imported into the graph module.
#
# Routing map:
#   shouldGenerateFollowup:
#       "conductorAgent" → followUpAgent decided to advance to the next
#                          planned question (or safety ceiling was breached).
#       END              → a follow-up question was injected into state, or
#                          the interview is already complete. The graph stops
#                          so the API route can read next_question from state.
# ─────────────────────────────────────────────────────────────────────────────

import logging
from langgraph.graph import END

logger = logging.getLogger(__name__)


def shouldGenerateFollowup(state: dict) -> str:
    """
    Conditional routing edge — invoked by LangGraph after the followUpAgent node.

    Reads the ``should_advance`` flag that followUpAgent writes to state after
    its decision pipeline (ceiling check → score gate → LLM decision):

        should_advance=True  → the agent decided NOT to generate a follow-up.
                               Route to ``conductorAgent`` to deliver the next
                               planned question from question_plan.

        should_advance=False → the agent generated a follow-up question and
                               injected it into ``state["next_question"]`` and
                               ``state["asked_questions"]``. Route to END so the
                               graph stops and the API route serves the follow-up.

    Safety overrides (always route to END regardless of should_advance):
        • status == "completed"  — interview was already finished before this node ran.
        • status == "error"      — an upstream agent hit an unrecoverable failure.

    The safety overrides prevent an infinite loop where a malfunctioning
    followUpAgent continuously returns should_advance=False on a completed
    or errored session.

    Args:
        state: The full InterviewSession dict, post-followUpAgent update.

    Returns:
        "conductorAgent" to advance to the next planned question, or
        END (LangGraph sentinel) to terminate the current graph invocation.
    """
    shouldAdvance: bool = state.get("should_advance", True)
    sessionStatus: str = state.get("status", "in_progress")

    # ── Safety override: always terminate on terminal statuses ─────────────────
    if sessionStatus in ("completed", "error"):
        logger.debug(
            "shouldGenerateFollowup: terminal status='%s' — routing to END.",
            sessionStatus,
        )
        return END

    if shouldAdvance:
        # followUpAgent decided to skip follow-up → advance the main question plan
        logger.debug(
            "shouldGenerateFollowup: should_advance=True — routing to conductorAgent."
        )
        return "conductorAgent"

    # followUpAgent injected a follow-up question → stop the graph here.
    # The API route reads state["next_question"] and serves it to the frontend.
    logger.debug(
        "shouldGenerateFollowup: should_advance=False — follow-up injected, routing to END."
    )
    return END
