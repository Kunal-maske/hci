"""
Data manager containing personas, question banks, survey data (N=30),
literature review findings, and user requirements synthesized from CS 435 Assignment 2.
"""

PERSONAS = {
    "aditi": {
        "id": "aditi",
        "name": "Aditi",
        "title": "Master's Student Seeking an Internship",
        "age": 23,
        "education": "Master's Student",
        "target_role": "UX Research Intern",
        "interview_type": "Behavioral",
        "difficulty": "Medium",
        "cv_summary": (
            "Master's candidate in HCI. Experience conducting 15+ semi-structured user interviews, "
            "usability evaluations, and persona development for educational apps. Proficient in Figma and qualitative coding."
        ),
        "job_description": (
            "Seeking a passionate UX Research Intern to collaborate with cross-functional product squads. "
            "Responsibilities: Plan and execute evaluative studies, synthesize user feedback into actionable insights, "
            "and communicate findings to designers and engineers."
        ),
        "pain_points": [
            "Unsure whether her answers are good or sufficiently rigorous",
            "Feedback from standard AI tools feels too generic",
            "Struggles to practice consistently without a live mentor",
            "Frequently describes actions well but leaves out measurable outcomes"
        ],
        "goals": "Practice independently, receive transparent rubric-grounded feedback, retry weak answers, and track progress.",
        "quote": "“I want to know exactly what was weak and how I can improve it.”",
        "previous_focus": "Providing concrete outcomes & measurable results"
    },
    "rahul": {
        "id": "rahul",
        "name": "Rahul",
        "title": "Recent Graduate Seeking Full-Time Roles",
        "age": 24,
        "education": "Recent Graduate (B.Tech / B.S.)",
        "target_role": "Associate Product Manager",
        "interview_type": "Behavioral",
        "difficulty": "Medium",
        "cv_summary": (
            "Computer Science graduate with leadership experience in student venture accelerator. "
            "Shipped 2 web applications, led agile sprint planning for a team of 5, and analyzed user retention funnels."
        ),
        "job_description": (
            "Associate Product Manager (APM). Seeking ambitious graduates to drive feature roadmaps, "
            "resolve cross-team conflicts, make data-informed trade-offs under ambiguity, and deliver business impact."
        ),
        "pain_points": [
            "Needs realistic interview simulation with tough follow-up questions",
            "Wants to avoid repeating the same mistake across interviews",
            "Needs an overarching improvement plan rather than piecemeal feedback"
        ],
        "goals": "Experience full adaptive mock interviews, reflect on systemic response patterns, and build a persistent longitudinal improvement profile.",
        "quote": "“I want each practice session to build on what I did last time.”",
        "previous_focus": "Structuring answers with clear outcome metrics"
    }
}

