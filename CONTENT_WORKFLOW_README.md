# Content Creation Workflow

A sophisticated multi-agent content creation system with human-in-the-loop feedback at every critical stage.

## 🎯 Workflow Overview

```
User Input
    ↓
Orchestrator (decides complexity)
    ↓
   / \
  /   \
yes   no
 ↓     ↓
Basic  Complex Workflow
LLM    ↓
END    Analyzer/Collector (with human feedback + search)
       ↓
       Plan Writer (with human approval)
       ↓
       Draft Writer
       ↓
       Critic Agent
       ↓
       Human Feedback (approve/disapprove)
       ↓
       [If approved] → Save to DB → Final Drafter (with review) → END
       [If disapproved] → Loop back to Draft Writer
```

## 📋 Graph Nodes

### 1. **Orchestrator**

- **Purpose**: Determines if the user's request is a simple question or complex content task
- **Routes to**:
  - `basic_llm_response` for general questions
  - `analyzer_collector` for complex content creation

### 2. **Basic LLM Response**

- **Purpose**: Provides direct answers to general questions
- **Ends workflow**: Yes

### 3. **Analyzer/Collector**

- **Purpose**: Researches the topic using search tools
- **Human-in-the-loop**: Reviews research, can request more data
- **Tools**: Tavily search integration
- **Loop**: Can collect more information based on human feedback

### 4. **Plan Writer**

- **Purpose**: Creates a structured content outline
- **Human-in-the-loop**: Must approve plan before proceeding
- **Loop**: Revises plan if not approved

### 5. **Draft Writer**

- **Purpose**: Writes the initial content draft based on plan
- **Uses**: Research data + content plan
- **Tracks**: Draft iteration count

### 6. **Critic Agent**

- **Purpose**: Reviews draft quality and provides feedback
- **Outputs**: Strengths, improvements, approval status

### 7. **Human Feedback (Draft)**

- **Purpose**: Final human review of draft + critic feedback
- **Options**:
  - Approve → Continue to save
  - Disapprove → Loop back to Draft Writer
  - Revise → Provide feedback and redraft

### 8. **Save to DB**

- **Purpose**: Saves approved content (placeholder for database)
- **Next**: Proceeds to final polishing

### 9. **Final Drafter**

- **Purpose**: Polishes the approved draft
- **Human-in-the-loop**: Final review before completion
- **Loop**: Can make final adjustments if needed

## 🚀 How to Use

1. **Start the LangGraph server:**

   ```powershell
   cd C:\Users\Oussema\Downloads\my_new_langgraph_project\react-agent-project
   langgraph dev --allow-blocking
   ```

2. **Access LangGraph Studio:**

   - Open: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
   - Select graph: `content_workflow`

3. **Test with different inputs:**

   **General Question (simple path):**

   ```
   "What is machine learning?"
   ```

   → Goes straight to basic LLM response

   **Complex Content Task:**

   ```
   "Write a comprehensive blog post about the future of AI in healthcare"
   ```

   → Goes through full workflow with research, planning, drafting, and review

## 🎨 Human-in-the-Loop Points

The workflow includes **4 human feedback points**:

1. **Research Review** (Analyzer/Collector)

   - Review collected research
   - Request additional searches
   - Approve to continue

2. **Plan Approval** (Plan Writer)

   - Review content outline
   - Approve or request revisions

3. **Draft Review** (Human Feedback)

   - Review draft + critic feedback
   - Approve, disapprove, or provide revision guidance

4. **Final Review** (Final Drafter)
   - Review polished content
   - Make final adjustments or approve

## 🔧 Configuration

Edit [`../../../../../C:/Users/Oussema/Downloads/my_new_langgraph_project/react-agent-project/.env`](../../../../../C:/Users/Oussema/Downloads/my_new_langgraph_project/react-agent-project/.env) for:

- `OPENAI_API_KEY`: LLM provider
- `TAVILY_API_KEY`: Search functionality
- `LANGSMITH_API_KEY`: Tracing (optional)

## 📊 State Management

The workflow tracks:

- `user_input`: Original request
- `is_general_question`: Routing decision
- `research_data`: Collected information
- `content_plan`: Approved outline
- `draft_content`: Current draft
- `draft_iteration`: Revision count
- `critic_feedback`: Quality review
- `human_feedback`: User input at each stage
- `final_content`: Polished output

## 🎯 Use Cases

Perfect for:

- ✅ Blog post creation with research
- ✅ Article writing with fact-checking
- ✅ Content that requires multiple review cycles
- ✅ High-quality content with human oversight
- ✅ Research-backed writing projects

## 🔄 Iteration Control

The graph automatically:

- Loops on disapproval
- Tracks iteration counts
- Preserves context across revisions
- Integrates human feedback into next iteration
