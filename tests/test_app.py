"""
Unit and integration tests for the AI Interview Practice System.
Tests rubric evaluation, adaptive follow-ups, database persistence, and report generation.
"""

import os
import unittest
from app.evaluator import evaluator
from app.database import init_db, save_session, save_attempt, get_longitudinal_progress
from app.report_generator import generate_docx_report, generate_pptx_summary


class TestInterviewSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_rubric_evaluation_attempt1(self):
        # Attempt 1: Action without concrete outcome
        ans1 = (
            "In my previous UX research sprint, I had a disagreement with our engineer on the dashboard layout. "
            "The engineer wanted fewer filters to save loading time, while I wanted all filters visible. "
            "I scheduled a 30-minute sync to talk through user needs and we agreed on a compromise."
        )
        res1 = evaluator.evaluate_answer(
            question_text="Tell me about a time when you worked with a difficult teammate.",
            answer_text=ans1,
            job_role="UX Research Intern",
            attempt_number=1
        )
        self.assertIsNotNone(res1)
        self.assertGreaterEqual(res1.overall_score, 4.0)
        # Outcome is missing, so evidence_outcome should reflect that
        self.assertLessEqual(res1.evidence_outcome.score, 6.0)
        self.assertIn("outcome", res1.evidence_outcome.reason.lower())
        self.assertGreaterEqual(len(res1.strengths), 1)

    def test_rubric_evaluation_attempt2(self):
        # Attempt 2: Improved with concrete metrics
        ans2 = (
            "During our cross-functional sprint for the user dashboard, a lead engineer and I disagreed on whether to include "
            "an extensive filter menu or streamline it based on our usability tests. "
            "Rather than escalating, I scheduled a 30-minute working session where I walked through recorded user testing clips showing that "
            "4 out of 5 users were confused by excessive filters. I proposed an A/B test compromise with collapsible filters. "
            "As a concrete result, our engineering partner agreed, we shipped the feature 2 days ahead of deadline, and subsequent product "
            "analytics revealed a 28% higher task completion rate with zero user drop-offs."
        )
        res2 = evaluator.evaluate_answer(
            question_text="Tell me about a time when you worked with a difficult teammate.",
            answer_text=ans2,
            job_role="UX Research Intern",
            attempt_number=2
        )
        self.assertGreaterEqual(res2.overall_score, 7.5)
        self.assertGreaterEqual(res2.evidence_outcome.score, 7.5)
        self.assertGreaterEqual(res2.specificity.score, 7.0)

    def test_attempt_comparison(self):
        ans1 = "I talked to the person and we worked it out."
        ans2 = "I scheduled an alignment sync with data clips. As a result we improved user metrics by 28%."
        res1 = evaluator.evaluate_answer("Tell me about a conflict", ans1, "UX Research Intern", 1)
        res2 = evaluator.evaluate_answer("Tell me about a conflict", ans2, "UX Research Intern", 2)
        comp = evaluator.compare_attempts(1, "Tell me about a conflict", ans1, ans2, res1, res2)
        self.assertGreater(comp.deltas["overall"], 0)
        self.assertGreaterEqual(len(comp.improvements), 1)

    def test_adaptive_followup(self):
        followup = evaluator.generate_adaptive_followup(
            previous_question="Tell me about a conflict",
            user_answer="I discussed the issue with my peer and we compromised.",
            job_role="Associate Product Manager"
        )
        self.assertIn("followup_question", followup)
        self.assertIn("reasoning", followup)

    def test_longitudinal_progress(self):
        prog = get_longitudinal_progress("aditi")
        self.assertIn("trajectory", prog)
        self.assertIn("profile", prog)
        self.assertGreaterEqual(len(prog["trajectory"]), 1)

    def test_report_generation(self):
        out_dir = "test_exports"
        os.makedirs(out_dir, exist_ok=True)
        docx_path = os.path.join(out_dir, "test_report.docx")
        pptx_path = os.path.join(out_dir, "test_summary.pptx")

        session_data = {
            "session_id": "test_123",
            "job_role": "UX Research Intern",
            "prototype_type": "A",
            "overall_score": 8.2,
            "attempts": [{
                "question_text": "Tell me about a conflict",
                "attempt_number": 1,
                "answer_text": "I scheduled a meeting and resolved the issue.",
                "evaluation": {
                    "overall_score": 7.0,
                    "relevance": {"score": 8.0, "reason": "Good"},
                    "specificity": {"score": 7.0, "reason": "Adequate"},
                    "evidence_outcome": {"score": 6.0, "reason": "Needs metric"},
                    "structure_clarity": {"score": 7.0, "reason": "Clear"}
                }
            }],
            "reflections": [{"what_would_you_change": "Add metrics", "what_did_you_learn": "Give evidence"}]
        }

        generate_docx_report(session_data, docx_path)
        generate_pptx_summary(session_data, pptx_path)

        self.assertTrue(os.path.exists(docx_path))
        self.assertTrue(os.path.exists(pptx_path))
        self.assertGreater(os.path.getsize(docx_path), 1000)
        self.assertGreater(os.path.getsize(pptx_path), 1000)


if __name__ == "__main__":
    unittest.main()
