# Self-Directed AI-Assisted Interview Practice Interface (CS 435)
> **CS 435 Human-Computer Interaction: Assignment 4 — High-Fidelity Prototyping & User Evaluation**  
> Indian Institute of Technology, Gandhinagar | Instructor: Dr. Yogesh K. Meena

---

## 🌟 Overview & Key Enhancements (Assignment 4)

This repository contains a working **High-Fidelity Prototype** and an interactive usability-evaluation interface.

### 🎙️ 1. Real-Time Bidirectional Voice Communication ($0.00 Free Tier)
- **Speech-to-Text (STT)**: Browser speech recognition with optional server-side recognition fallbacks, microphone status badges (`🔴 Listening...`), and animated audio equalizer wave bars.
- **Text-to-Speech (TTS)**: Native Web Speech Synthesis with natural system voices (Google/Microsoft), configurable speech rate (0.8x–1.3x), pitch controls, and an animated AI Interviewer Avatar (`Dr. Marcus Vance`) with radiating halo ripples.
- **Echo Prevention**: Automatic turn-taking coordination that mutes candidate audio capture while the system is speaking.

### 🧠 2. Dual-Mode AI Reasoning & Adaptive Probing
- **Google Gemini Free Tier Integration**: Powered by `gemini-1.5-flash` for realistic, conversational follow-up questioning and qualitative recommendations.
- **100% Offline Deterministic Engine**: Built-in rule-based STAR rubric evaluator running with 0ms latency and zero external dependencies when offline.

### 📊 3. Interactive User Evaluation & Ethics Kit (CS 435 Rubric — 20%)
- **Ethical Consent & Safeguards**: Consent banner and participant evaluation form. Study responses are stored in the local SQLite database.
- **Psychometric SUS Calculator**: 10-item System Usability Scale (SUS) form that computes a score from submitted responses.
- **One-Click Dataset Export**: Exports recorded evaluation entries to JSON and CSV.

### 📄 4. Documentation
- Installation, run, optional speech-recognition setup, and test instructions are provided below.

---

## 🚀 Key Features

### 1. Prototype A — Immediate Feedback & Iterative Learning
Designed for focused instructional improvement (`Home → Setup → Question → Answer → Feedback → Why? → Reflection → Retry → Compare → Progress`):
- **Transparent Rubric Scoring**: Scores on 4 inspectable criteria:
  - **Relevance** (alignment with question and target role)
  - **Specificity** (concrete tools, methods, frameworks)
  - **Evidence & Outcome** (STAR Result with quantifiable impact)
  - **Structure & Clarity** (chronological narrative flow)
- **🔍 "Why This Feedback?" Audit Trail**: Direct explanation citing user sentences and explicitly breaking down why a score was awarded.
- **Guided Reflection**: Guided metacognitive prompts (*"What would you change?"* and *"What did you learn?"*).
- **Side-by-Side Attempt Comparison**: Direct diff table comparing Attempt 1 vs Attempt 2 with score deltas (`+4.0 in Evidence`, etc.) and detected improvements.

### 2. Prototype B — Full Interview Simulation (Realism-Oriented)
Designed for uninterrupted, realistic interview practice (`Home → Setup → Multi-Question Simulation with Adaptive Follow-ups → Interview Complete → Overall Feedback → Detailed Breakdown → Selective Retry`):
- **Conversational Simulation Room**: Chat-based interview interface simulating a real human interviewer.
- **Adaptive Follow-Up Questions**: Generates follow-up questions in real time based on what the candidate mentioned (e.g., probing unresolved conflict outcomes or risk mitigation).
- **Post-Interview Analysis**: Overall and question-by-question rubric breakdown with selective retry.

