"""
SQLite Database module for persistent storage of sessions, attempts,
reflections, and longitudinal user profiles across practice sessions.
"""

import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, Any, Iterator, List, Optional
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "interview_practice.db")


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        cursor = conn.cursor()

        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                prototype_type TEXT NOT NULL,
                job_role TEXT NOT NULL,
                interview_type TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                persona_id TEXT DEFAULT 'aditi',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'in_progress',
                overall_score REAL DEFAULT 0.0
            )
        """)

        # Attempts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                question_id INTEGER NOT NULL,
                attempt_number INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                answer_text TEXT NOT NULL,
                overall_score REAL NOT NULL,
                relevance_score REAL NOT NULL,
                specificity_score REAL NOT NULL,
                evidence_score REAL NOT NULL,
                structure_score REAL NOT NULL,
                eval_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            )
        """)

        # Reflections table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reflections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                question_id INTEGER NOT NULL,
                what_would_you_change TEXT NOT NULL,
                what_did_you_learn TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            )
        """)

        # Profiles / Longitudinal summary
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                persona_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                target_role TEXT NOT NULL,
                focus_area TEXT NOT NULL,
                recurring_weaknesses TEXT NOT NULL,
                total_practices INTEGER DEFAULT 0,
                avg_score REAL DEFAULT 0.0
            )
        """)

        # Seed initial profile data reflecting docx/pptx
        cursor.execute("SELECT COUNT(*) FROM profiles WHERE persona_id = 'aditi'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO profiles (persona_id, name, target_role, focus_area, recurring_weaknesses, total_practices, avg_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                "aditi",
                "Aditi",
                "UX Research Intern",
                "Providing concrete outcome / evidence",
                json.dumps(["Omits measurable outcomes", "Tendency to stop after describing action"]),
                3,
                7.5
            ))

        # User evaluations study table for CS 435 Assignment 4
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                participant_id TEXT NOT NULL,
                target_role TEXT NOT NULL,
                prototype_tested TEXT NOT NULL,
                task_completed INTEGER DEFAULT 1,
                task_time_seconds INTEGER DEFAULT 0,
                sus_scores TEXT NOT NULL,
                sus_total_score REAL NOT NULL,
                feedback_realism TEXT,
                feedback_learning TEXT,
                ethical_consent_signed INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM profiles WHERE persona_id = 'rahul'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO profiles (persona_id, name, target_role, focus_area, recurring_weaknesses, total_practices, avg_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                "rahul",
                "Rahul",
                "Associate Product Manager",
                "Structuring answers with clear outcome metrics",
                json.dumps(["Needs sharper metrics on business impact", "Over-indexing on technical details vs stakeholder alignment"]),
                2,
                7.4
            ))

        # Check if pre-seeded history exists for demo longitudinal tracking
        cursor.execute("SELECT COUNT(*) FROM sessions WHERE id LIKE 'demo_%'")
        if cursor.fetchone()[0] == 0:
            # Seed Session 1
            cursor.execute("""
                INSERT INTO sessions (id, prototype_type, job_role, interview_type, difficulty, persona_id, created_at, status, overall_score)
                VALUES ('demo_sess_1', 'A', 'UX Research Intern', 'Behavioral', 'Medium', 'aditi', '2026-10-01 10:00:00', 'completed', 6.0)
            """)
            cursor.execute("""
                INSERT INTO attempts (session_id, question_id, attempt_number, question_text, answer_text, overall_score, relevance_score, specificity_score, evidence_score, structure_score, eval_json)
                VALUES ('demo_sess_1', 1, 1, 'Tell me about a time when you worked with a difficult teammate.', 'I had a conflict with a teammate and we talked it out and finished the project.', 6.0, 7.0, 6.0, 4.0, 6.0, '{}')
            """)

            # Seed Session 2
            cursor.execute("""
                INSERT INTO sessions (id, prototype_type, job_role, interview_type, difficulty, persona_id, created_at, status, overall_score)
                VALUES ('demo_sess_2', 'A', 'UX Research Intern', 'Behavioral', 'Medium', 'aditi', '2026-10-04 14:30:00', 'completed', 8.0)
            """)
            cursor.execute("""
                INSERT INTO attempts (session_id, question_id, attempt_number, question_text, answer_text, overall_score, relevance_score, specificity_score, evidence_score, structure_score, eval_json)
                VALUES ('demo_sess_2', 1, 2, 'Tell me about a time when you worked with a difficult teammate.', 'During our sprint, I resolved a teammate disagreement by showing user research video clips. As a result we delivered 2 days early with 95% satisfaction.', 8.0, 8.5, 8.0, 7.5, 8.0, '{}')
            """)

            # Seed Session 3
            cursor.execute("""
                INSERT INTO sessions (id, prototype_type, job_role, interview_type, difficulty, persona_id, created_at, status, overall_score)
                VALUES ('demo_sess_3', 'A', 'UX Research Intern', 'Behavioral', 'Medium', 'aditi', '2026-10-08 09:15:00', 'completed', 8.5)
            """)
            cursor.execute("""
                INSERT INTO attempts (session_id, question_id, attempt_number, question_text, answer_text, overall_score, relevance_score, specificity_score, evidence_score, structure_score, eval_json)
                VALUES ('demo_sess_3', 2, 1, 'Describe a usability study you conducted where results contradicted product team assumptions.', 'I conducted evaluative usability tests on the checkout flow. The team expected users to love the 1-click buy, but 60% encountered errors. I presented a clip reel and recommended a 2-step verification. Result: cart abandonment decreased by 22%.', 8.5, 9.0, 8.5, 8.5, 8.5, '{}')
            """)

        conn.commit()