QUESTION_BANKS = {
    "UX Research Intern": [
        {
            "id": 1,
            "text": "Tell me about a time when you worked with a difficult teammate. What was the situation and how did you resolve it?",
            "category": "Behavioral",
            "difficulty": "Medium",
            "competency": "Conflict Resolution & Collaboration",
            "ideal_structure": "STAR (Situation, Task, Action, Result)",
            "key_lookouts": ["Did they describe the outcome?", "Was the teammate dehumanized?", "What proactive action was taken?"]
        },
        {
            "id": 2,
            "text": "Describe a usability study you conducted where the results completely contradicted the product team's assumptions. How did you communicate the findings?",
            "category": "Situational",
            "difficulty": "Medium",
            "competency": "Stakeholder Management & Evidence-Based Advocacy",
            "ideal_structure": "Context, Discrepancy, Communication strategy, Impact on product",
            "key_lookouts": ["Concrete methodology mentioned", "Diplomatic stakeholder handling", "Actionable design change"]
        },
        {
            "id": 3,
            "text": "How do you decide between conducting qualitative interviews versus running a quantitative survey when resources and time are limited?",
            "category": "Methodological",
            "difficulty": "Hard",
            "competency": "Research Design & Prioritization",
            "ideal_structure": "Evaluation criteria, Trade-offs, Concrete example of past decision",
            "key_lookouts": ["Clear distinction of exploratory vs evaluative", "Cost/time awareness", "Specific metrics"]
        }
    ],
    "Associate Product Manager": [
        {
            "id": 1,
            "text": "Tell me about a time you had a conflict with an engineering or design teammate over product requirements. What did you do?",
            "category": "Behavioral",
            "difficulty": "Medium",
            "competency": "Conflict Resolution & Cross-Functional Alignment",
            "ideal_structure": "STAR method with quantifiable resolution",
            "key_lookouts": ["Empathetic listening", "Root cause identification", "Business/user-centric resolution", "Outcome metric"]
        },
        {
            "id": 2,
            "text": "Tell me about a time you had to make a high-stakes decision with incomplete or conflicting user data.",
            "category": "Behavioral",
            "difficulty": "Hard",
            "competency": "Decision Making Under Uncertainty",
            "ideal_structure": "Context, Data gap, Risk mitigation framework, Decision made, Measured outcome",
            "key_lookouts": ["Risk assessment", "Hypothesis testing", "Post-launch validation"]
        },
        {
            "id": 3,
            "text": "How do you prioritize feature requests when two key executive stakeholders demand mutually exclusive roadmap items?",
            "category": "Situational",
            "difficulty": "Hard",
            "competency": "Prioritization & Executive Communication",
            "ideal_structure": "Framework (e.g. RICE), Data gathering, Stakeholder alignment session, Result",
            "key_lookouts": ["Objective criteria vs politics", "Transparent communication", "Impact tracking"]
        }
    ],
    "Software Engineer": [
        {
            "id": 1,
            "text": "Tell me about a time you encountered an unexpected and critical bug right before a production release.",
            "category": "Behavioral / Technical",
            "difficulty": "Medium",
            "competency": "Crisis Management & Problem Solving",
            "ideal_structure": "Situation, Root cause discovery, Quick fix vs permanent fix, Post-mortem outcome",
            "key_lookouts": ["Systematic debugging", "Communication to team", "Preventive measures"]
        },
        {
            "id": 2,
            "text": "Describe a technical disagreement you had regarding architecture or code style during a pull request review.",
            "category": "Behavioral",
            "difficulty": "Medium",
            "competency": "Constructive Code Review & Team Standards",
            "ideal_structure": "Disagreement context, Technical merits evaluated, Resolution consensus, Project outcome",
            "key_lookouts": ["Data/benchmark-driven choices", "Professional tone", "Long-term maintainability"]
        },
        {
            "id": 3,
            "text": "How do you handle technical debt when product deadlines are tight?",
            "category": "Situational",
            "difficulty": "Hard",
            "competency": "Engineering Pragmatism & Technical Strategy",
            "ideal_structure": "Assessment criteria, Trade-off negotiation with product, Tracking mechanisms",
            "key_lookouts": ["Business impact awareness", "Refactoring strategy", "Documenting debt"]
        }
    ],
    "Data Scientist": [
        {
            "id": 1,
            "text": "Tell me about a machine learning or data project where the model performed well offline but degraded significantly in production.",
            "category": "Technical & Behavioral",
            "difficulty": "Hard",
            "competency": "MLOps & Root Cause Analysis",
            "ideal_structure": "Context, Data drift discovery, Investigation steps, Retraining solution, Business outcome",
            "key_lookouts": ["Data hygiene", "Metric selection", "Cross-team communication"]
        },
        {
            "id": 2,
            "text": "How do you explain a complex black-box model to non-technical business stakeholders?",
            "category": "Behavioral / Communication",
            "difficulty": "Medium",
            "competency": "Data Storytelling & Stakeholder Alignment",
            "ideal_structure": "Metaphor used, Feature importance breakdown, Risk explanation, Decision impact",
            "key_lookouts": ["Clarity without condescension", "Actionable insights", "Confidence calibration"]
        }
    ],
    "General / Leadership": [
        {
            "id": 1,
            "text": "Tell me about a time when you worked with a difficult teammate or stakeholder. What was the situation and how did you resolve it?",
            "category": "Behavioral",
            "difficulty": "Medium",
            "competency": "Conflict Resolution & Collaboration",
            "ideal_structure": "STAR (Situation, Task, Action, Result)",
            "key_lookouts": ["Did they describe the outcome?", "Empathy demonstrated", "Measurable resolution"]
        },
        {
            "id": 2,
            "text": "Describe a time when you took initiative to solve an ambiguous problem without direct guidance from your manager.",
            "category": "Behavioral",
            "difficulty": "Medium",
            "competency": "Ownership & Problem Solving",
            "ideal_structure": "Ambiguity context, Framework chosen, Steps executed, Measured outcome",
            "key_lookouts": ["Bias for action", "Risk awareness", "Impact delivered"]
        }
    ]
}


