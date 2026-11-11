import unittest
import asyncio
from app.evaluator import InterviewEvaluator, OPENROUTER_MODEL
from app.data_manager import get_question_bank_for_role
from starlette.testclient import TestClient
from main import app


class TestOpenRouterIntegration(unittest.TestCase):
    def setUp(self):
        self.evaluator = InterviewEvaluator()
        self.client = TestClient(app)

    def test_default_model_is_nemotron_free(self):
        self.assertEqual(OPENROUTER_MODEL, "nvidia/nemotron-3.5-super-vl:free")
        self.assertEqual(self.evaluator.openrouter_model, "nvidia/nemotron-3.5-super-vl:free")

    def test_fallback_custom_questions_when_key_empty(self):
        # Empty API key should seamlessly return the curated sample question bank
        self.evaluator.get_openrouter_api_key = lambda: ""
        questions = asyncio.run(self.evaluator.generate_custom_interview_questions(
            candidate_name="Test Candidate",
            job_role="Software Engineer",
            target_company="Google",
            count=3
        ))
        self.assertIsInstance(questions, list)
        self.assertGreaterEqual(len(questions), 3)
        self.assertEqual(questions[0]["id"], 1)
        self.assertIn("text", questions[0])
        self.assertIn("competency", questions[0])

    def test_fallback_adaptive_followup_when_key_empty(self):
        self.evaluator.get_openrouter_api_key = lambda: ""
        self.evaluator.get_gemini_api_key = lambda: ""
        res = asyncio.run(self.evaluator.generate_adaptive_followup_ai(
            previous_question="Tell me about a time you had a conflict with an engineering teammate.",
            user_answer="I discussed the issue with them and we came to an agreement.",
            job_role="Associate Product Manager",
            candidate_name="Rahul"
        ))
        self.assertIn("followup_question", res)
        self.assertIn("reasoning", res)
        self.assertIn(res.get("source"), ["deterministic_engine", "gemini_1.5_flash"])

    def test_fallback_evaluate_answer_when_key_empty(self):
        self.evaluator.get_openrouter_api_key = lambda: ""
        self.evaluator.get_gemini_api_key = lambda: ""
        eval_res = asyncio.run(self.evaluator.evaluate_answer_ai(
            question_text="Tell me about a time you resolved a disagreement.",
            answer_text="At my previous job, I organized a sprint review with the lead engineer to align on product priorities.",
            job_role="Product Manager",
            attempt_number=1
        ))
        self.assertIsNotNone(eval_res)
        self.assertGreater(eval_res.overall_score, 0)
        self.assertIsNotNone(eval_res.relevance)
        self.assertIsNotNone(eval_res.specificity)

    def test_api_config_openrouter_endpoints(self):
        # Test GET /api/config
        get_res = self.client.get("/api/config")
        self.assertEqual(get_res.status_code, 200)
        data = get_res.json()
        self.assertIn("openrouter_active", data)
        self.assertIn("openrouter_model", data)
        self.assertEqual(data["openrouter_model"], "nvidia/nemotron-3.5-super-vl:free")

        # Test in-memory config without mutating real .env file
        from app.models import ConfigUpdateRequest
        req = ConfigUpdateRequest(openrouter_model="nvidia/nemotron-3.5-super-vl:free")
        self.assertEqual(req.openrouter_model, "nvidia/nemotron-3.5-super-vl:free")

    def test_dotenv_file_exists_and_loads(self):
        from app.env_loader import DOTENV_PATH, load_dotenv_file
        self.assertTrue(DOTENV_PATH.exists())
        content = DOTENV_PATH.read_text(encoding="utf-8")
        self.assertIn("OPENROUTER_API_KEY", content)
        self.assertIn("OPENROUTER_MODEL", content)
        self.assertIn("nvidia/nemotron-3.5-super-vl:free", content)


if __name__ == "__main__":
    unittest.main()