def save_session(session_data: Dict[str, Any]):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO sessions (id, prototype_type, job_role, interview_type, difficulty, persona_id, created_at, status, overall_score)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?, ?)
        """, (
            session_data["id"],
            session_data.get("prototype_type", "A"),
            session_data.get("job_role", "UX Research Intern"),
            session_data.get("interview_type", "Behavioral"),
            session_data.get("difficulty", "Medium"),
            session_data.get("persona_id", "aditi"),
            session_data.get("status", "in_progress"),
            session_data.get("overall_score", 0.0)
        ))
        conn.commit()


def save_attempt(
    session_id: str,
    question_id: int,
    attempt_number: int,
    question_text: str,
    answer_text: str,
    evaluation: Dict[str, Any]
):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO attempts (session_id, question_id, attempt_number, question_text, answer_text, overall_score, relevance_score, specificity_score, evidence_score, structure_score, eval_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            question_id,
            attempt_number,
            question_text,
            answer_text,
            evaluation["overall_score"],
            evaluation["relevance"]["score"],
            evaluation["specificity"]["score"],
            evaluation["evidence_outcome"]["score"],
            evaluation["structure_clarity"]["score"],
            json.dumps(evaluation)
        ))

        # Update session overall score
        cursor.execute("""
            UPDATE sessions 
            SET overall_score = (
                SELECT ROUND(AVG(overall_score), 1) FROM attempts WHERE session_id = ?
            )
            WHERE id = ?
        """, (session_id, session_id))

        conn.commit()


def save_reflection(
    session_id: str,
    question_id: int,
    what_would_you_change: str,
    what_did_you_learn: str
):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reflections (session_id, question_id, what_would_you_change, what_did_you_learn)
            VALUES (?, ?, ?, ?)
        """, (session_id, question_id, what_would_you_change, what_did_you_learn))
        conn.commit()


