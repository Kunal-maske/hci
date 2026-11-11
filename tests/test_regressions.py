import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import app.database as database
import main
from app.evaluator import evaluator


class TestHighPriorityRegressions(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test.db")
        self.db_path_patch = patch("app.database.DB_PATH", self.db_path)
        self.db_path_patch.start()
        database.init_db()
        self.client = TestClient(main.app)

    def tearDown(self):
        self.db_path_patch.stop()
        self.temp_dir.cleanup()

    def _evaluation(self, answer, attempt_number):
        return evaluator.evaluate_answer(
            "Tell me about a time you resolved a team conflict.",
            answer,
            "Software Engineer",
            attempt_number,
        )

    def test_progress_only_includes_the_requested_persona(self):
        database.save_session({
            "id": "rahul-session",
            "prototype_type": "A",
            "job_role": "Software Engineer",
            "persona_id": "rahul",
        })
        evaluation = self._evaluation(
            "I organized a review, aligned the team, and delivered the release on time.",
            1,
        )
        database.save_attempt(
            "rahul-session",
            1,
            1,
            "Tell me about a team conflict.",
            "I organized a review, aligned the team, and delivered the release on time.",
            evaluation.model_dump(),
        )

        aditi = database.get_longitudinal_progress("aditi")
        rahul = database.get_longitudinal_progress("rahul")

        self.assertEqual(aditi["total_attempts"], 3)
        self.assertEqual(rahul["total_attempts"], 1)

    def test_new_database_does_not_seed_fake_participant_responses(self):
        self.assertEqual(database.get_user_evaluations(), [])

    def test_comparison_uses_the_saved_evaluations(self):
        database.save_session({
            "id": "comparison-session",
            "prototype_type": "A",
            "job_role": "Software Engineer",
            "persona_id": "rahul",
        })
        answers = [
            "I talked with my teammate and we resolved the issue.",
            "I organized a review, showed test results, and reduced the issue rate by 25 percent.",
        ]
        evaluations = [
            self._evaluation(answer, index)
            for index, answer in enumerate(answers, start=1)
        ]
        for index, (answer, evaluation) in enumerate(zip(answers, evaluations), start=1):
            database.save_attempt(
                "comparison-session",
                1,
                index,
                "Tell me about a team conflict.",
                answer,
                evaluation.model_dump(),
            )

        with patch.object(main.evaluator, "evaluate_answer", side_effect=AssertionError):
            response = self.client.post(
                "/api/compare?session_id=comparison-session&question_id=1"
            )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["attempt1_scores"]["overall"], evaluations[0].overall_score)
        self.assertEqual(result["attempt2_scores"]["overall"], evaluations[1].overall_score)

    def test_exports_use_persisted_sessions_and_reject_unknown_ids(self):
        session_id = "persisted-session"
        database.save_session({
            "id": session_id,
            "prototype_type": "A",
            "job_role": "Data Scientist",
            "persona_id": "rahul",
        })
        answer = "I organized the analysis, aligned the team, and improved completion by 20 percent."
        evaluation = self._evaluation(answer, 1)
        database.save_attempt(
            session_id,
            1,
            1,
            "Tell me about a team conflict.",
            answer,
            evaluation.model_dump(),
        )
        database.save_reflection(session_id, 1, "Add context.", "Measure the outcome.")

        with patch.dict(main.active_sessions, {}, clear=True), patch.object(
            main, "EXPORTS_DIR", self.temp_dir.name
        ):
            docx = self.client.get(f"/api/export-docx/{session_id}")
            pptx = self.client.get(f"/api/export-pptx/{session_id}")
            missing_docx = self.client.get("/api/export-docx/unknown-session")
            missing_pptx = self.client.get("/api/export-pptx/unknown-session")

        self.assertEqual(docx.status_code, 200)
        self.assertEqual(pptx.status_code, 200)
        self.assertGreater(len(docx.content), 1000)
        self.assertGreater(len(pptx.content), 1000)
        self.assertEqual(missing_docx.status_code, 404)
        self.assertEqual(missing_pptx.status_code, 404)

    def test_evaluation_submissions_require_consent_and_valid_sus_data(self):
        payload = {
            "participant_id": "P_REGRESSION",
            "target_role": "Software Engineer",
            "prototype_tested": "Both",
            "task_completed": True,
            "task_time_seconds": 30,
            "sus_scores": [5, 1, 5, 1, 5, 1, 5, 1, 5, 1],
            "sus_total_score": 100,
            "feedback_realism": "",
            "feedback_learning": "",
            "ethical_consent_signed": True,
        }

        no_consent = self.client.post(
            "/api/evaluation-study",
            json={**payload, "ethical_consent_signed": False},
        )
        incorrect_score = self.client.post(
            "/api/evaluation-study",
            json={**payload, "sus_total_score": 90},
        )
        missing_answer = self.client.post(
            "/api/evaluation-study",
            json={**payload, "sus_scores": payload["sus_scores"][:-1]},
        )
        valid = self.client.post("/api/evaluation-study", json=payload)

        self.assertEqual(no_consent.status_code, 400)
        self.assertEqual(incorrect_score.status_code, 422)
        self.assertEqual(missing_answer.status_code, 422)
        self.assertEqual(valid.status_code, 200)


if __name__ == "__main__":
    unittest.main()