def get_question_bank_for_role(role_name: str) -> list:
    """Return matching or closest question bank for any user-defined role."""
    r = (role_name or "").lower().strip()
    if any(k in r for k in ["ux", "design", "research", "hci"]):
        return QUESTION_BANKS["UX Research Intern"]
    if any(k in r for k in ["product", "apm", "pm", "manager"]):
        return QUESTION_BANKS["Associate Product Manager"]
    if any(k in r for k in ["data", "science", "ml", "ai", "analytics"]):
        return QUESTION_BANKS.get("Data Scientist", QUESTION_BANKS["General / Leadership"])
    if any(k in r for k in ["software", "engineer", "developer", "backend", "frontend", "sde"]):
        return QUESTION_BANKS["Software Engineer"]
    return QUESTION_BANKS["General / Leadership"]


SURVEY_INSIGHTS = {
    "total_n": 30,
    "participant_breakdown": [
        {"type": "Undergraduate student", "count": 14, "pct": 46.7},
        {"type": "Master's student", "count": 12, "pct": 40.0},
        {"type": "Working professional", "count": 2, "pct": 6.7},
        {"type": "PhD student", "count": 1, "pct": 3.3},
        {"type": "Incomplete", "count": 1, "pct": 3.3}
    ],
    "preparation_methods": [
        {"method": "Use ChatGPT or another AI tool", "count": 23, "pct": 79.3},
        {"method": "Practise alone", "count": 20, "pct": 69.0},
        {"method": "Watch interview-preparation videos", "count": 14, "pct": 48.3},
        {"method": "Read interview guides/articles", "count": 10, "pct": 34.5},
        {"method": "Practise with friends/classmates", "count": 9, "pct": 31.0},
        {"method": "Practise with a mentor/teacher", "count": 3, "pct": 10.3},
        {"method": "Dedicated interview platform", "count": 2, "pct": 6.9}
    ],
    "main_problems": [
        {"problem": "I don't know whether my answers are good", "count": 17, "pct": 58.6},
        {"problem": "I find it difficult to practise consistently", "count": 17, "pct": 58.6},
        {"problem": "Feedback is too generic", "count": 16, "pct": 55.2},
        {"problem": "I don't know whether I am improving over time", "count": 15, "pct": 51.7},
        {"problem": "No one available for mock interviews", "count": 13, "pct": 44.8},
        {"problem": "I don't know what questions to practise", "count": 12, "pct": 41.4},
        {"problem": "I don't know how to improve an answer", "count": 7, "pct": 24.1}
    ],
    "preferred_feedback": [
        {"type": "Strengths", "count": 24, "pct": 82.8},
        {"type": "Weaknesses", "count": 24, "pct": 82.8},
        {"type": "Specific suggestions for improvement", "count": 20, "pct": 69.0},
        {"type": "Feedback on clarity", "count": 19, "pct": 65.5},
        {"type": "Feedback on structure", "count": 19, "pct": 65.5},
        {"type": "Example of an improved answer", "count": 19, "pct": 65.5},
        {"type": "Feedback on evidence/examples", "count": 16, "pct": 55.2},
        {"type": "Overall score", "count": 14, "pct": 48.3}
    ],
    "why_feedback_importance": [
        {"rating": "4 or 5 (Often / Extremely Important)", "count": 18, "pct": 60.0},
        {"rating": "3 (Moderately Important)", "count": 10, "pct": 33.3},
        {"rating": "1 or 2 (Rarely / Not Important)", "count": 2, "pct": 6.7}
    ],
    "post_feedback_preference": [
        {"pref": "Have both options available", "count": 13, "pct": 43.3},
        {"pref": "Immediately try same question again", "count": 8, "pct": 26.7},
        {"pref": "Continue to next question & review later", "count": 6, "pct": 20.0},
        {"pref": "Not sure", "count": 2, "pct": 6.7}
    ]
}

