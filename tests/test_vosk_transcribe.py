import io
import json
import wave
import unittest
from fastapi.testclient import TestClient
from main import app, vosk_model

class TestVoskTranscription(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_vosk_recognizer_initialization(self):
        if vosk_model is None:
            self.skipTest("Vosk is optional; install the speech extra to enable offline recognition.")
        self.assertIsNotNone(vosk_model)

    def test_transcribe_endpoint_with_wav(self):
        if vosk_model is None:
            self.skipTest("Vosk is optional; install the speech extra to enable offline recognition.")
        # Generate 1.5 seconds of 16kHz 16-bit mono PCM audio
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"\x00\x00" * 24000)

        buf.seek(0)
        files = {"audio": ("test_speech.wav", buf.getvalue(), "audio/wav")}
        response = self.client.post("/api/transcribe", files=files)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("transcript", data)
        self.assertIn("source", data)
        self.assertEqual(data["source"], "vosk_local_offline")
        print("[Endpoint Test Log] /api/transcribe returned:", data)

if __name__ == "__main__":
    unittest.main()
