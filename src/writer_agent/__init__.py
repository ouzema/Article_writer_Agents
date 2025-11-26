"""Writer Agent.

This module defines a custom content creation workflow with multi-agent collaboration.
"""

from writer_agent.content_workflow_graph import content_workflow_graph

# Alias for backward compatibility
graph = content_workflow_graph

__all__ = ["content_workflow_graph", "graph"]
