"""
Simulation script demonstrating end-to-end interview practice session
for Aditi (UX Research Intern) and Rahul (Associate Product Manager).
"""

import json
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from app.evaluator import evaluator
from app.database import init_db, get_longitudinal_progress

init_db()

print("=" * 70)
print("  SIMULATION RUN: ADITI (UX RESEARCH INTERN) — PROTOTYPE A FLOW")
print("=" * 70)

# Question
question = "Tell me about a time when you worked with a difficult teammate. What was the situation and how did you resolve it?"
print(f"\n[INTERVIEWER QUESTION]:\n\"{question}\"\n")

# Attempt 1
ans1 = (
    "In my previous UX research internship project, I had a disagreement with our engineer on the dashboard layout. "
    "The engineer wanted fewer filters to save loading time and technical effort, while I wanted all filters visible because our exploratory user interviews showed people needed search precision. "
    "It was frustrating because we had a deadline coming up. I scheduled a 30-minute sync to talk through user needs and we agreed on a compromise where we kept the main filters and hid the rest."
)
print("[CANDIDATE ANSWER - ATTEMPT 1]:")
print(f"\"{ans1}\"\n")

eval1 = evaluator.evaluate_answer(question, ans1, "UX Research Intern", 1)
print(f"[AI EVALUATION 1] Overall Score: {eval1.overall_score}/10")
print(f" • Relevance:          {eval1.relevance.score}/10 ({eval1.relevance.status})")
print(f" • Specificity:        {eval1.specificity.score}/10 ({eval1.specificity.status})")
print(f" • Evidence & Outcome: {eval1.evidence_outcome.score}/10 ({eval1.evidence_outcome.status}) <-- Missing tangible outcome!")
print(f" • Structure & Clarity:{eval1.structure_clarity.score}/10 ({eval1.structure_clarity.status})")
print(f"Strengths: {eval1.strengths}")
print(f"Needs Improvement: {eval1.needs_improvement}")
print(f"Actionable Suggestions: {eval1.actionable_suggestions}")

print("\n--- [WHY THIS FEEDBACK? AUDIT MODAL] ---")
print(json.dumps(eval1.why_feedback_summary, indent=2))

# Candidate Reflection
print("\n--- [CANDIDATE GUIDED REFLECTION] ---")
refl_change = "I need to explain what happened AFTER the compromise. Did the product actually succeed? Did users find the filters? I will add metrics and testing evidence."
refl_learn = "I tend to stop my answer once the conflict is resolved socially, but interviewers need to see the business and user impact."
print(f"Prompt 1 (What would you change?): \"{refl_change}\"")
print(f"Prompt 2 (What did you learn?):     \"{refl_learn}\"")

# Attempt 2 (Retry)
ans2 = (
    "During our cross-functional sprint for the analytics dashboard, our lead engineer and I disagreed on whether to include advanced filter menus or keep them minimal to optimize load speed. "
    "Rather than debating hypotheticals, I scheduled a 30-minute working session where I shared a 2-minute video compilation of our usability testing sessions showing that 4 out of 5 users failed search tasks without specific filters. "
    "Seeing the direct user struggle aligned our priorities. I proposed a phased compromise: collapsible advanced filters with lazy loading. "
    "As a concrete result, engineering implemented the design without performance degradation, we delivered the sprint 2 days ahead of schedule, and post-launch telemetry revealed a 28% increase in task completion with zero drop-off complaints."
)
print("\n[CANDIDATE ANSWER - ATTEMPT 2 (RETRY)]:")
print(f"\"{ans2}\"\n")

eval2 = evaluator.evaluate_answer(question, ans2, "UX Research Intern", 2)
print(f"[AI EVALUATION 2] Overall Score: {eval2.overall_score}/10")
print(f" • Relevance:          {eval2.relevance.score}/10 ({eval2.relevance.status})")
print(f" • Specificity:        {eval2.specificity.score}/10 ({eval2.specificity.status})")
print(f" • Evidence & Outcome: {eval2.evidence_outcome.score}/10 ({eval2.evidence_outcome.status})")
print(f" • Structure & Clarity:{eval2.structure_clarity.score}/10 ({eval2.structure_clarity.status})")

# Comparison
comp = evaluator.compare_attempts(1, question, ans1, ans2, eval1, eval2)
print("\n--- [ATTEMPT 1 vs ATTEMPT 2 COMPARISON] ---")
print(f"Score Deltas: {comp.deltas}")
print(f"Improvements: {comp.improvements}")
print(f"Remaining Focus: {comp.focus_areas_remaining}")

# Prototype B Simulation
print("\n" + "=" * 70)
print("  PROTOTYPE B SIMULATION: CONVERSATIONAL REALISM & ADAPTIVE FOLLOW-UP")
print("=" * 70)
followup = evaluator.generate_adaptive_followup(question, ans1, "UX Research Intern")
print(f"[INTERVIEWER ADAPTIVE PROBE]:\n{followup['followup_question']}")
print(f"[ADAPTIVE TRIGGER REASON]: {followup['reasoning']}\n")
