"""
FastAPI Main Application for Self-Directed AI-Assisted Interview Practice Interface.
Synthesized from CS 435 Task 2 Specifications & Wireframes.
"""

import os
import uuid
import base64
from typing import Dict, Any, List
import httpx
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.models import (
    SessionSetupRequest,
    AnswerSubmitRequest,
    ReflectionSubmitRequest,
    FollowUpRequest,
    InterviewTurnRequest,
    EvaluationResult,
    AttemptComparison,
    ConfigUpdateRequest,
    UserEvaluationSubmission
)
from app.evaluator import evaluator
from app.env_loader import get_env_variable, DOTENV_PATH
from app.data_manager import PERSONAS, QUESTION_BANKS, SURVEY_INSIGHTS, ROL_SYNTHESIS, get_question_bank_for_role
from app.database import (
    init_db,
    save_session,
    save_attempt,
    save_reflection,
    get_attempts_for_question,
    get_longitudinal_progress,
    get_session_report_data,
    save_user_evaluation,
    get_user_evaluations
)
from app.report_generator import generate_docx_report, generate_pptx_summary

# Initialize database
init_db()
EXPORTS_DIR = os.path.join(os.path.dirname(__file__), "exports")

# Initialize 100% Offline Local Speech Recognition (Vosk ASR)
vosk_model = None
try:
    import io
    import json
    import wave
    from vosk import Model, KaldiRecognizer
    vosk_model = Model(lang="en-us")
    print("[OK] Vosk Offline Speech-to-Text Model loaded successfully!")
except Exception as _vosk_err:
    try:
        print("[Notice] Vosk offline model initialization:", str(_vosk_err))
    except Exception:
        pass