### 3. Interactive Style Switcher: Low-Fi Wireframe vs Modern UI
- **Low-Fidelity Wireframe Mode**: Replicates the exact hand-drawn aesthetic of the PowerPoint wireframes (`CS435_Task2_Low_Fidelity_Prototype_Wireframes.pptx`), complete with sticky annotations and clickable connection flows.
- **High-Fidelity Modern Mode**: Clean, responsive, glassmorphic web interface.

### 4. Longitudinal Progress & Profile Tracking (SQLite)
- Persistent database tracking performance history, attempt trajectories, and recurring weaknesses across sessions.
- Interactive **Chart.js** trend visualizer showing scores over time.

### 5. Research & Survey Explorer
- Interactive explorer for survey summaries, literature themes, research questions, and user requirements.

### 6. DOCX & PPTX Export Engine
- Powered by `python-docx` and `python-pptx` to dynamically generate and download:
  - Formatted **DOCX Evaluation & Reflection Reports**
  - **PPTX Wireframe Summaries**

### 7. Voice Dictation (Speech-to-Text)
- Integrated Web Speech API toggle allowing candidates to dictate responses verbally or type them.

---

## 📁 Project Structure

```
my_project/
├── app/
│   ├── __init__.py
│   ├── models.py           # Pydantic schemas (rubrics, sessions, attempts, comparisons)
│   ├── evaluator.py        # Inspectable rubric scoring & adaptive follow-up engine
│   ├── database.py         # SQLite persistence for longitudinal tracking
│   ├── data_manager.py     # Personas (Aditi, Rahul), question banks, survey data (N=30)
│   ├── report_generator.py # Python-docx & python-pptx report builders
│   └── interview_practice.db # Created locally on first run; not tracked
├── static/
│   ├── index.html          # Unified single-page web interface (Prototype A, B & Research Hub)
│   ├── style.css           # Modern styles + Low-Fi wireframe mode overrides
│   └── app.js              # Client-side state, Chart.js analytics, voice dictation
├── tests/
│   ├── test_app.py         # Unit tests (evaluator, DB, comparisons, reports)
│   ├── test_api.py         # Integration tests (FastAPI endpoints)
│   └── test_regressions.py # Regression tests
├── main.py                 # FastAPI application entry point
├── pyproject.toml          # Project metadata & dependencies
└── README.md
```

---

## 🛠️ Installation & Quick Start

### Prerequisites
- Python 3.11+
- `uv` (recommended) or standard `pip`

### Step 1: Install Dependencies
```powershell
uv sync
```
*Or using standard pip:*
```powershell
pip install -e .
```

Offline Vosk speech recognition is optional. To enable it, install the speech extra:
```powershell
uv sync --extra speech
```
On first startup, Vosk may download its small English model if it is not already present; that requires an internet connection. Without Vosk, the app uses the available browser or configured speech-recognition fallbacks.

### Step 2: Run the Application
```powershell
uv run python main.py
```
*Or:*
```powershell
python main.py
```

The application will start at:
👉 **`http://127.0.0.1:8000`**

Open your browser to explore both Prototype A and Prototype B!

---

## 🧪 Running the Tests

A comprehensive test suite verifies rubric evaluation, attempt comparisons, adaptive questions, database persistence, and docx/pptx generation:

```powershell
uv run python -m unittest discover tests
```
The offline Vosk speech tests are skipped unless Vosk is installed with `uv sync --extra speech`.

---

## 👥 Personas & Scenarios Tested

| Persona | Role | Scenario | Target Interaction |
| :--- | :--- | :--- | :--- |
| **Aditi** (23, Master's Student) | UX Research Intern | Scenario 1 & 2 | Immediate feedback → "Why this feedback?" → Reflection → Retry on same question → Attempt comparison |
| **Rahul** (24, Recent Graduate) | Associate Product Manager | Scenario 3 | Multi-turn simulation with adaptive follow-up questions → Post-interview overall breakdown |

---

## 📄 References
- Daryanto et al. (2025), *Conversate: Supporting Reflective Learning in Interview Practice Through Interactive Simulation and Dialogic Feedback*.