def get_attempts_for_question(session_id: str, question_id: int) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM attempts 
            WHERE session_id = ? AND question_id = ? 
            ORDER BY attempt_number ASC
        """, (session_id, question_id))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["eval_json"] = json.loads(d["eval_json"]) if d["eval_json"] else {}
            result.append(d)
        return result


def get_longitudinal_progress(persona_id: str = "aditi") -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()

        # Get all attempts
        cursor.execute("""
            SELECT a.*, s.job_role, s.created_at as session_date 
            FROM attempts a
            JOIN sessions s ON a.session_id = s.id
            WHERE s.persona_id = ?
            ORDER BY a.created_at ASC
        """, (persona_id,))
        attempts = [dict(r) for r in cursor.fetchall()]

        # Compute trajectory
        trajectory = []
        for idx, att in enumerate(attempts):
            trajectory.append({
                "attempt_label": f"Attempt {idx + 1}",
                "overall_score": att["overall_score"],
                "evidence_score": att["evidence_score"],
                "relevance_score": att["relevance_score"],
                "specificity_score": att["specificity_score"],
                "structure_score": att["structure_score"],
                "question": att["question_text"][:50] + "...",
                "date": att["created_at"][:10]
            })

        # Profile summary
        cursor.execute("SELECT * FROM profiles WHERE persona_id = ?", (persona_id,))
        profile_row = cursor.fetchone()
        profile = dict(profile_row) if profile_row else {
            "name": "User",
            "target_role": "UX Research Intern",
            "focus_area": "Providing concrete outcome / evidence",
            "recurring_weaknesses": json.dumps(["Omits measurable outcomes"]),
            "avg_score": 7.5
        }
        if isinstance(profile.get("recurring_weaknesses"), str):
            try:
                profile["recurring_weaknesses"] = json.loads(profile["recurring_weaknesses"])
            except Exception:
                profile["recurring_weaknesses"] = [profile["recurring_weaknesses"]]

        # Calculate average scores
        if trajectory:
            avg_overall = round(sum(t["overall_score"] for t in trajectory) / len(trajectory), 1)
            avg_evidence = round(sum(t["evidence_score"] for t in trajectory) / len(trajectory), 1)
        else:
            avg_overall = 7.5
            avg_evidence = 6.5

        return {
            "profile": profile,
            "trajectory": trajectory,
            "total_attempts": len(trajectory),
            "average_overall": avg_overall,
            "average_evidence": avg_evidence,
            "current_focus_area": "Providing concrete outcome / evidence (STAR: Result)",
            "action_advice": "Focus next session on quantifying results (e.g. percentages, user metrics, deliverable completion)."
        }


def get_session_report_data(session_id: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        session = conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if session is None:
            return None

        report_data = dict(session)
        report_data["session_id"] = report_data.pop("id")
        report_data["attempts"] = []
        for row in conn.execute(
            "SELECT * FROM attempts WHERE session_id = ? ORDER BY question_id, attempt_number",
            (session_id,),
        ):
            attempt = dict(row)
            attempt["evaluation"] = json.loads(attempt.pop("eval_json") or "{}")
            report_data["attempts"].append(attempt)

        report_data["reflections"] = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM reflections WHERE session_id = ? ORDER BY id",
                (session_id,),
            )
        ]
        return report_data


def save_user_evaluation(eval_data: Dict[str, Any]):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_evaluations (
                participant_id, target_role, prototype_tested, task_completed,
                task_time_seconds, sus_scores, sus_total_score,
                feedback_realism, feedback_learning, ethical_consent_signed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            eval_data.get("participant_id", "P01"),
            eval_data.get("target_role", "UX Research"),
            eval_data.get("prototype_tested", "Both"),
            1 if eval_data.get("task_completed", True) else 0,
            eval_data.get("task_time_seconds", 0),
            json.dumps(eval_data.get("sus_scores", [])),
            eval_data.get("sus_total_score", 82.5),
            eval_data.get("feedback_realism", ""),
            eval_data.get("feedback_learning", ""),
            1 if eval_data.get("ethical_consent_signed", True) else 0
        ))
        conn.commit()


def get_user_evaluations() -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_evaluations ORDER BY created_at DESC")
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["sus_scores"] = json.loads(d["sus_scores"])
            except Exception:
                pass
            result.append(d)
        return result