ROL_SYNTHESIS = {
    "research_questions": [
        {"id": "RQ1", "text": "How do users perceive different forms of AI-generated interview feedback, and how transparent is that feedback about its own basis?"},
        {"id": "RQ2", "text": "Does adaptive, personalized questioning based on previous performance improve perceived usefulness and engagement, and does personalization persist across sessions?"},
        {"id": "RQ3", "text": "Does an iterative practice → feedback → reflection → retry workflow improve outcomes compared with one-shot AI feedback?"},
        {"id": "RQ4", "text": "How does feedback transparency, and the trustworthiness/consistency of the AI's judgments, affect user trust in AI interview assessment?"}
    ],
    "themes": [
        {
            "theme": "Theme 1: Feedback exists, but explanation does not",
            "gap": "None of the reviewed systems (VIPP, Conversate, ITEM) were fully transparent. Scoring mechanisms were opaque or unexplained.",
            "design_response": "Visible rubric criteria + 'Why This Feedback?' inspectable audit trail."
        },
        {
            "theme": "Theme 2: Personalization is mainly live-signal or role-locked, not longitudinal",
            "gap": "Existing systems adapt within a single session or by job title, but don't build a persistent multi-session learning profile.",
            "design_response": "Persistent user profile retaining past weaknesses, mistakes, and longitudinal progress tracking."
        },
        {
            "theme": "Theme 3: Generation and scoring are common; reflection loop is rare",
            "gap": "Systems score answers without an integrated invitation to reflect, rewrite the same weakness, and compare attempts.",
            "design_response": "Integrated Practice → Feedback → Reflection → Retry → Comparison workflow."
        },
        {
            "theme": "Theme 4: Trust and bias are acknowledged, not solved",
            "gap": "LLM sycophancy (Conversate) and fairness/robustness issues (ITEM) create trust deficits.",
            "design_response": "Grounded evaluation using fixed, transparent rubrics rather than unconstrained black-box LLM scoring."
        }
    ],
    "user_requirements": [
        {"id": "UR1", "name": "Realistic practice", "desc": "Simulate an interview and support contextually relevant follow-up questions."},
        {"id": "UR2", "name": "Personalized setup", "desc": "Select job role, interview type and difficulty, with CV/JD inputs."},
        {"id": "UR3", "name": "Adaptive questioning", "desc": "Adapt questions to current responses and previous performance."},
        {"id": "UR4", "name": "Specific feedback", "desc": "Identify strengths, weaknesses and concrete improvement areas."},
        {"id": "UR5", "name": "Transparent evaluation", "desc": "Show why a particular criterion received its evaluation with evidence."},
        {"id": "UR6", "name": "Actionable improvement", "desc": "Provide practical suggestions and an example improved answer."},
        {"id": "UR7", "name": "Reflection", "desc": "Prompt users to consider what they would change or learned."},
        {"id": "UR8", "name": "Retry", "desc": "Allow retry of the same question after feedback/reflection."},
        {"id": "UR9", "name": "Compare attempts", "desc": "Show score differences and qualitative changes between attempts."},
        {"id": "UR10", "name": "Longitudinal progress", "desc": "Retain performance history, recurring weaknesses and improvement areas."},
        {"id": "UR11", "name": "Consistent evaluation", "desc": "Ground feedback in clearly defined criteria/rubrics."},
        {"id": "UR12", "name": "Self-directed practice", "desc": "Make the complete flow usable without a human interviewer."}
    ]
}
