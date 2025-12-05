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

    The decision is based on simple keyword heuristics for now.
    In production this would typically be delegated to an LLM.
    """

    text = state.user_message.lower()

    # Medical intent: medication-related queries
    medical_keywords = ["dose", "medication", "drug", "side effect", "prescription", "take medicine"]
    if any(keyword in text for keyword in medical_keywords):
        decision = RouterDecision(
            intent=Intent.MEDICAL,
            rationale="User asked about medications / side effects.",
            target_agent="clinical_safety",
        )
    # Lifestyle intent: glucose logs, meals, activity, food patterns
    elif any(keyword in text for keyword in [
        "glucose", "blood sugar", "sugar level", "reading", "readings", 
        "log", "logs", "level", "levels", "measurement", "measurements",
        "exercise", "walk", "walking", "activity", "activities",
        "meal", "meals", "food", "diet", "eating", "carb", "carbs",
        "breakfast", "lunch", "dinner", "snack", "pattern", "patterns",
        "average", "trend", "trends", "history", "recent", "health"
    ]):
        decision = RouterDecision(
            intent=Intent.LIFESTYLE,
            rationale="User asked about glucose logs, meals, or activity patterns.",
            target_agent="lifestyle_analyst",
        )
    else:
        decision = RouterDecision(
            intent=Intent.CHITCHAT,
            rationale="No explicit medical or lifestyle intent detected.",
            target_agent="chitchat",
        )

    return decision.model_dump()


