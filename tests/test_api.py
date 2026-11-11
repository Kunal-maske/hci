"""
API Endpoint integration tests.
Tests complete interaction flow through FastAPI TestClient.
"""

import unittest
import os
from unittest.mock import patch
from starlette.testclient import TestClient
from main import app, vosk_model
from app.evaluator import evaluator


class TestAPIEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_home_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("AI Interview Practice System", response.text)

    def test_personas_and_survey(self):
        resp_p = self.client.get("/api/personas")
        self.assertEqual(resp_p.status_code, 200)
        self.assertIn("aditi", resp_p.json())
        self.assertIn("rahul", resp_p.json())

        resp_s = self.client.get("/api/survey-data")
        self.assertEqual(resp_s.status_code, 200)
        self.assertEqual(resp_s.json()["survey"]["total_n"], 30)

    def test_prototype_a_flow(self):
        # 1. Setup
        setup_resp = self.client.post("/api/setup", json={
            "prototype_type": "A",
            "job_role": "UX Research Intern",
            "interview_type": "Behavioral",
            "difficulty": "Medium",
            "cv_text": "HCI student with user testing experience",
            "job_description": "UX Research Intern role",
            "persona_id": "aditi"
        })
        self.assertEqual(setup_resp.status_code, 200)
        sess_data = setup_resp.json()
        session_id = sess_data["session_id"]
        self.assertTrue(session_id.startswith("sess_"))

        # 2. Evaluate Attempt 1 (weak on outcome)
        eval_resp1 = self.client.post("/api/evaluate", json={
            "session_id": session_id,
            "question_id": 1,
            "question_text": "Tell me about a time when you worked with a difficult teammate.",
            "answer_text": "I had a conflict with my peer and we had a meeting and compromised.",
            "attempt_number": 1
        })
        self.assertEqual(eval_resp1.status_code, 200)
        eval1_json = eval_resp1.json()
        self.assertIn("evidence_outcome", eval1_json)

        # 3. Submit Reflection
        ref_resp = self.client.post("/api/reflect", json={
            "session_id": session_id,
            "question_id": 1,
            "what_would_you_change": "I would add the 28% completion metric and delivery timeline.",
            "what_did_you_learn": "Give evidence and outcomes, not just actions."
        })
        self.assertEqual(ref_resp.status_code, 200)

        # 4. Evaluate Attempt 2 (strong on outcome)
        eval_resp2 = self.client.post("/api/evaluate", json={
            "session_id": session_id,
            "question_id": 1,
            "question_text": "Tell me about a time when you worked with a difficult teammate.",
            "answer_text": "During our sprint, I resolved a teammate disagreement by showing recorded user testing clips. As a result, our team shipped 2 days early with a 28% higher task completion rate.",
            "attempt_number": 2
        })
        self.assertEqual(eval_resp2.status_code, 200)
        eval2_json = eval_resp2.json()
        self.assertGreater(eval2_json["overall_score"], eval1_json["overall_score"])

        # 5. Compare Attempts
        comp_resp = self.client.post(f"/api/compare?session_id={session_id}&question_id=1")
        self.assertEqual(comp_resp.status_code, 200)
        comp_json = comp_resp.json()
        self.assertGreater(comp_json["deltas"]["overall"], 0)

        # 6. Check Longitudinal Progress
        prog_resp = self.client.get("/api/progress?persona_id=aditi")
        self.assertEqual(prog_resp.status_code, 200)
        self.assertGreaterEqual(prog_resp.json()["total_attempts"], 2)

        # 7. Test Export DOCX and PPTX
        docx_resp = self.client.get(f"/api/export-docx/{session_id}")
        self.assertEqual(docx_resp.status_code, 200)

        pptx_resp = self.client.get(f"/api/export-pptx/{session_id}")
        self.assertEqual(pptx_resp.status_code, 200)

    def test_prototype_b_followup(self):
        followup_resp = self.client.post("/api/followup", json={
            "session_id": "test_b",
            "question_id": 1,
            "previous_question": "Tell me about a conflict",
            "user_answer": "I talked to the designer and we agreed on a plan.",
            "job_role": "Associate Product Manager"
        })
        self.assertEqual(followup_resp.status_code, 200)
        self.assertIn("followup_question", followup_resp.json())

    def test_prototype_b_official_multi_turn(self):
        # 1. Setup Prototype B session
        setup_resp = self.client.post("/api/setup", json={
            "prototype_type": "B",
            "candidate_name": "Elena Rostova",
            "job_role": "Staff Distributed Systems Engineer",
            "target_company": "Stripe",
            "experience_level": "Senior",
            "cv_text": "Led multi-region consensus protocol redesign and ledger latency optimization",
            "job_description": "Architect high-throughput payment ledgers with sub-50ms latency"
        })
        self.assertEqual(setup_resp.status_code, 200)
        sess_data = setup_resp.json()
        session_id = sess_data["session_id"]
        first_q = sess_data["first_question"]["text"]
        self.assertIn("Elena", first_q)
        self.assertIn("Good morning", first_q)

        # 2. Turn 1 (Self-introduction)
        turn1_resp = self.client.post("/api/interview/turn", json={
            "session_id": session_id,
            "user_message": "Good morning Dr. Vance! I'm Elena, a backend systems engineer specializing in distributed consensus and payment ledgers.",
            "turn_index": 1,
            "job_role": "Staff Distributed Systems Engineer"
        })
        self.assertEqual(turn1_resp.status_code, 200)
        turn1_data = turn1_resp.json()
        self.assertIn("interviewer_message", turn1_data)
        self.assertEqual(turn1_data["turn_index"], 2)

        # 3. Turn 2 (Project Deep Dive Response)
        turn2_resp = self.client.post("/api/interview/turn", json={
            "session_id": session_id,
            "user_message": "We experienced partition stalls on cross-region 2PC. I redesigned our lease manager using Raft quorum leases, cutting commit latency from 450ms to 42ms.",
            "turn_index": 2,
            "job_role": "Staff Distributed Systems Engineer"
        })
        self.assertEqual(turn2_resp.status_code, 200)
        turn2_data = turn2_resp.json()
        self.assertIn("interviewer_message", turn2_data)
        self.assertEqual(turn2_data["turn_index"], 3)

    def test_config_endpoints(self):
        # GET config
        resp = self.client.get("/api/config")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("stt_engine", resp.json())
        self.assertEqual(resp.json()["stt_engine"], "web_speech_api")

        # POST config
        original_key = evaluator.gemini_api_key
        original_env_key = os.environ.get("GEMINI_API_KEY")
        try:
            with patch("main.update_dotenv_key"):
                post_resp = self.client.post("/api/config", json={
                    "gemini_api_key": "test_mock_key_123",
                    "voice_speed": 1.1,
                    "auto_speak": True
                })
                self.assertEqual(post_resp.status_code, 200)
                self.assertTrue(post_resp.json()["gemini_active"])

                clear_resp = self.client.post("/api/config", json={"gemini_api_key": ""})
                self.assertEqual(clear_resp.status_code, 200)
                self.assertFalse(clear_resp.json()["gemini_active"])
        finally:
            evaluator.gemini_api_key = original_key
            if original_env_key is None:
                os.environ.pop("GEMINI_API_KEY", None)
            else:
                os.environ["GEMINI_API_KEY"] = original_env_key

    def test_evaluation_study_endpoints(self):
        # Submit evaluation
        payload = {
            "participant_id": "P_TEST",
            "target_role": "UX Research",
            "prototype_tested": "Both",
            "task_completed": True,
            "task_time_seconds": 180,
            "sus_scores": [5, 1, 5, 1, 5, 1, 5, 1, 5, 1],
            "sus_total_score": 100.0,
            "feedback_realism": "Excellent speech and voice response.",
            "feedback_learning": "Rubric deltas were clear.",
            "ethical_consent_signed": True
        }
        post_resp = self.client.post("/api/evaluation-study", json=payload)
        self.assertEqual(post_resp.status_code, 200)
        self.assertEqual(post_resp.json()["participant_id"], "P_TEST")

        # Retrieve evaluations
        get_resp = self.client.get("/api/evaluation-study")
        self.assertEqual(get_resp.status_code, 200)
        evals = get_resp.json()
        self.assertTrue(any(e["participant_id"] == "P_TEST" for e in evals))

    def test_websocket_live_streaming_transcribe(self):
        if vosk_model is None:
            self.skipTest("Vosk is optional; install the speech extra to enable offline recognition.")
        # Verify real-time streaming WebSocket endpoint connects and handles frames concurrently during recording
        with self.client.websocket_connect("/api/ws/transcribe") as websocket:
            # Send small 16kHz mono 16-bit PCM silence frame (3200 bytes = 100ms)
            silence_frame = b"\x00" * 3200
            websocket.send_bytes(silence_frame)
            # Send finish action
            websocket.send_text('{"action": "finish"}')
            data = websocket.receive_json()
            self.assertIn("type", data)
            self.assertEqual(data["type"], "complete")
            self.assertIn("text", data)


if __name__ == "__main__":
    unittest.main()
