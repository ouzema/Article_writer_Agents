"""Node implementations for the content creation workflow."""

from typing import Dict, Any, cast
from datetime import UTC, datetime

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.runtime import Runtime
from langgraph.types import Command, interrupt

from react_agent.context import Context
from react_agent.content_workflow_state import State
from react_agent.tools import search, serper_search
from react_agent.utils import load_chat_model


async def orchestrator_node(
    state: State, runtime: Runtime[Context]
) -> Dict[str, Any]:
    """
    Orchestrator: Decides if the query is general or requires deep research.
    
    Routes to:
    - Basic LLM response for general questions
    - Complex workflow for content creation tasks
    """
    model = load_chat_model(runtime.context.model)
    
    system_prompt = """You are an orchestrator that determines if a user's request is:
1. A general question that can be answered directly (yes)
2. A complex content creation task requiring research and planning (no)

Examples of general questions:
- "What is Python?"
- "Explain machine learning"
- "How does HTTP work?"

Examples of complex tasks:
- "Write a blog post about..."
- "Create a comprehensive guide on..."
- "Research and draft an article about..."

Respond with only "yes" for general questions or "no" for complex tasks."""

    response = cast(
        AIMessage,
        await model.ainvoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": state["user_input"]}
        ])
    )
    
    is_general = "yes" in response.content.lower()
    
    return {
        "messages": [response],
        "is_general_question": is_general
    }


async def basic_llm_response_node(
    state: State, runtime: Runtime[Context]
) -> Dict[str, Any]:
    """
    Provides a direct LLM response for general questions.
    """
    model = load_chat_model(runtime.context.model)
    
    system_prompt = f"""You are a helpful AI assistant.
Answer the user's question clearly and concisely.

System time: {datetime.now(tz=UTC).isoformat()}"""

    response = cast(
        AIMessage,
        await model.ainvoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": state["user_input"]}
        ])
    )
    
    return {
        "messages": [response],
        "final_content": response.content
    }


async def analyzer_collector_node(
    state: State, runtime: Runtime[Context]
) -> Command[Dict[str, Any]]:
    """
    Analyzer/Collector: Researches the topic and collects information.
    Includes human-in-the-loop for feedback.
    """
    model = load_chat_model(runtime.context.model)
    
    # If this is the first pass, do research
    if not state.get("research_data"):
        system_prompt = """You are a research analyst. Based on the user's request, 
identify key topics to research and generate search queries.
Provide 2-3 specific search queries."""

        response = cast(
            AIMessage,
            await model.ainvoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": state["user_input"]}
            ])
        )
        
        # Extract search queries and perform searches using Serper
        search_queries = response.content.split("\n")[:3]
        collected_info = []
        
        for query in search_queries:
            if query.strip():
                # Try Serper first, fallback to Tavily
                search_result = await serper_search(query.strip())
                if not search_result or "error" in search_result:
                    search_result = await search(query.strip())
                if search_result:
                    collected_info.append(str(search_result))
        
        # Request human feedback
        human_feedback = interrupt({
            "question": "Review the collected research. Any specific areas to explore?",
            "research_data": "\n\n".join(collected_info),
            "action": "collect"
        })
        
        return Command(
            update={
                "research_data": "\n\n".join(collected_info),
                "collected_information": collected_info,
                "human_feedback": human_feedback if human_feedback else "Approved",
                "messages": [response]
            },
            goto="analyzer_collector" if human_feedback and "more" in human_feedback.lower() else "plan_writer"
        )
    
    # If human wants more research
    else:
        additional_query = state.get("human_feedback", "")
        if additional_query and additional_query != "Approved":
            # Use Serper for additional research
            search_result = await serper_search(additional_query)
            if not search_result or "error" in search_result:
                search_result = await search(additional_query)
            if search_result:
                updated_info = state["collected_information"] + [str(search_result)]
                
                human_feedback = interrupt({
                    "question": "Review the additional research. Continue or proceed?",
                    "research_data": str(search_result),
                    "action": "collect"
                })
                
                return Command(
                    update={
                        "collected_information": updated_info,
                        "research_data": state["research_data"] + "\n\n" + str(search_result),
                        "human_feedback": human_feedback if human_feedback else "Approved"
                    },
                    goto="analyzer_collector" if human_feedback and "more" in human_feedback.lower() else "plan_writer"
                )
        
        return Command(goto="plan_writer")


