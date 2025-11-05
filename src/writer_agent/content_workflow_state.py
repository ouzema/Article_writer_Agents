"""State definitions for the content creation workflow."""

from typing import Annotated, List
from typing_extensions import TypedDict

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class State(TypedDict):
    """Main state for the content creation workflow."""
    
    # Messages history
    messages: Annotated[List[BaseMessage], add_messages]
    
    # User's original input
    user_input: str
    
    # Orchestrator decision
    is_general_question: bool
    
    # Analysis and research
    research_data: str
    collected_information: List[str]
    
    # Planning
    content_plan: str
    plan_approved: bool
    plan_steps: List[str]  # Individual steps from the plan
    current_step_index: int  # Which step we're working on
    completed_steps: List[str]  # Steps that passed human validation
    
    # Drafting
    draft_content: str
    draft_iteration: int
    current_step_draft: str  # Draft for current step only
    
    # Critic feedback
    critic_feedback: str
    critic_approved: bool
    step_approved: bool  # Human approval for current step
    
    # Final output
    final_content: str
    
    # Human feedback tracking
    human_feedback: str
    needs_human_input: bool


class InputState(TypedDict):
    """Input state for the workflow."""
    
    messages: List[BaseMessage]
    user_input: str


class OutputState(TypedDict):
    """Output state for the workflow."""
    
    messages: List[BaseMessage]
    final_content: str