app = FastAPI(
    title="Self-Directed AI-Assisted Interview Practice System",
    description="Interactive Prototype A & B implementation based on CS 435 HCI Project Specification",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session tracker for live interaction
active_sessions: Dict[str, Dict[str, Any]] = {}

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_home():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h2>AI Interview Practice System is loading...</h2>")


@app.get("/api/personas")
async def get_personas():
    return PERSONAS


@app.get("/api/survey-data")
async def get_survey_data():
    return {
        "survey": SURVEY_INSIGHTS,
        "rol": ROL_SYNTHESIS
    }


@app.get("/api/questions")
async def get_questions(role: str = "Software Engineer"):
    return get_question_bank_for_role(role)


@app.post("/api/setup")
async def setup_session(req: SessionSetupRequest):
    session_id = f"sess_{uuid.uuid4().hex[:8]}"
    cand_name = (req.candidate_name or "").strip() or "Candidate"
    job_role = req.job_role or "Software Engineer"

    # AI-driven custom interview questioning (NVIDIA Nemotron 3.5 Super VL via OpenRouter, with curated fallback)
    questions = await evaluator.generate_custom_interview_questions(
        candidate_name=cand_name,
        job_role=job_role,
        target_company=req.target_company or "",
        experience_level=req.experience_level or "Mid-Level",
        interview_type=req.interview_type or "Behavioral",
        difficulty=req.difficulty or "Medium",
        cv_text=req.cv_text or "",
        job_description=req.job_description or "",
        count=3
    )

    company_ref = f" at {req.target_company}" if req.target_company else ""
    opening_greeting = (
        f"Good morning, {cand_name}! Welcome to your official mock interview for the {job_role} position{company_ref}. "
        "I'm Dr. Marcus Vance, lead hiring evaluator for our team today. Thanks for taking the time to join me. "
        "To kick off our conversation, could you please introduce yourself, walk me through your background, and share what brings you to this role?"
    )

    if req.prototype_type == "B":
        first_q = {
            "id": 1,
            "text": opening_greeting,
            "category": "Stage 1: Introduction & Background",
            "difficulty": req.difficulty or "Medium",
            "competency": "Self-Introduction & Background",
            "ideal_structure": "Background, technical trajectory, and role alignment",
            "key_lookouts": ["Clear career trajectory", "Relevant skills", "Confidence"],
            "source": "official_interview_protocol"
        }
        questions = [first_q] + questions

    session_info = {
        "id": session_id,
        "prototype_type": req.prototype_type,
        "candidate_name": cand_name,
        "job_role": job_role,
        "target_company": req.target_company or "",
        "experience_level": req.experience_level or "Mid-Level",
        "interview_type": req.interview_type or "Behavioral",
        "difficulty": req.difficulty or "Medium",
        "cv_text": req.cv_text,
        "job_description": req.job_description,
        "persona_id": req.persona_id or "custom",
        "current_question_index": 0,
        "questions": questions,
        "conversation_history": [{"role": "assistant", "content": opening_greeting}] if req.prototype_type == "B" else [],
        "turn_index": 1,
        "attempts": [],
        "reflections": [],
        "overall_score": 0.0,
        "status": "in_progress"
    }
    active_sessions[session_id] = session_info
    save_session(session_info)

    return {
        "session_id": session_id,
        "prototype_type": req.prototype_type,
        "candidate_name": cand_name,
        "job_role": job_role,
        "first_question": questions[0] if questions else None,
        "questions": questions,
        "total_questions": len(questions)
    }


@app.post("/api/evaluate")
async def evaluate_answer(req: AnswerSubmitRequest):
    sess = active_sessions.get(req.session_id)
    job_role = sess.get("job_role", "Software Engineer") if sess else "Software Engineer"
    cand_name = sess.get("candidate_name", "Candidate") if sess else "Candidate"
    target_comp = sess.get("target_company", "") if sess else ""
    exp_level = sess.get("experience_level", "") if sess else ""
    cv_text = sess.get("cv_text", "") if sess else ""
    jd_text = sess.get("job_description", "") if sess else ""

    # Rubric-grounded evaluation (OpenRouter Nemotron / Gemini / Deterministic STAR fallback)
    eval_result = await evaluator.evaluate_answer_ai(
        question_text=req.question_text,
        answer_text=req.answer_text,
        job_role=job_role,
        attempt_number=req.attempt_number,
        candidate_name=cand_name,
        target_company=target_comp,
        experience_level=exp_level,
        cv_text=cv_text,
        job_description=jd_text
    )

    # Persist in DB and session memory
    save_attempt(
        session_id=req.session_id,
        question_id=req.question_id,
        attempt_number=req.attempt_number,
        question_text=req.question_text,
        answer_text=req.answer_text,
        evaluation=eval_result.model_dump()
    )

    if sess:
        sess["attempts"].append({
            "question_id": req.question_id,
            "attempt_number": req.attempt_number,
            "question_text": req.question_text,
            "answer_text": req.answer_text,
            "evaluation": eval_result.model_dump()
        })
        sess["overall_score"] = eval_result.overall_score

    return eval_result


@app.post("/api/reflect")
async def submit_reflection(req: ReflectionSubmitRequest):
    save_reflection(
        session_id=req.session_id,
        question_id=req.question_id,
        what_would_you_change=req.what_would_you_change,
        what_did_you_learn=req.what_did_you_learn
    )
    sess = active_sessions.get(req.session_id)
    if sess:
        sess["reflections"].append({
            "question_id": req.question_id,
            "what_would_you_change": req.what_would_you_change,
            "what_did_you_learn": req.what_did_you_learn
        })
    return {"status": "saved", "message": "Reflection saved to persistent profile."}


@app.post("/api/compare")
async def compare_user_attempts(session_id: str, question_id: int):
    attempts = get_attempts_for_question(session_id, question_id)
    if len(attempts) < 2:
        # Check active session memory
        sess = active_sessions.get(session_id)
        if sess:
            q_att = [a for a in sess["attempts"] if a["question_id"] == question_id]
            if len(q_att) >= 2:
                attempts = q_att

    if len(attempts) < 2:
        raise HTTPException(status_code=400, detail="At least two attempts are required to compare.")

    att1 = attempts[0]
    att2 = attempts[1]

    # Use the scores shown when each attempt was submitted.
    job_role = "UX Research Intern"
    if session_id in active_sessions:
        job_role = active_sessions[session_id].get("job_role", job_role)

    def get_attempt_evaluation(attempt, attempt_number):
        stored = attempt.get("evaluation") or attempt.get("eval_json") or {}
        if stored:
            return EvaluationResult.model_validate(stored)
        return evaluator.evaluate_answer(
            attempt["question_text"],
            attempt["answer_text"],
            job_role,
            attempt.get("attempt_number", attempt_number),
        )

    eval1 = get_attempt_evaluation(att1, 1)
    eval2 = get_attempt_evaluation(att2, 2)

    comp = evaluator.compare_attempts(
        question_id=question_id,
        question_text=att1["question_text"],
        attempt1_answer=att1["answer_text"],
        attempt2_answer=att2["answer_text"],
        eval1=eval1,
        eval2=eval2
    )
    return comp


@app.post("/api/interview/turn")
async def handle_interview_turn(req: InterviewTurnRequest):
    sess = active_sessions.get(req.session_id)
    cand_name = sess.get("candidate_name", "Candidate") if sess else "Candidate"
    target_comp = sess.get("target_company", "") if sess else ""
    exp_level = sess.get("experience_level", "") if sess else ""
    cv_text = sess.get("cv_text", "") if sess else ""
    jd_text = sess.get("job_description", "") if sess else ""
    role = req.job_role or (sess.get("job_role", "Software Engineer") if sess else "Software Engineer")
    history = req.conversation_history or (sess.get("conversation_history", []) if sess else [])

    turn_res = await evaluator.conduct_official_interview_turn(
        conversation_history=history,
        user_message=req.user_message,
        candidate_name=cand_name,
        job_role=role,
        target_company=target_comp,
        experience_level=exp_level,
        cv_text=cv_text,
        job_description=jd_text,
        turn_index=req.turn_index
    )

    if sess:
        if "conversation_history" not in sess:
            sess["conversation_history"] = []
        sess["conversation_history"].append({"role": "user", "content": req.user_message})
        sess["conversation_history"].append({"role": "assistant", "content": turn_res["interviewer_message"]})
        sess["turn_index"] = turn_res["turn_index"]

    return turn_res


@app.post("/api/followup")
async def generate_followup(req: FollowUpRequest):
    sess = active_sessions.get(req.session_id)
    cand_name = sess.get("candidate_name", "Candidate") if sess else "Candidate"
    target_comp = sess.get("target_company", "") if sess else ""
    exp_level = sess.get("experience_level", "") if sess else ""
    cv_text = sess.get("cv_text", "") if sess else ""
    jd_text = sess.get("job_description", "") if sess else ""
    history = sess.get("conversation_history", []) if sess else []

    # If active session exists, advance official interview multi-turn progression
    if sess:
        turn_idx = sess.get("turn_index", 1)
        turn_res = await evaluator.conduct_official_interview_turn(
            conversation_history=history,
            user_message=req.user_answer,
            candidate_name=cand_name,
            job_role=req.job_role,
            target_company=target_comp,
            experience_level=exp_level,
            cv_text=cv_text,
            job_description=jd_text,
            turn_index=turn_idx
        )
        if "conversation_history" not in sess:
            sess["conversation_history"] = []
        sess["conversation_history"].append({"role": "user", "content": req.user_answer})
        sess["conversation_history"].append({"role": "assistant", "content": turn_res["interviewer_message"]})
        sess["turn_index"] = turn_res["turn_index"]
        return turn_res

    res = await evaluator.generate_adaptive_followup_ai(
        previous_question=req.previous_question,
        user_answer=req.user_answer,
        job_role=req.job_role,
        candidate_name=cand_name,
        target_company=target_comp,
        experience_level=exp_level,
        cv_text=cv_text,
        job_description=jd_text
    )
    return res


def update_dotenv_key(key: str, val: str):
    """Syncs updated configuration keys to the project .env file."""
    lines = DOTENV_PATH.read_text(encoding="utf-8").splitlines(keepends=True) if DOTENV_PATH.exists() else []
    found = False
    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={val}\n")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={val}\n")
    try:
        DOTENV_PATH.write_text("".join(new_lines), encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Unable to save API key configuration.") from exc


@app.get("/api/config")
async def get_config():
    openrouter_key = evaluator.get_openrouter_api_key()
    gemini_key = evaluator.get_gemini_api_key()
    has_openrouter = bool(openrouter_key)
    has_gemini = bool(gemini_key)
    mode = "openrouter_nemotron" if has_openrouter else ("gemini_free_tier" if has_gemini else "deterministic_offline")
    return {
        "openrouter_active": has_openrouter,
        "openrouter_model": evaluator.openrouter_model,
        "gemini_active": has_gemini,
        "mode": mode,
        "stt_engine": "web_speech_api",
        "tts_engine": "web_speech_synthesis"
    }


@app.post("/api/config")
async def update_config(req: ConfigUpdateRequest):
    if req.openrouter_api_key is not None:
        clean_or_key = req.openrouter_api_key.strip()
        update_dotenv_key("OPENROUTER_API_KEY", clean_or_key)
        evaluator.openrouter_api_key = clean_or_key
        os.environ["OPENROUTER_API_KEY"] = clean_or_key

    if req.openrouter_model and req.openrouter_model.strip():
        clean_model = req.openrouter_model.strip()
        evaluator.openrouter_model = clean_model
        os.environ["OPENROUTER_MODEL"] = clean_model
        update_dotenv_key("OPENROUTER_MODEL", clean_model)

    if req.gemini_api_key is not None:
        clean_gem_key = req.gemini_api_key.strip()
        update_dotenv_key("GEMINI_API_KEY", clean_gem_key)
        evaluator.gemini_api_key = clean_gem_key
        os.environ["GEMINI_API_KEY"] = clean_gem_key

    return {
        "status": "updated",
        "openrouter_active": bool(evaluator.get_openrouter_api_key()),
        "openrouter_model": evaluator.openrouter_model,
        "gemini_active": bool(evaluator.get_gemini_api_key())
    }


@app.get("/api/evaluation-study")
async def list_evaluation_studies():
    return get_user_evaluations()


@app.post("/api/evaluation-study")
async def submit_evaluation_study(req: UserEvaluationSubmission):
    if not req.ethical_consent_signed:
        raise HTTPException(status_code=400, detail="Participant consent is required.")
    save_user_evaluation(req.model_dump())
    return {"status": "saved", "participant_id": req.participant_id}


@app.get("/api/web-search")
async def web_search(q: str = ""):
    """
    Real-Time Web Search API for interview preparation, role research, and interview questions.
    Uses DuckDuckGo search with structured fallbacks. Zero external keys required ($0.00 Free Tier).
    """
    query = (q or "").strip()
    if not query:
        return {"query": "", "results": []}

    results = []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "https://api.duckduckgo.com/",
                params={
                    "q": query,
                    "format": "json",
                    "no_html": "1",
                    "skip_disambig": "1"
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("AbstractText"):
                    results.append({
                        "title": data.get("Heading") or query,
                        "snippet": data.get("AbstractText"),
                        "url": data.get("AbstractURL") or "https://duckduckgo.com"
                    })
                for topic in data.get("RelatedTopics", [])[:5]:
                    if isinstance(topic, dict) and topic.get("Text"):
                        results.append({
                            "title": topic.get("Text").split(" - ")[0] if " - " in topic.get("Text") else query,
                            "snippet": topic.get("Text"),
                            "url": topic.get("FirstURL") or "https://duckduckgo.com"
                        })
    except Exception as search_err:
        print("[Web Search API Notice]:", search_err)

    if not results:
        results = [
            {
                "title": f"Interview Preparation & Best Practices for '{query}'",
                "snippet": f"Key frameworks for answering '{query}' include the STAR method (Situation, Task, Action, Result) with quantifiable metrics and concrete trade-off rationale.",
                "url": "https://en.wikipedia.org/wiki/Situation,_task,_action_and_result"
            },
            {
                "title": f"Behavioral Competencies & Question Bank: {query}",
                "snippet": "Top hiring rubrics evaluate candidates on Relevance to role, Specificity of technical actions, Evidence of impact, and Communication structure.",
                "url": "https://hbr.org/topic/subject/interviews"
            }
        ]

    return {
        "query": query,
        "results": results,
        "source": "web_search_api"
    }


@app.websocket("/api/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    """
    Live streaming Speech-to-Text WebSocket endpoint.
    Converts incoming audio frames in real time concurrently DURING recording,
    eliminating sequential delays and delivering instantaneous transcription on finish.
    """
    await websocket.accept()
    if not vosk_model:
        await websocket.send_json({"type": "error", "message": "Speech engine unavailable"})
        await websocket.close()
        return

    rec = KaldiRecognizer(vosk_model, 16000)
    rec.SetWords(True)
    accumulated_words: List[str] = []

    try:
        while True:
            message = await websocket.receive()
            if "bytes" in message and message["bytes"]:
                chunk = message["bytes"]
                if chunk:
                    if rec.AcceptWaveform(chunk):
                        res = json.loads(rec.Result())
                        text = res.get("text", "").strip()
                        if text:
                            accumulated_words.append(text)
                            current_total = " ".join(accumulated_words).strip()
                            await websocket.send_json({
                                "type": "final",
                                "text": text,
                                "accumulated": current_total
                            })
                    else:
                        part = json.loads(rec.PartialResult())
                        partial_text = part.get("partial", "").strip()
                        if partial_text:
                            current_preview = (" ".join(accumulated_words) + " " + partial_text).strip()
                            await websocket.send_json({
                                "type": "partial",
                                "text": partial_text,
                                "accumulated": current_preview
                            })
            elif "text" in message and message["text"]:
                try:
                    payload = json.loads(message["text"])
                    if payload.get("action") == "finish":
                        final_res = json.loads(rec.FinalResult())
                        final_text = final_res.get("text", "").strip()
                        if final_text:
                            accumulated_words.append(final_text)
                        full_result = " ".join(accumulated_words).strip()
                        if full_result:
                            full_result = full_result[0].upper() + full_result[1:] + "."
                        await websocket.send_json({
                            "type": "complete",
                            "text": full_result
                        })
                        break
                except Exception:
                    pass
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print("[WebSocket Transcribe Notice]:", e)


@app.post("/api/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    audio_bytes = await audio.read()

    # 1. Primary: 100% Offline Local Vosk Speech Recognition (Zero Network, Zero Cloud, 100% Private)
    if vosk_model and len(audio_bytes) > 200:
        try:
            with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
                framerate = wf.getframerate()
                rec = KaldiRecognizer(vosk_model, framerate)
                rec.SetWords(True)
                words = []
                while True:
                    data = wf.readframes(4000)
                    if len(data) == 0:
                        break
                    if rec.AcceptWaveform(data):
                        part = json.loads(rec.Result())
                        txt = part.get("text", "").strip()
                        if txt:
                            words.append(txt)
                final_part = json.loads(rec.FinalResult())
                txt_final = final_part.get("text", "").strip()
                if txt_final:
                    words.append(txt_final)

                transcript = " ".join(words).strip()
                if transcript:
                    formatted = transcript[0].upper() + transcript[1:] + "."
                    return {
                        "transcript": formatted,
                        "source": "vosk_local_offline",
                        "words_count": len(formatted.split())
                    }
                else:
                    return {
                        "transcript": "",
                        "source": "vosk_local_offline",
                        "message": "No clear speech detected. Please speak closer to microphone."
                    }
        except Exception as v_err:
            print("[Vosk Transcription Notice]:", v_err)

    # 2. Secondary: Gemini Free Tier if API key available
    key = evaluator.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
    if key and len(audio_bytes) > 200:
        b64 = base64.b64encode(audio_bytes).decode("utf-8")
        mime = audio.content_type or "audio/wav"
        prompt = "Transcribe the candidate's spoken interview response verbatim. Return ONLY the transcribed text without extra commentary."
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}",
                    json={
                        "contents": [{
                            "parts": [
                                {"inline_data": {"mime_type": mime, "data": b64}},
                                {"text": prompt}
                            ]
                        }]
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                        if text:
                            return {"transcript": text, "source": "gemini_free_audio"}
        except Exception:
            pass

    # 3. Tertiary: SpeechRecognition Google fallback (if unblocked)
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio_data = r.record(source)
            transcript = r.recognize_google(audio_data)
            if transcript and transcript.strip():
                return {"transcript": transcript.strip(), "source": "speech_recognition_google"}
    except Exception:
        pass

    return {
        "transcript": "",
        "source": "empty",
        "message": "Could not recognize audio. Please speak clearly or type your answer."
    }



@app.get("/api/progress")
async def get_progress(persona_id: str = "aditi"):
    data = get_longitudinal_progress(persona_id)
    return data


@app.get("/api/export-docx/{session_id}")
async def export_docx(session_id: str):
    sess = active_sessions.get(session_id) or get_session_report_data(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    out_path = os.path.join(EXPORTS_DIR, f"{session_id}_report.docx")
    generate_docx_report(sess, out_path)
    return FileResponse(out_path, filename=f"Interview_Report_{session_id}.docx", media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@app.get("/api/export-pptx/{session_id}")
async def export_pptx(session_id: str):
    sess = active_sessions.get(session_id) or get_session_report_data(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    out_path = os.path.join(EXPORTS_DIR, f"{session_id}_summary.pptx")
    generate_pptx_summary(sess, out_path)
    return FileResponse(out_path, filename=f"Interview_Wireframes_{session_id}.pptx", media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")


def run():
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    run()
