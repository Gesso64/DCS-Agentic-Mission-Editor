"""Campaign layer: multi-mission orchestration with persistent state.

NOT YET IMPLEMENTED — see PLAN.md Phase 10.

A campaign is a sequence of missions. State (score, losses, captured
airfields, completed missions) is persisted to JSON between runs.
Branching missions select the next mission based on the after-action
report from the previous one.

Two-tier model strategy (PLAN.md §0.1):
  - Architect (Sonnet): designs the CampaignSpec skeleton + templates
  - Renderer (GLM):     fills templates against current state per run
"""
