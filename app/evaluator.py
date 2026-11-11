"""
Rubric Evaluator & Adaptive Question Engine.
Provides inspectable, transparent rubric evaluations, 'Why This Feedback' evidence extraction,
attempt comparisons, and adaptive follow-up question generation.
Supports Google Gemini Free Tier API with 100% offline deterministic fallback.
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
import httpx
from app.models import EvaluationResult, RubricCriterion, AttemptComparison
from app.data_manager import get_question_bank_for_role
from app.env_loader import get_env_variable

logger = logging.getLogger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "nvidia/nemotron-3.5-super-vl:free"


class InterviewEvaluator:
    def __init__(self):
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
        self.openrouter_api_key = os.environ.get("OPENROUTER_API_KEY", "")
        self.openrouter_model = os.environ.get("OPENROUTER_MODEL", OPENROUTER_MODEL)
        # Action keywords
        self.action_words = [
            "decided", "implemented", "organized", "scheduled", "analyzed", "researched",
            "facilitated", "moderated", "created", "built", "designed", "resolved", "conducted",
            "initiated", "collaborated", "aligned", "prioritized", "negotiated"
        ]
        # Outcome keywords (metrics, deliverables, results)
        self.outcome_words = [
            "result", "outcome", "improved", "increased", "decreased", "saved", "delivered",
            "completed", "launched", "achieved", "reduced", "metric", "percent", "%",
            "success", "timeline", "consensus", "agreed", "validated", "adopted", "promoted"
        ]
        # Specificity indicators (tools, frameworks, concrete entities)
        self.specificity_words = [
            "figma", "python", "sql", "jira", "sprint", "star", "usability", "metric", "kpi",
            "interview", "survey", "prototype", "wireframe", "stakeholder", "engineer", "designer",
            "product", "user", "cohort", "a/b test", "roadmap", "architecture", "git"
        ]

    def get_openrouter_api_key(self) -> str:
        key = self.openrouter_api_key or get_env_variable("OPENROUTER_API_KEY", "")
        clean_key = key.strip().strip('"').strip("'")
        if clean_key:
            if clean_key.startswith("v1-"):
                clean_key = f"sk-or-{clean_key}"
            elif not clean_key.startswith("sk-"):
                clean_key = f"sk-or-v1-{clean_key}"
        return clean_key

    def get_gemini_api_key(self) -> str:
        key = self.gemini_api_key or get_env_variable("GEMINI_API_KEY", "")
        return key.strip().strip('"').strip("'")

    def evaluate_answer(
        self,
        question_text: str,
        answer_text: str,
        job_role: str = "General",
        attempt_number: int = 1
    ) -> EvaluationResult:
        cleaned = answer_text.strip()
        sentences = [s.strip() for s in re.split(r'[.!?]+', cleaned) if len(s.strip()) > 5]
        words = cleaned.split()
        word_count = len(words)

        # Baseline checks
        if word_count < 15:
            # Very short / incomplete answer
            rel_score = 4.0
            spec_score = 3.0
            evid_score = 2.0
            struct_score = 3.0
            overall = 3.0
            return EvaluationResult(
                overall_score=overall,
                relevance=RubricCriterion(
                    name="Relevance",
                    score=rel_score,
                    status="Needs Improvement",
                    reason="The response is too brief to adequately address the core dimensions of the question.",
                    evidence_found="Brief statement provided.",
                    missing_aspect="Context and role-specific depth.",
                    rubric_definition="Addresses the specific prompt directly, stays on topic, and reflects target role competencies."
                ),
                specificity=RubricCriterion(
                    name="Specificity",
                    score=spec_score,
                    status="Needs Improvement",
                    reason="No concrete examples, tools, or specific methods were cited.",
                    evidence_found="None",
                    missing_aspect="Concrete situational details, names, tools, or methodologies.",
                    rubric_definition="Mentions concrete details, names, tools, technologies, and specific methodologies rather than broad generalities."
                ),
                evidence_outcome=RubricCriterion(
                    name="Evidence & Outcome",
                    score=evid_score,
                    status="Needs Improvement",
                    reason="No tangible result or measurable outcome was presented.",
                    evidence_found="None",
                    missing_aspect="Deliverables, metrics, or positive resolution.",
                    rubric_definition="Provides concrete results, quantifiable metrics, positive impact, and tangible deliverables (the 'R' in STAR)."
                ),
                structure_clarity=RubricCriterion(
                    name="Structure & Clarity",
                    score=struct_score,
                    status="Needs Improvement",
                    reason="Lacks narrative flow or STAR structure.",
                    evidence_found="Fragmentary explanation.",
                    missing_aspect="Progression from Situation to Task, Action, and Result.",
                    rubric_definition="Follows an organized narrative arc (e.g. STAR framework) with coherent progression."
                ),
                strengths=["Started addressing the topic."],
                needs_improvement=["Answer is too short (under 15 words). Elaborate using the STAR method."],
                actionable_suggestions=["Expand on the situation, the specific actions you took, and what resulted from it."],
                example_improved_answer=self._generate_example_answer(question_text, job_role),
                why_feedback_summary={
                    "primary_deficit": "Word count below threshold for substantive evaluation",
                    "recommendation": "Use 100-250 words following Situation, Task, Action, and Result."
                }
            )

        # 1. Relevance Score calculation (0-10)
        relevance_evidence = []
        rel_score = 7.0
        # Check alignment with question keywords
        q_keywords = [w.lower() for w in re.findall(r'\b\w{4,}\b', question_text)]
        overlap = [w for w in q_keywords if w in cleaned.lower()]
        if len(overlap) >= 3:
            rel_score += 1.5
            relevance_evidence.append(f"Directly addressed question concepts: {', '.join(set(overlap[:4]))}")
        elif len(overlap) >= 1:
            rel_score += 0.5
            relevance_evidence.append(f"Referenced question elements: {', '.join(set(overlap[:2]))}")
        else:
            rel_score -= 1.0

        if word_count > 60:
            rel_score += 0.5
        rel_score = min(9.5, max(4.0, round(rel_score, 1)))

        # 2. Specificity Score calculation (0-10)
        spec_hits = [w for w in self.specificity_words if re.search(r'\b' + re.escape(w) + r'\b', cleaned.lower())]
        spec_evidence = []
        has_numbers = bool(re.search(r'\b\d+\b|\b\d+%\b', cleaned))

        spec_score = 5.0
        if spec_hits:
            spec_score += min(3.0, len(spec_hits) * 0.8)
            spec_evidence.append(f"Concrete terms used: {', '.join(spec_hits[:4])}")
        if has_numbers:
            spec_score += 1.5
            num_match = re.search(r'\b\d+(?:%|\s+[a-zA-Z]+)?', cleaned)
            spec_evidence.append(f"Quantifiable detail cited: '{num_match.group(0)}'")
        if word_count > 120:
            spec_score += 0.5

        spec_score = min(9.5, max(3.5, round(spec_score, 1)))

        # 3. Evidence & Outcome Score calculation (0-10)
        # Outcome metrics require quantifiable impact or explicit outcome statements (STAR: Result)
        outcome_metric_match = re.search(r'\b\d+%\b|\b\d+\s*(?:percent|%|days ahead|higher|lower|increase|decrease|rate|satisfaction|completion)\b', cleaned, re.IGNORECASE)
        has_explicit_result_phrase = bool(re.search(r'\b(?:result|outcome|analytics revealed|metrics showed|completion rate|consequence)\b', cleaned, re.IGNORECASE))
        has_resolution = bool(re.search(r'\b(?:compromise|resolved|agreed|finished)\b', cleaned, re.IGNORECASE))

        evid_evidence = []
        evid_missing = None

        if outcome_metric_match or (has_explicit_result_phrase and ("%" in cleaned or "rate" in cleaned.lower() or "improved" in cleaned.lower())):
            evid_score = 8.0
            if outcome_metric_match:
                evid_score += 0.5
            outcome_sentences = [s for s in sentences if any(w in s.lower() for w in ["result", "outcome", "rate", "%", "improved", "ahead"])]
            if outcome_sentences:
                evid_evidence.append(f"Outcome clearly articulated: “{outcome_sentences[0].strip()}”")
            else:
                evid_evidence.append("Described positive measurable team and project results.")
        elif has_resolution or has_explicit_result_phrase:
            # Described action / compromise, but lacks measurable outcome (The Docx Survey / Scenario case: 4.0 to 5.0)
            evid_score = 4.5
            evid_evidence.append("Mentioned that a compromise was reached, but omitted concrete measurable outcomes.")
            evid_missing = "Concrete measurable result, metric, or user impact percentage (e.g., '28% higher task completion rate')."
        else:
            # Typical Survey/Docx scenario: "Situation clearly explained, outcome is missing (4/10)"
            evid_score = 4.0
            evid_missing = "Outcome is completely missing. Response describes actions taken but does not state the final tangible result or evidence."

        evid_score = min(9.5, max(3.0, round(evid_score, 1)))

        # 4. Structure & Clarity (0-10)
        struct_score = 6.0
        struct_evidence = []
        action_hits = [w for w in self.action_words if re.search(r'\b' + re.escape(w) + r'\b', cleaned.lower())]

        if len(sentences) >= 3:
            struct_score += 1.0
            struct_evidence.append(f"Well-developed response structure across {len(sentences)} distinct sentences.")
        if action_hits:
            struct_score += 1.0
            struct_evidence.append(f"Clear action-oriented phrasing ('{action_hits[0]}', '{action_hits[1] if len(action_hits)>1 else ''}').")
        if evid_score >= 7.0 and len(sentences) >= 3:
            struct_score += 1.0
            struct_evidence.append("Follows natural STAR progression (Situation → Action → Result).")

        struct_score = min(9.5, max(4.0, round(struct_score, 1)))

        # Overall weighted score
        overall = round((rel_score * 0.25) + (spec_score * 0.25) + (evid_score * 0.3) + (struct_score * 0.2), 1)

        # Qualitative synthesis
        strengths = []
        needs_improvement = []
        suggestions = []

        if rel_score >= 7.5:
            strengths.append("Situation and context are clearly framed and directly relevant to the role.")
        if spec_score >= 7.5:
            strengths.append(f"Great use of concrete terminology ({', '.join(spec_hits[:3]) if spec_hits else 'specific details'}).")
        if struct_score >= 7.5:
            strengths.append("Answer follows a coherent narrative sequence with clear professional actions.")
        if not strengths:
            strengths.append("You clearly explained the situation and the initial friction point.")

        if evid_score < 7.0:
            needs_improvement.append("Outcome is missing or understated: your answer does not explain what tangible result occurred.")
            suggestions.append("Add a concrete result, measurable metric (e.g., delivered on time, 95% user satisfaction, zero regressions), or clear team consensus.")
        if spec_score < 7.0:
            needs_improvement.append("Lacks specific methodologies, tools, or concrete artifacts.")
            suggestions.append("Name the exact tools (e.g., Figma, Jira, user tests) or specific meeting formats you utilized.")
        if struct_score < 7.0:
            needs_improvement.append("Structure feels somewhat rushed. Organize more explicitly around the STAR framework.")
            suggestions.append("Explicitly state: 1. Situation, 2. Your specific Task, 3. Actions taken, 4. Final Result.")

        if not needs_improvement:
            needs_improvement.append("Strong response! To elevate further, briefly mention what long-term takeaway or process change you instituted.")
            suggestions.append("Reflect on what you would do even better next time.")

        # Status labels
        def get_status(s):
            if s >= 8.0:
                return "Good"
            elif s >= 6.0:
                return "Adequate"
            return "Needs Improvement"

        why_summary = {
            "evaluation_criterion": "Provides concrete outcome / evidence (UR5, Rubric Section 10)",
            "evidence_score": evid_score,
            "evidence_reason": (
                "Your response describes the action you took, but does not provide a concrete outcome."
                if evid_score <= 5.5 else
                "Your response incorporates positive resolution and measurable details."
            ),
            "citations_found": evid_evidence if evid_evidence else ["Action described, but resolution omitted."],
            "recommended_addition": "A single sentence quantifying impact (e.g., 'As a result, we finished the sprint 2 days early with 100% test coverage')."
        }

        return EvaluationResult(
            overall_score=overall,
            relevance=RubricCriterion(
                name="Relevance",
                score=rel_score,
                status=get_status(rel_score),
                reason="Addresses the conflict resolution theme effectively and stays focused on professional context." if rel_score >= 7 else "Partially aligns with prompt, but deviates into generalities.",
                evidence_found="; ".join(relevance_evidence) if relevance_evidence else "Referenced situational elements.",
                missing_aspect=None if rel_score >= 7.5 else "More direct alignment with role responsibilities.",
                rubric_definition="Addresses the specific prompt directly, stays on topic, and reflects target role competencies."
            ),
            specificity=RubricCriterion(
                name="Specificity",
                score=spec_score,
                status=get_status(spec_score),
                reason="Includes technical and contextual references." if spec_score >= 7 else "Uses broad, generic descriptions rather than specific tools or steps.",
                evidence_found="; ".join(spec_evidence) if spec_evidence else "General terminology used.",
                missing_aspect="Specific artifacts, tools, or metrics." if spec_score < 7.5 else None,
                rubric_definition="Mentions concrete details, names, tools, technologies, and specific methodologies rather than broad generalities."
            ),
            evidence_outcome=RubricCriterion(
                name="Evidence & Outcome",
                score=evid_score,
                status=get_status(evid_score),
                reason="Clearly documents outcomes and resolution impact." if evid_score >= 7.5 else "The response describes the action taken, but does not state a concrete outcome.",
                evidence_found="; ".join(evid_evidence) if evid_evidence else "None detected.",
                missing_aspect=evid_missing,
                rubric_definition="Provides concrete results, quantifiable metrics, positive impact, and tangible deliverables (the 'R' in STAR)."
            ),
            structure_clarity=RubricCriterion(
                name="Structure & Clarity",
                score=struct_score,
                status=get_status(struct_score),
                reason="Clear chronological arc from problem to resolution." if struct_score >= 7.5 else "Narrative flow is slightly jumpy or incomplete.",
                evidence_found="; ".join(struct_evidence) if struct_evidence else "Basic chronological order.",
                missing_aspect="Clear transition to the outcome phase." if struct_score < 7.5 else None,
                rubric_definition="Follows an organized narrative arc (e.g. STAR framework) with coherent progression."
            ),
            strengths=strengths,
            needs_improvement=needs_improvement,
            actionable_suggestions=suggestions,
            example_improved_answer=self._generate_example_answer(question_text, job_role),
            why_feedback_summary=why_summary
        )

    def _generate_example_answer(self, question_text: str, job_role: str) -> str:
        if "difficult teammate" in question_text.lower() or "conflict" in question_text.lower():
            return (
                "“During our cross-functional sprint for the user dashboard, a lead engineer and I disagreed on "
                "whether to include an extensive filtering menu or streamline it based on our usability tests. "
                "(Situation/Task) Rather than escalating, I scheduled a 30-minute working session where I walked through "
                "recorded test clips showing that 4 out of 5 users were confused by excessive filters. I proposed an A/B test "
                "compromise with collapsible advanced filters. (Action) As a measurable result, our engineering partner supported "
                "the compromise, we shipped the feature 2 days ahead of deadline, and subsequent product analytics revealed a "
                "28% higher task completion rate with zero user drop-offs.” (Result/Evidence)"
            )
        elif "incomplete information" in question_text.lower() or "decision" in question_text.lower():
            return (
                "“When our quarterly roadmap was due, analytics tracking on our newest onboarding funnel was delayed by a week. "
                "I needed to decide whether to invest in social sign-in or two-factor security first. (Situation) "
                "I triangulated qualitative support tickets, interviewed 6 recent active users, and reviewed historical drop-off patterns. "
                "(Action) I made the call to prioritize social sign-in while implementing basic 2FA in the subsequent sprint. (Action) "
                "Post-launch metrics validated the decision: onboarding completion surged by 19% within two weeks, with zero reported security escalations.” (Outcome)"
            )
        else:
            return (
                "“In my previous project, we faced an unexpected timeline crunch. I prioritized the core MVP requirements, "
                "communicated proactively with our stakeholders through daily standups, and reallocated sprint backlog items. "
                "As a concrete result, we delivered the high-priority release on schedule, improved client satisfaction scores from 3.8 to 4.7/5, "
                "and prevented any engineering burnout.”"
            )

    def compare_attempts(
        self,
        question_id: int,
        question_text: str,
        attempt1_answer: str,
        attempt2_answer: str,
        eval1: EvaluationResult,
        eval2: EvaluationResult
    ) -> AttemptComparison:
        deltas = {
            "relevance": round(eval2.relevance.score - eval1.relevance.score, 1),
            "specificity": round(eval2.specificity.score - eval1.specificity.score, 1),
            "evidence_outcome": round(eval2.evidence_outcome.score - eval1.evidence_outcome.score, 1),
            "structure_clarity": round(eval2.structure_clarity.score - eval1.structure_clarity.score, 1),
            "overall": round(eval2.overall_score - eval1.overall_score, 1),
        }

        improvements = []
        if deltas["evidence_outcome"] > 0:
            improvements.append(f"✓ Added measurable outcome & concrete evidence ({eval1.evidence_outcome.score} → {eval2.evidence_outcome.score})")
        if deltas["specificity"] > 0:
            improvements.append(f"✓ Integrated more concrete details, tools, and specific examples ({eval1.specificity.score} → {eval2.specificity.score})")
        if deltas["structure_clarity"] > 0:
            improvements.append(f"✓ Improved narrative flow and STAR progression ({eval1.structure_clarity.score} → {eval2.structure_clarity.score})")
        if deltas["overall"] > 0:
            improvements.append(f"✓ Overall score increased from {eval1.overall_score}/10 to {eval2.overall_score}/10 (+{deltas['overall']})")

        if not improvements:
            improvements.append("Revised phrasing and consolidated wording between attempts.")

        remaining = []
        if eval2.evidence_outcome.score < 8.0:
            remaining.append("Continue to sharpen quantifiable business metrics in the conclusion.")
        if eval2.specificity.score < 8.0:
            remaining.append("Consider citing specific industry frameworks or tools.")

        return AttemptComparison(
            question_id=question_id,
            question_text=question_text,
            attempt1_answer=attempt1_answer,
            attempt2_answer=attempt2_answer,
            attempt1_scores={
                "relevance": eval1.relevance.score,
                "specificity": eval1.specificity.score,
                "evidence": eval1.evidence_outcome.score,
                "structure": eval1.structure_clarity.score,
                "overall": eval1.overall_score
            },
            attempt2_scores={
                "relevance": eval2.relevance.score,
                "specificity": eval2.specificity.score,
                "evidence": eval2.evidence_outcome.score,
                "structure": eval2.structure_clarity.score,
                "overall": eval2.overall_score
            },
            deltas=deltas,
            improvements=improvements,
            focus_areas_remaining=remaining
        )

    def generate_adaptive_followup(
        self,
        previous_question: str,
        user_answer: str,
        job_role: str
    ) -> Dict[str, str]:
        cleaned = user_answer.strip()
        sentences = [s.strip() for s in re.split(r'[.!?]+', cleaned) if len(s.strip()) > 5]

        # Analyze answer content for realistic contextual follow-up
        lower_ans = cleaned.lower()
        if "conflict" in lower_ans or "disagreed" in lower_ans or "teammate" in lower_ans:
            if not any(w in lower_ans for w in ["result", "outcome", "percent", "%", "metric", "compromise"]):
                return {
                    "followup_question": "I can certainly understand how challenging that kind of disagreement can be with a teammate. When you sat down to work through that, what was the specific compromise or outcome you landed on, and how did it affect the project timeline?",
                    "reasoning": "Acknowledging conflict resolution effort while probing for the tangible resolution outcome and timeline impact."
                }
            else:
                return {
                    "followup_question": "That sounds like a very productive way to reach consensus. If you were to encounter that same disagreement with an executive stakeholder or external customer rather than a peer, how would you adapt your approach?",
                    "reasoning": "Validating peer resolution while probing situational adaptability across seniority levels."
                }
        elif "decision" in lower_ans or "data" in lower_ans or "incomplete" in lower_ans:
            return {
                "followup_question": "Making a critical call under ambiguity is always tough. When you made that decision with limited data, what primary risk did you identify, and what contingency plan did you prepare in case your hypothesis was wrong?",
                "reasoning": "Acknowledging ambiguity while probing risk management and contingency planning."
            }
        else:
            return {
                "followup_question": f"Thanks for sharing that breakdown. Looking back at that experience in your role as {job_role}, what was the single biggest takeaway that changed how you operate today?",
                "reasoning": "Inviting reflective depth and longitudinal professional growth."
            }

    async def generate_adaptive_followup_gemini(
        self,
        previous_question: str,
        user_answer: str,
        job_role: str,
        api_key: Optional[str] = None
    ) -> Dict[str, str]:
        key = api_key or self.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        if not key:
            res = self.generate_adaptive_followup(previous_question, user_answer, job_role)
            res["source"] = "deterministic_engine"
            return res

        prompt = f"""You are an empathetic yet rigorous professional interviewer conducting an interview for the role: "{job_role}".