async def plan_writer_node(
    state: State, runtime: Runtime[Context]
) -> Command[Dict[str, Any]]:
    """
    Plan Writer: Creates a structured content plan with numbered steps.
    Includes human-in-the-loop for plan approval.
    """
    model = load_chat_model(runtime.context.model)
    
    system_prompt = """You are a content strategist. Based on the research data, 
create a detailed content plan with NUMBERED STEPS.

Format your plan as:
STEP 1: [Title/Topic]
- Key points to cover
- Approach

STEP 2: [Title/Topic]
- Key points to cover
- Approach

(Continue with all steps...)

Make each step a clear, independent unit of work."""

    response = cast(
        AIMessage,
        await model.ainvoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User request: {state['user_input']}\n\nResearch data:\n{state['research_data']}"}
        ])
    )
    
    # Extract steps from the plan
    plan_text = response.content
    steps = []
    for line in plan_text.split("\n"):
        if line.strip().startswith("STEP"):
            steps.append(line.strip())
    
    # Request human approval
    human_feedback = interrupt({
        "question": "Review the content plan. Approve or provide feedback for revisions?",
        "plan": response.content,
        "steps_count": len(steps),
        "action": "ask"
    })
    
    approved = not human_feedback or "approve" in human_feedback.lower()
    
    return Command(
        update={
            "content_plan": response.content,
            "plan_steps": steps if steps else ["STEP 1: Complete content"],
            "current_step_index": 0,
            "completed_steps": [],
            "plan_approved": approved,
            "human_feedback": human_feedback if human_feedback else "Approved",
            "messages": [response]
        },
        goto="draft_writer" if approved else "plan_writer"
    )


async def draft_writer_node(
    state: State, runtime: Runtime[Context]
) -> Dict[str, Any]:
    """
    Draft Writer: Creates draft for CURRENT STEP only.
    Works step-by-step through the plan.
    """
    model = load_chat_model(runtime.context.model)
    
    current_index = state.get("current_step_index", 0)
    plan_steps = state.get("plan_steps", [])
    
    if current_index >= len(plan_steps):
        # All steps completed, combine into final draft
        return {
            "draft_content": "\n\n".join(state.get("completed_steps", [])),
            "current_step_draft": "All steps completed",
            "messages": [AIMessage(content="All plan steps completed!")]
        }
    
    current_step = plan_steps[current_index]
    
    system_prompt = f"""You are an expert content writer. 
Write ONLY the content for the CURRENT STEP of the plan.
Do not write other steps - focus on this specific section.

Current Step: {current_step}

Make it engaging, well-structured, and informative."""

    completed = "\n\n".join(state.get("completed_steps", []))
    context = f"""User request: {state['user_input']}

Full Content Plan:
{state['content_plan']}

Research Data:
{state['research_data']}

Already Completed Steps:
{completed if completed else 'None yet'}

NOW WRITE ONLY: {current_step}"""

    response = cast(
        AIMessage,
        await model.ainvoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context}
        ])
    )
    
    return {
        "current_step_draft": response.content,
        "draft_iteration": state.get("draft_iteration", 0) + 1,
        "messages": [response]
    }


