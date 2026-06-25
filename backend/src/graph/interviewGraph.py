# ─────────────────────────────────────────────────────────────────────────────
# backend/src/graph/interviewGraph.py
#
# Interview Graph — Core LangGraph state machine for the live interview phase
#
# Milestone 2.2 scope (skeleton):
#   This graph handles the question delivery loop only. Advanced feedback loops
#   (LiveCoachAgent, DifficultyCalibrator, FollowUpAgent) will be added in Milestone 2.3.
#
# Graph topology (Milestone 2.2):
#
#   START → conductorAgent → [conditional] → END            (interview complete)
#                          ↗ conductorAgent                  (next question)
#
# The "question loop" in LangGraph is NOT a Python loop — it is a conditional edge
# that routes back to conductorAgent when more questions remain. The graph terminates
# (routes to END) when conductorAgent signals status == "completed".
#
# Conditional routing function:
#   routeAfterConductor(state) → "conductorAgent" | END
#
# Usage:
#   Per-question invocation from the API route:
#     from src.graph.interviewGraph import interviewGraph
#     result = await interviewGraph.ainvoke(session_state)
#
#   The API route is responsible for:
#     1. Loading the session from memory/disk.
#     2. Invoking interviewGraph.ainvoke(session).
#     3. Persisting the returned state back via sessionManager.
#
# Exports: interviewGraph, routeAfterConductor
# ─────────────────────────────────────────────────────────────────────────────

from langgraph.graph import StateGraph, END

from src.graph.sessionState import InterviewSession
from src.agents.conductorAgent import conductorAgent


# ── Conditional Routing ────────────────────────────────────────────────────────

def routeAfterConductor(state: dict) -> str:
    """
    Conditional edge function: decide what happens after conductorAgent runs.

    Routes to END when:
        - state["status"] == "completed"   (all questions delivered)
        - state["status"] == "error"        (something failed)
        - state["next_question"] is None   (safety net)

    Routes back to "conductorAgent" when:
        - More questions remain in the plan.

    Note (Milestone 2.3 extension point):
        When FollowUpAgent is integrated, this edge will be replaced by a more
        complex routing function that checks shouldFollowUp() and routes to
        "followUpAgent" → "liveCoachAgent" → "difficultyCalibrator" → "conductorAgent".

    Args:
        state: Full InterviewSession dict after conductorAgent ran.

    Returns:
        Node name to route to, or END.
    """
    status = state.get("status", "")
    nextQuestion = state.get("next_question")

    if status in ("completed", "error") or nextQuestion is None:
        return END

    # More questions remain — loop back to conductor
    # (Milestone 2.3: this will route to liveCoachAgent after answer submission)
    return "conductorAgent"


def _buildInterviewGraph() -> StateGraph:
    """
    Construct and compile the live interview StateGraph skeleton.

    Milestone 2.2 topology:
        START → conductorAgent → routeAfterConductor → END / conductorAgent

    Each call to `interviewGraph.ainvoke(state)` runs ONE full pass of the graph,
    delivering one question. The API route calls invoke once per answer submission.
    """
    graph = StateGraph(InterviewSession)

    # ── Add nodes ──────────────────────────────────────────────────────────────
    graph.add_node("conductorAgent", conductorAgent)

    # ── Entry point ────────────────────────────────────────────────────────────
    graph.set_entry_point("conductorAgent")

    # ── Conditional edge from conductor ───────────────────────────────────────
    graph.add_conditional_edges(
        "conductorAgent",
        routeAfterConductor,
        {
            END: END,
            "conductorAgent": "conductorAgent",
        },
    )

    return graph.compile()


# Compile on import — singleton graph object
interviewGraph = _buildInterviewGraph()
