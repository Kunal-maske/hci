from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Literal, Optional, Dict, Any


class RubricCriterion(BaseModel):
    name: str
    score: float
    max_score: float = 10.0
    status: str  # "Good", "Adequate", "Needs Improvement"
    reason: str
    evidence_found: Optional[str] = None
    missing_aspect: Optional[str] = None
    rubric_definition: str


class EvaluationResult(BaseModel):
    overall_score: float
    relevance: RubricCriterion
    specificity: RubricCriterion
    evidence_outcome: RubricCriterion
    structure_clarity: RubricCriterion
    strengths: List[str]
    needs_improvement: List[str]
    actionable_suggestions: List[str]
    example_improved_answer: Optional[str] = None
    why_feedback_summary: Dict[str, Any] = {}


class SessionSetupRequest(BaseModel):
    prototype_type: str = "A"  # "A" (Immediate/Learning) or "B" (Full Simulation/Realism)
    candidate_name: Optional[str] = "Candidate"
    job_role: str = "Software Engineer"
    target_company: Optional[str] = ""
    experience_level: Optional[str] = "Mid-Level"
    interview_type: str = "Behavioral"
    difficulty: str = "Medium"
    cv_text: Optional[str] = ""
    job_description: Optional[str] = ""
    persona_id: Optional[str] = "custom"


class AnswerSubmitRequest(BaseModel):
    session_id: str
    question_id: int
    question_text: str
    answer_text: str
    attempt_number: int = 1


class ReflectionSubmitRequest(BaseModel):
    session_id: str
    question_id: int
    what_would_you_change: str
    what_did_you_learn: str


class FollowUpRequest(BaseModel):
    session_id: str
    question_id: int
    previous_question: str
    user_answer: str
    job_role: str


class InterviewTurnRequest(BaseModel):
    session_id: str
    user_message: str
    turn_index: int = 1
    job_role: Optional[str] = "Software Engineer"
    conversation_history: Optional[List[Dict[str, str]]] = []


class AttemptComparison(BaseModel):
    question_id: int
    question_text: str
    attempt1_answer: str
    attempt2_answer: str
    attempt1_scores: Dict[str, float]
    attempt2_scores: Dict[str, float]
    deltas: Dict[str, float]
    improvements: List[str]
    focus_areas_remaining: List[str]


class ConfigUpdateRequest(BaseModel):
    openrouter_api_key: Optional[str] = None
    openrouter_model: Optional[str] = "nvidia/nemotron-3.5-super-vl:free"
    gemini_api_key: Optional[str] = None
    voice_speed: Optional[float] = 1.0
    auto_speak: Optional[bool] = True


class UserEvaluationSubmission(BaseModel):
    participant_id: str = Field(min_length=1, max_length=32)
    target_role: str = Field(min_length=1, max_length=120)
    prototype_tested: Literal["A", "B", "Both"]
    task_completed: bool
    task_time_seconds: int = Field(ge=0)
    sus_scores: List[int] = Field(min_length=10, max_length=10)
    sus_total_score: float
    feedback_realism: str
    feedback_learning: str
    ethical_consent_signed: bool

    @field_validator("sus_scores")
    @classmethod
    def validate_sus_scores(cls, scores: List[int]) -> List[int]:
        if any(score < 1 or score > 5 for score in scores):
            raise ValueError("SUS responses must be between 1 and 5.")
        return scores

    @model_validator(mode="after")
    def validate_sus_total(self):
        odd_sum = sum(self.sus_scores[index] - 1 for index in range(0, 10, 2))
        even_sum = sum(5 - self.sus_scores[index] for index in range(1, 10, 2))
        expected_score = (odd_sum + even_sum) * 2.5
        if abs(self.sus_total_score - expected_score) > 0.1:
            raise ValueError("SUS total does not match the individual responses.")
        return self
