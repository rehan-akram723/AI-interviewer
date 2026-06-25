# ─────────────────────────────────────────────────────────────────────────────
# backend/src/graph/interviewGraph.py
#
# Interview Graph — Full LangGraph state machine for the live interview phase
#
# Milestone 2.3 (complete feedback pipeline):
#
# Graph topology:
#
#   [API route invokes graph after answer submission]
#
#   START → liveCoachAgent
#               ↓
#           difficultyCalibratorAgent
#               ↓
#           followUpAgent ──────────────────────────────────────┐
#               │                                               │
#               │ should_advance=True                           │ should_advance=False
#               ↓                                               │ (follow-up injected)
#           conductorAgent → routeAfterConductor → END          │
#               ↑                                               │
#               └───────────────────────────────────────────────┘
#               (END if interview complete)
#
# Key design notes:
#   1. The graph is invoked ONCE per answer submission. The API route drives the loop.
#   2. liveCoachAgent runs first, always — coaching feedback is emitted before routing.
#   3. difficultyCalibratorAgent runs deterministically — no LLM.
#   4. followUpAgent may or may not call the LLM depending on ceiling/gate checks.
#   5. conductorAgent delivers the next planned question OR signals completion.
#   6. routeAfterConductor is the terminal conditional edge (routes to END or loops).
#
# Conditional routing:
#   routeAfterFollowUp:   followUpAgent result → "conductorAgent" (advance) or END
#                         [END case only if interview complete at follow-up stage]
#   routeAfterConductor:  conductorAgent result → END (complete/error) or back to conductor
#                         [conductor loops back only in edge cases — API route controls flow]
#
# Exports: interviewGraph, routeAfterConductor, routeAfterFollowUp
# ─────────────────────────────────────────────────────────────────────────────

from langgraph.graph import StateGraph, END

from src.graph.sessionState import InterviewSession
from src.agents.liveCoachAgent import liveCoachAgent
from src.agents.difficultyCalibratorAgent import difficultyCalibratorAgent
from src.agents.followUpAgent import followUpAgent
from src.agents.conductorAgent import conductorAgent


# ── Conditional Routing Functions ─────────────────────────────────────────────

def routeAfterFollowUp(state: dict) -> str:
    """
    Conditional edge after followUpAgent.

    Routes to "conductorAgent" when:
        - should_advance is True (follow-up ceiling hit, score gate cleared, or LLM said advance)
        - Interview is NOT yet complete

    Routes to END when:
        - The interview was already complete before followUpAgent ran (edge case)

    Note: When should_advance=False, the follow-up question is already in
    state["next_question"] and state["asked_questions"]. The graph terminates
    here so the API route returns the follow-up as the next question.
    In this case, routeAfterFollowUp returns END so the graph stops after injecting
    the follow-up — the API route reads state["next_question"] directly.

    Returns:
        "conductorAgent" if we should pull the next planned question,
        END if the follow-up was injected (API reads it from state) or interview done.
    """
    shouldAdvance: bool = state.get("should_advance", True)
    status: str = state.get("status", "in_progress")

    # If the interview was completed before this point (e.g. last question answered)
    if status in ("completed", "error"):
        return END

    if shouldAdvance:
        # Follow-up was bypassed → deliver next planned question via conductorAgent
        return "conductorAgent"

    # Follow-up question was injected into state — stop the graph here.
    # The API route will read state["next_question"] and serve the follow-up.
    return END


def routeAfterConductor(state: dict) -> str:
    """
    Terminal conditional edge after conductorAgent.

    Routes to END when:
        - status == "completed"  (all planned questions delivered)
        - status == "error"
        - next_question is None  (safety net)

    In practice, after the full pipeline runs, conductorAgent always terminates
    the graph (routes to END). The API route controls session flow between invocations.

    Returns:
        END in all normal operation cases.
    """
    status: str = state.get("status", "")
    nextQuestion = state.get("next_question")

    if status in ("completed", "error") or nextQuestion is None:
        return END

    # Safety valve: if conductor delivered a question but status isn't "completed",
    # stop — the API route will invoke the graph again after the next answer.
    return END


def _buildInterviewGraph() -> StateGraph:
    """
    Construct and compile the full live interview StateGraph.

    Milestone 2.3 complete topology:
        START → liveCoachAgent → difficultyCalibratorAgent → followUpAgent
                    → [routeAfterFollowUp]
                        → "conductorAgent" (advance)  → [routeAfterConductor] → END
                        → END (follow-up injected, API reads it from state)
    """
    graph = StateGraph(InterviewSession)

    # ── Add nodes ──────────────────────────────────────────────────────────────
    graph.add_node("liveCoachAgent", liveCoachAgent)
    graph.add_node("difficultyCalibratorAgent", difficultyCalibratorAgent)
    graph.add_node("followUpAgent", followUpAgent)
    graph.add_node("conductorAgent", conductorAgent)

    # ── Entry point: always start with coaching after an answer ────────────────
    graph.set_entry_point("liveCoachAgent")

    # ── Linear pipeline: coach → calibrator → follow-up decision ──────────────
    graph.add_edge("liveCoachAgent", "difficultyCalibratorAgent")
    graph.add_edge("difficultyCalibratorAgent", "followUpAgent")

    # ── Conditional: follow-up result routes to conductor OR terminates ────────
    graph.add_conditional_edges(
        "followUpAgent",
        routeAfterFollowUp,
        {
            "conductorAgent": "conductorAgent",
            END: END,
        },
    )

    # ── Terminal: conductor always routes to END ───────────────────────────────
    graph.add_conditional_edges(
        "conductorAgent",
        routeAfterConductor,
        {END: END},
    )

    return graph.compile()


# Compile on import — singleton graph object
interviewGraph = _buildInterviewGraph()
