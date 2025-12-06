from __future__ import annotations

from enum import Enum
from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel
from pydantic.config import ConfigDict

from app.schemas.patient_context import PatientContext


class Intent(str, Enum):
    """High-level intents that the Router Agent can choose."""

    MEDICAL = "medical"
    LIFESTYLE = "lifestyle"
    CHITCHAT = "chitchat"


class RouterState(BaseModel):
    """Typed input state for the Router Agent."""

    patient: PatientContext
    user_message: str

    model_config = ConfigDict(extra="ignore")


class RouterDecision(BaseModel):
    """Structured output from the Router Agent."""

    intent: Intent
    rationale: str
    target_agent: Literal["clinical_safety", "lifestyle_analyst", "chitchat"]

    model_config = ConfigDict(extra="ignore")


@tool("route_intent", return_direct=False)
def route_intent(state: RouterState) -> dict:
    """Decide whether a query is Medical, Lifestyle, or ChitChat.

    The decision is based on keyword heuristics that differentiate between:
    - Medical/Safety queries: side effects, interactions, safety, dosage changes
      Examples: "Can I take metformin with insulin?", "What are the side effects?", 
                "Is it safe to skip a dose?", "Should I increase my medication dose?"
    
    - Lifestyle/Tracking queries: adherence, logging history, recent medications taken
      Examples: "Did I take my medication today?", "What medications did I log recently?",
                "Have I been taking my meds regularly?", "When did I last take insulin?"
    
    In production this would typically be delegated to an LLM for better accuracy.
    """

    text = state.user_message.lower()

    # Medical/Safety intent: medication safety, side effects, interactions, dosage questions
    # These require clinical safety agent for safety checks
    # Examples: "side effects of metformin", "can I take X with Y", "is it safe to...", "should I increase dose"
    medical_safety_keywords = [
        "side effect", "side effects", "adverse", "reaction", "interaction", "interactions",
        "safe to take", "can i take", "should i take", "is it safe", "is safe",
        "dose", "dosage", "increase dose", "decrease dose", "change dose", "adjust dose",
        "overdose", "double dose", "extra dose", "missed dose", "skip dose",
        "contraindication", "contraindicated", "warning", "warnings", "precaution",
        "harmful", "dangerous", "risk", "risky", "compatible", "incompatible",
        "prescription", "prescribed", "doctor said", "doctor told", "healthcare provider"
    ]
    
    # Lifestyle/Tracking intent: medication adherence, logging, history, recent medications
    # These require lifestyle analyst for data analysis
    # Examples: "did I take my medication", "what medications did I log", "have I been taking regularly"
    lifestyle_tracking_keywords = [
        "did i take", "have i taken", "when did i take", "when did i log",
        "recent medication", "recent med", "medication log", "med logs",
        "medication history", "med history", "taking regularly", "taking consistently",
        "adherence", "compliance", "missed", "forgot", "remember",
        "what medication", "which medication", "medications i", "meds i",
        "logged medication", "logged med", "took medication", "took med",
        "took medicine", "took insulin", "taken medicine", "taken insulin"
    ]
    
    # Check for medical/safety intent FIRST (higher priority for safety)
    if any(keyword in text for keyword in medical_safety_keywords):
        decision = RouterDecision(
            intent=Intent.MEDICAL,
            rationale="User asked about medication safety, side effects, interactions, or dosage changes. Requires clinical safety agent.",
            target_agent="clinical_safety",
        )
    # Check for lifestyle/tracking intent (medication adherence, logging history)
    elif any(keyword in text for keyword in lifestyle_tracking_keywords):
        decision = RouterDecision(
            intent=Intent.LIFESTYLE,
            rationale="User asked about medication adherence, logging history, or recent medications taken. Requires lifestyle analyst for data analysis.",
            target_agent="lifestyle_analyst",
        )
    # General lifestyle intent: glucose logs, meals, activity, food patterns
    elif any(keyword in text for keyword in [
        "glucose", "blood sugar", "sugar level", "reading", "readings", 
        "log", "logs", "level", "levels", "measurement", "measurements",
        "exercise", "walk", "walking", "activity", "activities",
        "meal", "meals", "food", "diet", "eating", "carb", "carbs",
        "breakfast", "lunch", "dinner", "snack", "pattern", "patterns",
        "average", "trend", "trends", "history", "recent", "health", "BMI", "weight", "bmi", "height"
    ]):
        decision = RouterDecision(
            intent=Intent.LIFESTYLE,
            rationale="User asked about glucose logs, meals, or activity patterns.",
            target_agent="lifestyle_analyst",
        )
    # Fallback: if query contains "medication" or "med" but doesn't match above patterns,
    # check context to determine intent
    elif "medication" in text or "med " in text or " medicine" in text:
        # If asking about "my medication" or "medications" in general, check for safety vs tracking
        if any(phrase in text for phrase in ["my medication", "my med", "medications i", "meds i"]):
            # Likely tracking/adherence question
            decision = RouterDecision(
                intent=Intent.LIFESTYLE,
                rationale="User asked about their medications (likely tracking/adherence). Requires lifestyle analyst.",
                target_agent="lifestyle_analyst",
            )
        else:
            # Default to clinical safety for ambiguous medication queries (safer default)
            decision = RouterDecision(
                intent=Intent.MEDICAL,
                rationale="Ambiguous medication query - defaulting to clinical safety agent for safety.",
                target_agent="clinical_safety",
            )
    else:
        decision = RouterDecision(
            intent=Intent.CHITCHAT,
            rationale="No explicit medical or lifestyle intent detected.",
            target_agent="chitchat",
        )

    return decision.model_dump()