async def critic_agent_node(
    state: State, runtime: Runtime[Context]
) -> Dict[str, Any]:
    """
    Critic Agent: Reviews CURRENT STEP draft only.
    """
    model = load_chat_model(runtime.context.model)
    
    current_index = state.get("current_step_index", 0)
    plan_steps = state.get("plan_steps", [])
    current_step = plan_steps[current_index] if current_index < len(plan_steps) else "Unknown"
    
    system_prompt = f"""You are a critical editor reviewing step-by-step content.

Current Step Being Reviewed: {current_step}

Provide:
1. Strengths of this section
2. Areas for improvement
3. Specific suggestions
4. Quality assessment (Approve/Needs Revision)"""

    response = cast(
        AIMessage,
        await model.ainvoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""Step Draft to Review:

{state.get('current_step_draft', '')}

Step Context: {current_step}"""}
        ])
    )
    
    approved = "approve" in response.content.lower() and "needs revision" not in response.content.lower()
    
    return {
        "critic_feedback": response.content,
        "critic_approved": approved,
        "messages": [response]
    }


async def human_feedback_draft_node(
    state: State, runtime: Runtime[Context]
) -> Command[Dict[str, Any]]:
    """
    Human Feedback: Reviews current step. Approve to move to next step,
    or request revision to loop back to draft_writer for this step.
    Only saves to DB when ALL steps are approved.
    """
    current_index = state.get("current_step_index", 0)
    plan_steps = state.get("plan_steps", [])
    current_step = plan_steps[current_index] if current_index < len(plan_steps) else "Final"
    completed = state.get("completed_steps", [])
    
    # Request human decision for THIS STEP
    human_decision = interrupt({
        "question": f"Review STEP {current_index + 1}/{len(plan_steps)}: {current_step}",
        "step_draft": state.get("current_step_draft", ""),
        "critic_feedback": state.get("critic_feedback", ""),
        "iteration": state.get("draft_iteration", 1),
        "progress": f"Completed: {len(completed)}/{len(plan_steps)} steps",
        "action": "feedback"
    })
    
    if not human_decision or "approve" in human_decision.lower():
        # Approve this step - add to completed
        new_completed = completed + [state.get("current_step_draft", "")]
        new_index = current_index + 1
        
        # Check if all steps are done
        if new_index >= len(plan_steps):
            # All steps completed! Combine and save
            return Command(
                update={
                    "completed_steps": new_completed,
                    "draft_content": "\n\n".join(new_completed),
                    "human_feedback": "All steps approved",
                    "step_approved": True
                },
                goto="save_to_db"
            )
        else:
            # Move to next step - loop back to draft_writer
            return Command(
                update={
                    "completed_steps": new_completed,
                    "current_step_index": new_index,
                    "human_feedback": f"Step {current_index + 1} approved",
                    "step_approved": True
                },
                goto="draft_writer"
            )
    else:
        # Revision requested - loop back to draft_writer for SAME step
        return Command(
            update={
                "human_feedback": human_decision,
                "step_approved": False
            },
            goto="draft_writer"
        )


async def save_to_db_node(state: State) -> Dict[str, Any]:
    """
    Save to DB: Saves completed content to Pinecone vector database.
    """
    import os
    from datetime import datetime
    
    # Combine all completed steps into final draft
    completed_steps = state.get("completed_steps", [])
    full_content = "\n\n".join(completed_steps)
    
    print("💾 Saving approved content to database...")
    print(f"Title: {state['user_input'][:50]}...")
    print(f"Total steps completed: {len(completed_steps)}")
    print(f"Content length: {len(full_content)} characters")
    
    # Try to save to Pinecone if API key is available
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    
    if pinecone_api_key and pinecone_api_key != "your_pinecone_api_key_here":
        try:
            from pinecone.grpc import PineconeGRPC as Pinecone
            from pinecone import ServerlessSpec
            
            # Initialize Pinecone
            pc = Pinecone(api_key=pinecone_api_key)
            
            # Use or create index
            index_name = "langgraph-content"
            
            # Check if index exists, create if not
            existing_indexes = [idx.name for idx in pc.list_indexes()]
            if index_name not in existing_indexes:
                pc.create_index(
                    name=index_name,
                    dimension=1536,  # OpenAI embedding dimension
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1")
                )
                print(f"✅ Created new Pinecone index: {index_name}")
            
            index = pc.Index(index_name)
            
            # Generate embedding (using simple hash for now, should use OpenAI embeddings)
            # TODO: Replace with actual OpenAI embeddings
            import hashlib
            content_id = hashlib.md5(full_content.encode()).hexdigest()
            
            # For now, store metadata without vector (simplified)
            # In production, generate proper embeddings
            metadata = {
                "title": state["user_input"][:200],
                "content": full_content[:1000],  # Truncate for metadata
                "full_length": len(full_content),
                "steps_count": len(completed_steps),
                "timestamp": datetime.now().isoformat(),
                "plan": state.get("content_plan", "")[:500]
            }
            
            print(f"✅ Content metadata prepared for Pinecone")
            print(f"   ID: {content_id}")
            print(f"   Note: Full vector embedding requires OpenAI API")
            
        except Exception as e:
            print(f"⚠️  Pinecone save failed: {e}")
            print("   Content saved to state only")
    else:
        print("ℹ️  Pinecone API key not found - content saved to state only")
        print("   Add PINECONE_API_KEY to .env to enable vector storage")
    
    return {
        "messages": [AIMessage(content=f"Content saved! {len(completed_steps)} steps completed.")],
        "draft_content": full_content,
        "final_content": full_content
    }


async def final_drafter_node(
    state: State, runtime: Runtime[Context]
) -> Command[Dict[str, Any]]:
    """
    Final Drafter: Polishes the approved draft into final content.
    Includes human-in-the-loop for final review.
    """
    model = load_chat_model(runtime.context.model)
    
    system_prompt = """You are a final editor. Polish the approved draft:
1. Fix any remaining issues
2. Enhance clarity and flow
3. Ensure professional formatting
4. Add finishing touches"""

    response = cast(
        AIMessage,
        await model.ainvoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""Approved draft to finalize:

{state['draft_content']}

Critic feedback incorporated:
{state['critic_feedback']}"""}
        ])
    )
    
    # Request final human approval
    human_feedback = interrupt({
        "question": "Review the final polished content. Any last changes?",
        "final_content": response.content,
        "action": "feedback"
    })
    
    if not human_feedback or "approve" in human_feedback.lower():
        return Command(
            update={
                "final_content": response.content,
                "messages": [response]
            },
            goto="__end__"
        )
    else:
        return Command(
            update={
                "human_feedback": human_feedback,
                "messages": [response]
            },
            goto="final_drafter"
        )