The previous interview question asked was:
"{previous_question}"

The candidate just provided this spoken response:
"{user_answer}"

Generate an adaptive follow-up question.
Requirements:
1. Ground the follow-up directly in what the candidate mentioned or omitted (e.g., probe for metrics, trade-offs, interpersonal nuance, or risk management).
2. Keep it conversational, realistic, and punchy (1-2 sentences maximum).
3. Do NOT include markdown styling or bullet points.

Respond ONLY with a JSON object in this exact format:
{{
  "followup_question": "“Your question here...”",
  "reasoning": "Brief explanation of why this follow-up was probed based on the response."
}}
"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{GEMINI_API_URL}?key={key}",
                    json={
                        "contents": [
                            {"parts": [{"text": prompt}]}
                        ],
                        "generationConfig": {
                            "temperature": 0.7,
                            "maxOutputTokens": 300,
                            "responseMimeType": "application/json"
                        }
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text_part = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        parsed = json.loads(text_part)
                        if "followup_question" in parsed:
                            parsed["source"] = "gemini_1.5_flash"
                            return parsed
        except Exception as e:
            logger.warning(f"Gemini API call failed, falling back to local engine: {e}")

        fallback = self.generate_adaptive_followup(previous_question, user_answer, job_role)
        fallback["source"] = "deterministic_engine"
        return fallback

    async def evaluate_answer_gemini(
        self,
        question_text: str,
        answer_text: str,
        job_role: str = "General",
        attempt_number: int = 1,
        api_key: Optional[str] = None
    ) -> EvaluationResult:
        base_eval = self.evaluate_answer(question_text, answer_text, job_role, attempt_number)
        key = api_key or self.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        if not key or len(answer_text.strip().split()) < 15:
            return base_eval

        prompt = f"""You are an expert interview coach evaluating a candidate for the role: "{job_role}".
Question: "{question_text}"
Candidate's Spoken Answer: "{answer_text}"

The candidate was preliminarily evaluated on:
- Relevance: {base_eval.relevance.score}/10
- Specificity: {base_eval.specificity.score}/10
- Evidence & Outcome: {base_eval.evidence_outcome.score}/10
- Structure & Clarity: {base_eval.structure_clarity.score}/10

Please provide:
1. 2 distinct strengths
2. 2 distinct needs for improvement
3. 1 concrete actionable recommendation following the STAR method
4. An improved model response demonstrating how to include measurable outcomes.

Respond ONLY with a JSON object in this format:
{{
  "strengths": ["...", "..."],
  "needs_improvement": ["...", "..."],
  "actionable_suggestions": ["..."],
  "example_improved_answer": "..."
}}
"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{GEMINI_API_URL}?key={key}",
                    json={
                        "contents": [
                            {"parts": [{"text": prompt}]}
                        ],
                        "generationConfig": {
                            "temperature": 0.6,
                            "maxOutputTokens": 600,
                            "responseMimeType": "application/json"
                        }
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text_part = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        parsed = json.loads(text_part)
                        if "strengths" in parsed and parsed["strengths"]:
                            base_eval.strengths = parsed["strengths"]
                        if "needs_improvement" in parsed and parsed["needs_improvement"]:
                            base_eval.needs_improvement = parsed["needs_improvement"]
                        if "actionable_suggestions" in parsed and parsed["actionable_suggestions"]:
                            base_eval.actionable_suggestions = parsed["actionable_suggestions"]
                        if "example_improved_answer" in parsed and parsed["example_improved_answer"]:
                            base_eval.example_improved_answer = parsed["example_improved_answer"]
        except Exception as e:
            logger.warning(f"Gemini API call for evaluation failed, retaining deterministic feedback: {e}")

        return base_eval

    # =========================================================================
    # OPENROUTER INTEGRATION: NVIDIA Nemotron 3.5 Super VL (Free)
    # =========================================================================

    async def call_openrouter(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.5,
        max_tokens: int = 3000
    ) -> Optional[str]:
        """
        Executes a chat completion call to OpenRouter targeting nvidia/nemotron-3.5-super-vl:free.
        Zero cost free tier reasoning model.
        """
        api_key = self.get_openrouter_api_key()
        if not api_key:
            return None

        model_name = (self.openrouter_model or OPENROUTER_MODEL).strip()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "http://127.0.0.1:8000",
            "Referer": "http://127.0.0.1:8000",
            "X-Title": "CS 435 AI Interview Practice",
            "Content-Type": "application/json"
        }
        # Nemotron 3.5 requires sufficient token budget for reasoning + output
        token_budget = max(max_tokens, 2800)
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": token_budget
        }

        try:
            # 60 second timeout with 15s connect for reasoning model completion
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=15.0)) as client:
                resp = await client.post(OPENROUTER_API_URL, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        msg = choices[0].get("message", {})
                        content = msg.get("content")
                        if content and content.strip():
                            return content.strip()
                        # Fallback if reasoning model placed answer in reasoning
                        reasoning = msg.get("reasoning", "")
                        if reasoning and ("[" in reasoning or "{" in reasoning):
                            return reasoning.strip()
                else:
                    logger.warning(f"OpenRouter HTTP {resp.status_code}: {resp.text[:300]}")
        except Exception as e:
            logger.warning(f"OpenRouter API call exception: {e}")

        return None

    def _clean_json_output(self, text: str) -> Any:
        """Helper to safely parse JSON from LLM responses even if wrapped in markdown blocks or containing comments/trailing commas."""
        t = text.strip()
        if t.startswith("```"):
            t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
            t = re.sub(r"\s*```$", "", t)
        t = t.strip()

        try:
            return json.loads(t)
        except Exception:
            pass

        # Match bracketed json array or object
        match = re.search(r'(\[[\s\S]*\]|\{[\s\S]*\})', t)
        if match:
            candidate = match.group(1).strip()
            try:
                return json.loads(candidate)
            except Exception:
                # Remove trailing commas like ", }" or ", ]"
                cleaned = re.sub(r',\s*([}\]])', r'\1', candidate)
                try:
                    return json.loads(cleaned)
                except Exception:
                    pass

        # Robust regex-based question array recovery
        regex_items = []
        for block in re.finditer(r'\{[^{}]*"(?:text|question)"[^{}]*\}', t):
            b_str = block.group(0)
            try:
                b_clean = re.sub(r',\s*\}', '}', b_str)
                regex_items.append(json.loads(b_clean))
            except Exception:
                q_match = re.search(r'"(?:text|question)"\s*:\s*"([^"]+)"', b_str)
                if q_match:
                    comp_match = re.search(r'"competency"\s*:\s*"([^"]+)"', b_str)
                    cat_match = re.search(r'"category"\s*:\s*"([^"]+)"', b_str)
                    regex_items.append({
                        "id": len(regex_items) + 1,
                        "text": q_match.group(1),
                        "competency": comp_match.group(1) if comp_match else "Role Competency",
                        "category": cat_match.group(1) if cat_match else "Behavioral"
                    })
        if regex_items:
            return regex_items

        raise ValueError(f"Could not parse valid JSON from text: {t[:200]}")

    async def generate_custom_interview_questions(
        self,
        candidate_name: str,
        job_role: str,
        target_company: str = "",
        experience_level: str = "Mid-Level",
        interview_type: str = "Behavioral",
        difficulty: str = "Medium",
        cv_text: str = "",
        job_description: str = "",
        count: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Generates high-fidelity tailored interview questions using OpenRouter (NVIDIA Nemotron 3.5 Super VL).
        Falls back seamlessly to curated sample questions when offline or key is absent.
        """
        api_key = self.get_openrouter_api_key()
        fallback_questions = get_question_bank_for_role(job_role)

        if not api_key:
            logger.info("OpenRouter API key not configured; using curated fallback question bank.")
            return fallback_questions

        company_context = f" Target Company: '{target_company}'." if target_company else " Industry Tier 1 Firm."
        cv_context = f"\nCandidate Resume/CV Highlights:\n{cv_text.strip()[:1000]}" if cv_text and cv_text.strip() else "\nCandidate Background: Mid to senior engineering/product practitioner."
        jd_context = f"\nTarget Job Description / Requirements:\n{job_description.strip()[:1000]}" if job_description and job_description.strip() else ""

        system_prompt = (
            "You are an elite corporate technical and behavioral interviewer for top global tech and product firms. "
            "Your goal is to generate personalized, rigorous, realistic interview questions for a candidate based directly on their profile. "
            "Always output strictly valid JSON with no unescaped double quotes inside strings."
        )

        user_prompt = f"""Generate {count} distinct interview questions tailored directly to this candidate:
Candidate Name: {candidate_name}
Target Role: {job_role}{company_context}
Experience Level: {experience_level}
Interview Focus / Type: {interview_type}
Difficulty / Tone: {difficulty}{cv_context}{jd_context}

Requirements:
1. Deeply anchor each question in the candidate's actual resume experience, role expertise, target company domain, and seniority level.
2. Provide a realistic mix of behavioral (STAR-method), technical execution, and architectural trade-off questions.
3. Do NOT use unescaped double quotes inside strings. Use single quotes for any internal terms or code identifiers.
4. For each question, supply the competency tested, ideal structure, and key lookouts for evaluation.

Respond ONLY with a valid JSON array of {count} question objects in this exact format, with no preamble:
[
  {{
    "id": 1,
    "text": "The verbatim interview question to ask the candidate...",
    "category": "{interview_type}",
    "difficulty": "{difficulty}",
    "competency": "Key competency being tested",
    "ideal_structure": "Situation, Task, Action, Result with quantifiable impact",
    "key_lookouts": ["Lookout 1", "Lookout 2", "Lookout 3"]
  }}
]
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            content = await self.call_openrouter(messages, temperature=0.4, max_tokens=3000)
            if content:
                parsed = self._clean_json_output(content)
                # If wrapped in a dict like {"questions": [...]} or {"data": [...]}
                if isinstance(parsed, dict):
                    for key in ["questions", "interview_questions", "question_list", "items", "data"]:
                        if key in parsed and isinstance(parsed[key], list):
                            parsed = parsed[key]
                            break

                if isinstance(parsed, list) and len(parsed) > 0:
                    sanitized = []
                    for i, q in enumerate(parsed[:count], start=1):
                        if isinstance(q, str):
                            sanitized.append({
                                "id": i,
                                "text": q.strip(),
                                "category": interview_type,
                                "difficulty": difficulty,
                                "competency": "Core Competency",
                                "ideal_structure": "STAR Method (Situation, Task, Action, Result)",
                                "key_lookouts": ["Specific actions taken", "Measurable outcome"],
                                "source": "openrouter_nemotron"
                            })
                        elif isinstance(q, dict):
                            sanitized.append({
                                "id": i,
                                "text": q.get("text") or q.get("question") or f"Tell me about your experience as a {job_role}.",
                                "category": q.get("category", interview_type),
                                "difficulty": q.get("difficulty", difficulty),
                                "competency": q.get("competency", "Core Competencies"),
                                "ideal_structure": q.get("ideal_structure", "STAR Method (Situation, Task, Action, Result)"),
                                "key_lookouts": q.get("key_lookouts", ["Specific actions", "Measurable outcomes"]),
                                "source": "openrouter_nemotron"
                            })
                    if sanitized:
                        logger.info(f"Generated {len(sanitized)} custom questions via OpenRouter ({self.openrouter_model}).")
                        return sanitized
        except Exception as e:
            logger.warning(f"Failed to generate custom questions via OpenRouter: {e}")

        logger.info("Retaining curated question bank fallback.")
        return fallback_questions

    async def generate_adaptive_followup_ai(
        self,
        previous_question: str,
        user_answer: str,
        job_role: str,
        candidate_name: str = "Candidate",
        target_company: str = "",
        experience_level: str = "",
        cv_text: str = "",
        job_description: str = ""
    ) -> Dict[str, str]:
        """
        Generates an adaptive follow-up probing question.
        Priority:
        1. OpenRouter (NVIDIA Nemotron 3.5 Super VL)
        2. Gemini 1.5 Flash (if key present)
        3. Deterministic local follow-up engine
        """
        api_key = self.get_openrouter_api_key()
        if api_key:
            cand_profile_str = f"Candidate: {candidate_name}, Target Role: {job_role}"
            if target_company:
                cand_profile_str += f", Target Company: {target_company}"
            if experience_level:
                cand_profile_str += f", Seniority: {experience_level}"
            if cv_text:
                cand_profile_str += f"\nCandidate Resume Highlights: {cv_text.strip()[:400]}"
            if job_description:
                cand_profile_str += f"\nTarget Job Context: {job_description.strip()[:300]}"

            company_ref = f" at {target_company}" if target_company else ""
            system_prompt = (
                f"You are Dr. Marcus Vance, a warm, seasoned, and highly perceptive senior hiring evaluator{company_ref} "
                f"interviewing {candidate_name} for the position of '{job_role}'. "
                "You conduct an authentic, natural human conversation. You actively listen to the candidate's exact words, "
                "acknowledge their points like a real human leader, and naturally probe their decision-making. "
                "You NEVER sound like an AI, a generic rubric checklist, or a cold mechanical exam interrogation."
            )
            user_prompt = f"""Candidate Profile:
{cand_profile_str}

The interview question you previously asked {candidate_name} was:
"{previous_question}"

{candidate_name} just answered you with this spoken response:
"{user_answer}"

Generate your natural, in-the-moment spoken conversational follow-up response.
Strict guidelines for an authentic, human conversation:
1. Open with a brief, warm, authentic conversational acknowledgment referencing a specific detail or dilemma they actually stated (e.g. 'That is a classic dilemma between velocity and stability, {candidate_name}.', 'Makes total sense why that would be a contentious issue with the engineering lead.').
2. Seamlessly transition into an insightful, natural follow-up question probing how they reached alignment, what benchmarks or prototypes they leveraged, or the actual measured outcome.
3. Keep the total response spoken, conversational, and punchy (1 to 2 spoken sentences total).
4. Do NOT use unescaped double quotes inside strings. Use single quotes for any internal terms.

Respond ONLY with a JSON object in this exact format:
{{
  "followup_question": "Your spoken conversational acknowledgment and follow-up question here...",
  "reasoning": "1-sentence note explaining why you probed this angle."
}}
"""
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            try:
                content = await self.call_openrouter(messages, temperature=0.6, max_tokens=2000)
                if content:
                    parsed = self._clean_json_output(content)
                    if isinstance(parsed, dict):
                        fq = parsed.get("followup_question") or parsed.get("question") or parsed.get("followup")
                        reason = parsed.get("reasoning") or parsed.get("reason") or "Probing situational depth."
                        if fq:
                            return {
                                "followup_question": str(fq).strip(),
                                "reasoning": str(reason).strip(),
                                "source": "openrouter_nemotron"
                            }
                    elif isinstance(parsed, str) and len(parsed.strip()) > 10:
                        return {
                            "followup_question": parsed.strip(),
                            "reasoning": "Contextual probing on candidate response.",
                            "source": "openrouter_nemotron"
                        }
            except Exception as e:
                logger.warning(f"OpenRouter follow-up failed, falling back: {e}")

        # Fallback to Gemini if configured
        gemini_key = self.get_gemini_api_key()
        if gemini_key:
            return await self.generate_adaptive_followup_gemini(previous_question, user_answer, job_role, api_key=gemini_key)

        # Fallback to deterministic
        res = self.generate_adaptive_followup(previous_question, user_answer, job_role)
        res["source"] = "deterministic_engine"
        return res

    def build_official_interview_system_prompt(
        self,
        candidate_name: str,
        job_role: str,
        target_company: str = "",
        experience_level: str = "",
        cv_text: str = "",
        job_description: str = "",
        interview_type: str = "Behavioral & Technical"
    ) -> str:
        company_phrase = f" at {target_company}" if target_company else ""
        return f"""You are Dr. Marcus Vance, a distinguished, seasoned, and deeply observant senior hiring evaluator conducting an official, high-stakes corporate interview{company_phrase} for the position of '{job_role}'.

==================================================
NON-NEGOTIABLE CANDIDATE SPECIFICATION (GROUND TRUTH)
==================================================
- Candidate Name: {candidate_name}
- Target Job Role: {job_role}
- Target Company / Organization: {target_company or 'Leading Industry Firm'}
- Experience / Seniority Level: {experience_level or 'Mid-Level'}
- Interview Focus: {interview_type}
- Candidate Resume & Experience Highlights:
{cv_text.strip() or 'Strong background in industry-standard competencies for ' + job_role + '.'}
- Target Job Description & Expectations:
{job_description.strip() or 'Core competencies, technical execution, leadership, problem-solving, and cross-functional communication.'}

==================================================
NON-NEGOTIABLE OFFICIAL INTERVIEW PROTOCOL
==================================================
1. MIMIC AN AUTHENTIC OFFICIAL INTERVIEW:
   - You are conducting a real live corporate oral interview, not an automated exam or robotic questionnaire.
   - Speak with executive presence, warmth, professional rigor, and active curiosity.
   - Address the candidate naturally by their first name ({candidate_name}).

2. ASK QUESTIONS STRICTLY ONE BY ONE:
   - Ask exactly ONE clear, focused question at a time.
   - NEVER ask multi-part compound questions, numbered lists, or bullet points.
   - Wait for the candidate's spoken response before proceeding to the next stage.

3. CONVERSATIONAL PROGRESSION & STAGES:
   - STAGE 1 (Opening & Self-Introduction):
     Welcome the candidate warmly ("Good morning / Hello {candidate_name}! Welcome to your interview..."). Briefly introduce yourself as Dr. Marcus Vance, lead hiring evaluator for the {job_role} role{company_phrase}. Invite the candidate to introduce themselves and walk through their background.
   - STAGE 2 (Project & Technical Execution):
     When the candidate introduces themselves, actively acknowledge specific details, domains, or technologies they highlighted. Transition smoothly into asking ONE targeted question about a major technical project, design decision, or core achievement from their background.
   - STAGE 3 (Behavioral, Conflict & Trade-Offs):
     Acknowledge their project explanation like a real engineering or product leader. Transition to a behavioral dilemma—such as resolving a sharp disagreement with a team member, navigating tight deadlines, or prioritizing technical debt vs product velocity.
   - STAGE 4 (Outcome Verification & Measured Impact):
     Acknowledge their resolution. Probe how they verified the outcome, what quantitative metrics or user feedback moved, and what lessons they took away.
   - STAGE 5 (Interview Conclusion):
     Acknowledge their complete journey warmly and officially conclude the interview.

4. ACTIVE LISTENING & HUMAN CONVERSATION:
   - Every single response from you MUST begin with a genuine, human conversational reaction to the candidate's latest user prompt (e.g., "Good morning, {candidate_name}...", "That's a very compelling trajectory, especially handling...", "Makes total sense why that sparked a debate with your tech lead...", "I appreciate the transparency about those latency hurdles...").
   - Never sound like an AI assistant or a rubric checklist.
   - Keep each spoken response between 1 to 3 natural, conversational sentences.
   - Do NOT emit Markdown headers, asterisks, bullet points, JSON keys, or meta tags in your spoken dialogue so that browser text-to-speech sounds completely natural.

==================================================
MANDATORY HISTORY BUFFER & ACTIVE LISTENING PROTOCOL
==================================================
You are provided with the complete chronological conversation history buffer above.
Every time you respond:
1. EXPLICIT ACTIVE LISTENING: You MUST actively listen and acknowledge specific concepts, technical keywords, frameworks, company names, tools, or metrics that the candidate directly stated in their latest response (e.g., if they mention PyTorch, medical imaging, CUDA, Kafka, gRPC, user churn, or checkout funnels, you must explicitly weave that into your acknowledgment).
2. LOGICAL PROBE CONTINUITY: Your question MUST directly investigate the specific decisions, trade-offs, deadlocks, or outcomes of what they just spoke about. Never ask detached, pre-canned, or generic questions that ignore what the candidate just told you.
3. CONVERSATIONAL PROGRESSION: Follow the interview stages naturally based on the continuous dialogue history.
"""

    async def conduct_official_interview_turn(
        self,
        conversation_history: List[Dict[str, str]],
        user_message: str,
        candidate_name: str = "Candidate",
        job_role: str = "Software Engineer",
        target_company: str = "",
        experience_level: str = "",
        cv_text: str = "",
        job_description: str = "",
        turn_index: int = 1
    ) -> Dict[str, Any]:
        """
        Executes a natural, official one-by-one multi-turn interview turn.
        System prompt contains non-negotiable candidate ground truth, continuous history buffer, and active listening rules.
        """
        api_key = self.get_openrouter_api_key()
        if api_key:
            system_prompt = self.build_official_interview_system_prompt(
                candidate_name=candidate_name,
                job_role=job_role,
                target_company=target_company,
                experience_level=experience_level,
                cv_text=cv_text,
                job_description=job_description
            )
            messages = [{"role": "system", "content": system_prompt}]

            # Add existing conversation turns from the history buffer
            for msg in conversation_history:
                r = msg.get("role", "user")
                c = msg.get("content", "").strip()
                if c:
                    messages.append({"role": r, "content": c})

            # Append latest user prompt only if not already at the end of the history buffer
            clean_user_msg = user_message.strip()
            if not messages or messages[-1].get("content") != clean_user_msg:
                messages.append({"role": "user", "content": clean_user_msg})

            try:
                content = await self.call_openrouter(messages, temperature=0.65, max_tokens=1500)
                if content and len(content.strip()) > 15:
                    clean_reply = content.strip().strip('"').strip("'")
                    if clean_reply.startswith("{") and "}" in clean_reply:
                        parsed = self._clean_json_output(clean_reply)
                        if isinstance(parsed, dict):
                            clean_reply = parsed.get("followup_question") or parsed.get("interviewer_message") or clean_reply
                    return {
                        "interviewer_message": str(clean_reply).strip(),
                        "followup_question": str(clean_reply).strip(),
                        "reasoning": f"Stage {turn_index + 1} official interview probe based on candidate response.",
                        "turn_index": turn_index + 1,
                        "is_concluded": (turn_index >= 4 or "conclude" in clean_reply.lower() or "evaluation" in clean_reply.lower()),
                        "source": "openrouter_nemotron"
                    }
            except Exception as e:
                logger.warning(f"OpenRouter official turn failed, using fallback: {e}")

        # Intelligent context-aware deterministic fallback (extracts key topics spoken by user)
        company_ref = f" at {target_company}" if target_company else ""
        extracted_topics = []
        lowered_user = user_message.lower()
        for word in ["pytorch", "cuda", "mri", "imaging", "grpc", "rest", "raft", "postgres", "sql", "kafka", "docker", "kubernetes", "latency", "funnel", "usability", "research", "pipeline", "model", "cloud", "aws", "security"]:
            if word in lowered_user:
                extracted_topics.append(word)
        topic_phrase = f" on {', '.join(extracted_topics[:2])}" if extracted_topics else ""

        if turn_index == 1:
            reply = (
                f"Good morning, {candidate_name}, and it's a pleasure to meet you. "
                f"That's a very compelling background leading up to this {job_role} role{company_ref}. "
                f"Diving into your direct experience{topic_phrase}: could you walk me through the most technically demanding project or system architecture you've spearheaded recently, and the core engineering challenge you had to solve?"
            )
        elif turn_index == 2:
            reply = (
                f"I appreciate that breakdown{topic_phrase}, {candidate_name}. "
                "Working through complex technical architectures naturally surfaces trade-offs and team friction. "
                f"Tell me about a specific time during that project where you had a significant disagreement with a teammate or engineering manager over technical priorities or trade-offs. What was the conflict, and how did you resolve it?"
            )
        elif turn_index == 3:
            reply = (
                f"Navigating technical deadlocks with structured evidence is essential in high-impact teams, {candidate_name}. "
                f"Looking back on that solution{topic_phrase}, how did you verify the measurable outcome and business impact, and what is one lesson you took away?"
            )
        else:
            reply = (
                f"Those are great insights and quantified results{topic_phrase}, {candidate_name}. "
                "Thank you for walking through your experience with me today—it gave me a great window into how you lead and solve complex challenges. "
                "That brings our interview questions to a close, and I'll now finalize your comprehensive rubric scorecard."
            )

        return {
            "interviewer_message": reply,
            "followup_question": reply,
            "reasoning": f"Stage {turn_index + 1} official staged interview probe.",
            "turn_index": turn_index + 1,
            "is_concluded": turn_index >= 4,
            "source": "deterministic_official_protocol"
        }

    async def evaluate_answer_ai(
        self,
        question_text: str,
        answer_text: str,
        job_role: str = "General",
        attempt_number: int = 1,
        candidate_name: str = "Candidate",
        target_company: str = "",
        experience_level: str = "",
        cv_text: str = "",
        job_description: str = ""
    ) -> EvaluationResult:
        """
        Evaluates a candidate's answer against the STAR rubric.
        Priority:
        1. OpenRouter (NVIDIA Nemotron 3.5 Super VL)
        2. Gemini 1.5 Flash
        3. Deterministic STAR Rubric Evaluator
        """
        base_eval = self.evaluate_answer(question_text, answer_text, job_role, attempt_number)
        if len(answer_text.strip().split()) < 15:
            return base_eval

        api_key = self.get_openrouter_api_key()
        if api_key:
            cand_profile_str = f"Candidate: {candidate_name}, Role: {job_role}"
            if target_company:
                cand_profile_str += f", Target Company: {target_company}"
            if experience_level:
                cand_profile_str += f", Level: {experience_level}"
            if cv_text:
                cand_profile_str += f"\nResume context: {cv_text[:300]}"

            system_prompt = (
                f"You are a master interview coach and evaluator reviewing answers for the role: '{job_role}'. "
                f"Tailor feedback to the candidate's target company and seniority expectations."
            )
            user_prompt = f"""Candidate Profile:
{cand_profile_str}

Question asked:
"{question_text}"

Candidate's spoken answer:
"{answer_text}"

Baseline automated rubric scores:
- Relevance: {base_eval.relevance.score}/10
- Specificity: {base_eval.specificity.score}/10
- Evidence & Outcome: {base_eval.evidence_outcome.score}/10
- Structure & Clarity: {base_eval.structure_clarity.score}/10

Please provide expert, constructive evaluation in JSON format:
1. 2 distinct strengths
2. 2 distinct areas for improvement
3. 1 concrete actionable recommendation following the STAR method
4. An improved model response demonstrating how to include measurable outcomes and concrete details tailored to this profile.

Respond ONLY with a JSON object in this format:
{{
  "strengths": ["...", "..."],
  "needs_improvement": ["...", "..."],
  "actionable_suggestions": ["..."],
  "example_improved_answer": "..."
}}
"""
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            try:
                content = await self.call_openrouter(messages, temperature=0.5, max_tokens=2500)
                if content:
                    parsed = self._clean_json_output(content)
                    if isinstance(parsed, dict):
                        strengths = parsed.get("strengths") or []
                        if isinstance(strengths, list) and strengths:
                            base_eval.strengths = [str(s) for s in strengths]

                        needs_imp = parsed.get("needs_improvement") or parsed.get("areas_for_improvement") or []
                        if isinstance(needs_imp, list) and needs_imp:
                            base_eval.needs_improvement = [str(n) for n in needs_imp]

                        actionable = parsed.get("actionable_suggestions") or parsed.get("recommendations") or []
                        if isinstance(actionable, list) and actionable:
                            base_eval.actionable_suggestions = [str(a) for a in actionable]

                        improved = parsed.get("example_improved_answer") or parsed.get("improved_answer") or parsed.get("sample_answer")
                        if improved:
                            base_eval.example_improved_answer = str(improved)

                        base_eval.why_feedback_summary["evaluator_engine"] = "openrouter_nemotron"
                        return base_eval
            except Exception as e:
                logger.warning(f"OpenRouter answer evaluation failed, falling back: {e}")

        # Fallback to Gemini if configured
        gemini_key = self.get_gemini_api_key()
        if gemini_key:
            return await self.evaluate_answer_gemini(question_text, answer_text, job_role, attempt_number, api_key=gemini_key)

        return base_eval


evaluator = InterviewEvaluator()
