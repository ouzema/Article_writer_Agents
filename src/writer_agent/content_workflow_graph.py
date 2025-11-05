"""Content Creation Workflow Graph with human-in-the-loop feedback."""

from typing import Literal

from langgraph.graph import StateGraph, START, END
from langgraph.types import Command

from writer_agent.context import Context
from writer_agent.content_workflow_state import State, InputState, OutputState
from writer_agent.content_workflow_nodes import (
    orchestrator_node,
    basic_llm_response_node,
    analyzer_collector_node,
    plan_writer_node,
    draft_writer_node,
    critic_agent_node,
    human_feedback_draft_node,
    save_to_db_node,
    final_drafter_node,
)


def route_orchestrator(state: State) -> Literal["basic_llm_response", "analyzer_collector"]:
    """Route based on whether it's a general question or complex task."""
    if state.get("is_general_question", False):
        return "basic_llm_response"
    return "analyzer_collector"


def route_critic_feedback(state: State) -> Literal["human_feedback_draft", "save_to_db"]:
    """Route based on critic's approval."""
    if state.get("critic_approved", False):
        return "save_to_db"
    return "human_feedback_draft"


# Build the graph
builder = StateGraph(
    State,
    input_schema=InputState,
    output_schema=OutputState,
    context_schema=Context
)

# Add all nodes
builder.add_node("orchestrator", orchestrator_node)
builder.add_node("basic_llm_response", basic_llm_response_node)
builder.add_node("analyzer_collector", analyzer_collector_node)
builder.add_node("plan_writer", plan_writer_node)
builder.add_node("draft_writer", draft_writer_node)
builder.add_node("critic_agent", critic_agent_node)
builder.add_node("human_feedback_draft", human_feedback_draft_node)
builder.add_node("save_to_db", save_to_db_node)
builder.add_node("final_drafter", final_drafter_node)

# Set entry point
builder.add_edge(START, "orchestrator")

# Orchestrator routing
builder.add_conditional_edges(
    "orchestrator",
    route_orchestrator,
    {
        "basic_llm_response": "basic_llm_response",
        "analyzer_collector": "analyzer_collector"
    }
)

# Simple path: general questions go straight to end
builder.add_edge("basic_llm_response", END)

# Complex path: Step-by-step content creation with human validation
# 1. analyzer_collector: Research (can loop back to itself via Command)
# 2. plan_writer: Create numbered steps plan (can loop via Command)
# 3. draft_writer → critic_agent → human_feedback_draft (loops per step)
#    - Each step goes through draft → critic → human approval
#    - If approved: move to next step (back to draft_writer) or save_to_db
#    - If revision: loop back to draft_writer for same step
# 4. save_to_db: Only after ALL steps approved
# 5. final_drafter: Polish final content

builder.add_edge("analyzer_collector", "plan_writer")
builder.add_edge("plan_writer", "draft_writer")

# Step-by-step loop: draft → critic → human (repeats for each step)
builder.add_edge("draft_writer", "critic_agent")

# Add conditional routing from critic to human OR save_to_db
# (Note: We actually want to always go to human_feedback_draft first)
builder.add_edge("critic_agent", "human_feedback_draft")

# human_feedback_draft returns Command - need explicit routing  
# Add a pass-through path so LangGraph knows these nodes are reachable
def route_human_feedback(state: State) -> str:
    """Dummy router - actual routing done by Command in node.
    This ensures save_to_db is recognized as reachable."""
    # This won't actually be called since node returns Command
    return "save_to_db"

builder.add_conditional_edges(
    "human_feedback_draft",
    route_human_feedback,
    {
        "draft_writer": "draft_writer",
        "save_to_db": "save_to_db",
        "__end__": END
    }
)

# Post-approval flow
builder.add_edge("save_to_db", "final_drafter")
builder.add_edge("final_drafter", END)

# Compile the graph
content_workflow_graph = builder.compile(
    name="Content Creation Workflow",
    interrupt_before=[]
)
