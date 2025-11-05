# Content Workflow Updates

## Changes Made

### 1. **Serper API Integration for Research**

- Added `serper_search()` function to `tools.py` for comprehensive Google Search results
- `analyzer_collector_node` now uses Serper API (with Tavily fallback)
- Provides richer research data including organic results, knowledge graphs, and related searches
- **Setup**: Add `SERPER_API_KEY` to `.env` file (get from https://serper.dev/)

### 2. **Plan Writer with Human-in-the-Loop**

- Plan writer creates a **numbered step-by-step plan** (STEP 1, STEP 2, etc.)
- Human reviews and approves the plan before execution
- Can request revisions if the plan needs changes
- Each step becomes an independent unit of work

### 3. **Step-by-Step Execution Loop**

The workflow now processes content **one step at a time** with human validation:

```
For each step in the plan:
  1. Draft Writer: Writes content for CURRENT STEP only
  2. Critic Agent: Reviews the step draft
  3. Human Feedback: Approves or requests revision
     - If APPROVED: Move to next step (or save if last step)
     - If REVISION: Loop back to Draft Writer for SAME step
```

### 4. **No Save Without Human Approval**

- `save_to_db` node is **only reached after ALL steps are approved**
- Each step must pass human validation before moving forward
- Completed steps are stored in `completed_steps` array
- Progress tracking: "Completed: X/Y steps"

### 5. **Updated State Fields**

New fields in `State`:

- `plan_steps`: List of numbered steps from the plan
- `current_step_index`: Which step is currently being worked on
- `completed_steps`: Array of approved step content
- `current_step_draft`: Draft content for current step only
- `step_approved`: Boolean for step-level approval

## Workflow Flow

```
START
  ↓
orchestrator
  ↓ (if complex task)
analyzer_collector (Serper API research)
  ↓ (can loop for more research)
plan_writer (Create numbered steps + human approval)
  ↓
┌─────────────────────────────────────────────┐
│  STEP-BY-STEP LOOP (for each plan step)    │
│                                              │
│  draft_writer (write current step)          │
│    ↓                                         │
│  critic_agent (review current step)         │
│    ↓                                         │
│  human_feedback_draft (approve/revise)      │
│    ↓                                         │
│    ├─ If REVISE: Loop back to draft_writer  │
│    └─ If APPROVE:                            │
│         ├─ More steps? → draft_writer       │
│         └─ All done? → save_to_db           │
└─────────────────────────────────────────────┘
  ↓
save_to_db (only after ALL steps approved)
  ↓
final_drafter (polish final content + human review)
  ↓
END
```

## Human-in-the-Loop Checkpoints

1. **Research Phase**: Review collected research, request more if needed
2. **Plan Approval**: Approve the numbered step plan
3. **Each Step** (repeats N times):
   - Review step draft
   - Review critic feedback
   - Approve or request revision
4. **Final Content**: Review polished final version

## Example Usage

**User Request**: "Write a comprehensive blog post about AI in healthcare"

**Execution**:

1. Orchestrator → Complex task
2. Analyzer uses Serper to research AI healthcare topics
3. Plan Writer creates:
   - STEP 1: Introduction to AI in Healthcare
   - STEP 2: Current Applications and Use Cases
   - STEP 3: Benefits and Challenges
   - STEP 4: Future Trends and Predictions
   - STEP 5: Conclusion
4. **Human approves plan**
5. Loop through each step:
   - Write STEP 1 → Critic reviews → Human approves → ✓
   - Write STEP 2 → Critic reviews → Human requests revision → Rewrite STEP 2 → Approve → ✓
   - Write STEP 3 → Critic reviews → Human approves → ✓
   - Write STEP 4 → Critic reviews → Human approves → ✓
   - Write STEP 5 → Critic reviews → Human approves → ✓
6. All steps complete → Save to DB
7. Final Drafter polishes → Human reviews → Complete!

## Setup Required

Add to `.env`:

```bash
SERPER_API_KEY=your_serper_api_key_here
```

Get your Serper API key from: https://serper.dev/

- Free tier: 2,500 queries/month
- Paid plans available for higher volume
