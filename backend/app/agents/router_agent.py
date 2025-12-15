from __future__ import annotations

import json
import logging
import os
from enum import Enum
from typing import Literal

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from pydantic.config import ConfigDict

from app.schemas.patient_context import PatientContext

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    """High-level intents that the Router Agent can choose."""

    MEDICAL = "medical"
    LIFESTYLE = "lifestyle"


class RouterState(BaseModel):
    """Typed input state for the Router Agent."""

    patient: PatientContext
    user_message: str

    model_config = ConfigDict(extra="ignore")


class RouterDecision(BaseModel):
    """Structured output from the Router Agent."""

    intent: Intent
    rationale: str
    target_agent: Literal["clinical_safety", "lifestyle_analyst", "unmatched"]

    model_config = ConfigDict(extra="ignore")


def _build_routing_prompt(patient: PatientContext) -> str:
    """Build the system prompt for LLM-based intent classification.

    Args:
        patient: Patient context for personalized routing

    Returns:
        System prompt for intent classification
    """
    prompt = """You are an intelligent routing agent for a diabetes management application. Your task is to classify the user's query into one of three intents:

**Intent Categories:**

1. **MEDICAL** (clinical_safety agent):
   - Medication safety, side effects, drug interactions, contraindications
   - Dosage questions, prescription advice, medication risks
   - Clinical warnings, precautions, adverse reactions
   - Questions about medication compatibility, safety concerns
   - Clinical guidelines and recommendations (MOH, ADA, WHO, medical standards)
   - Evidence-based medical protocols and best practices
   - Examples:
     * "Can I take metformin with insulin?"
     * "What are the side effects of my diabetes medication?"
     * "Is it safe to skip a dose?"
     * "Should I increase my medication dose?"
     * "Are there any interactions between my medications?"
     * "What do MOH guidelines say about diabetes management?"
     * "What are the ADA recommendations for blood sugar control?"
     * "Show me clinical guidelines for my medications"

2. **LIFESTYLE** (lifestyle_analyst agent):
   - Glucose tracking, blood sugar trends, readings analysis
   - Meal logging, food intake, carbohydrate tracking, diet patterns
   - Exercise tracking, activity logs, physical activity
   - Weight tracking, BMI, health metrics
   - Medication adherence tracking (did I take my meds, logging history)
   - Recent logs, historical data analysis, patterns, trends
   - Examples:
     * "What was my average glucose this week?"
     * "Show me my recent meals"
     * "Did I take my medication today?"
     * "What's my glucose trend over the past month?"
     * "Have I been exercising regularly?"
     * "What medications did I log recently?"

**Classification Rules:**

- **Safety First**: If there's ANY mention of medication safety, side effects, interactions, or dosage changes → MEDICAL
- **Clinical Guidelines**: Any query about clinical guidelines, recommendations, protocols, standards (MOH, ADA, WHO, medical societies) → MEDICAL
- **Tracking vs Safety**: Distinguish between:
  * Medication SAFETY questions (side effects, interactions) → MEDICAL
  * Medication TRACKING questions (did I take it, when did I take it) → LIFESTYLE
- **Data Analysis**: Questions about logs, trends, patterns, history, recent data → LIFESTYLE
- **Default to Safety**: When ambiguous and involves medications or clinical advice → MEDICAL (safer default)

**Patient Context:**"""

    # Add patient context
    if patient:
        if patient.first_name and patient.last_name:
            prompt += f"\n- Name: {patient.first_name} {patient.last_name}"
        if patient.age:
            prompt += f"\n- Age: {patient.age}"
        if patient.sex:
            prompt += f"\n- Sex: {patient.sex}"
        if patient.ethnicity:
            prompt += f"\n- Ethnicity: {patient.ethnicity}"
        if patient.conditions:
            prompt += f"\n- Medical Conditions: {', '.join(patient.conditions)}"
        if patient.medications:
            # Medications is a list of strings, not objects
            prompt += f"\n- Current Medications: {', '.join(patient.medications)}"

    prompt += """

**Output Format (JSON):**
{
    "intent": "medical" | "lifestyle",
    "rationale": "Brief explanation of why this intent was chosen (1-2 sentences)",
    "target_agent": "clinical_safety" | "lifestyle_analyst" | "unmatched"
}

**Important Notes:**
- If the query does not clearly fit into MEDICAL or LIFESTYLE categories, use "unmatched" as target_agent
- Only route to clinical_safety or lifestyle_analyst if the query is clearly related to diabetes management
- General conversation, greetings, or unrelated queries should be marked as "unmatched"

**Important:**
- Respond ONLY with valid JSON, no additional text
- Be precise in your classification
- Consider patient context when making decisions
- Prioritize safety for medication-related queries
"""

    return prompt


@tool("route_intent", return_direct=False)
def route_intent(state: RouterState) -> dict:
    """Decide whether a query is Medical or Lifestyle using LLM-based classification.

    This function uses an LLM (GPT-4o-mini) to intelligently classify user queries based on:
    - Intent analysis of the user's question
    - Patient context (medications, conditions, demographics)
    - Safety-first approach for medication queries

    Intent categories:
    - MEDICAL: Medication safety, side effects, interactions, dosage questions, clinical guidelines
    - LIFESTYLE: Glucose tracking, meal logs, activity patterns, adherence tracking
    - UNMATCHED: Queries that don't fit medical or lifestyle categories (general conversation, unrelated topics)

    Returns:
        RouterDecision with intent, rationale, and target_agent (or "unmatched" if query doesn't fit)
    """

    try:
        # Get OpenAI API key
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.warning("OPENAI_API_KEY not found, falling back to keyword-based routing")
            return _fallback_keyword_routing(state)

        # Build system prompt with patient context
        system_prompt = _build_routing_prompt(state.patient)

        # Initialize LLM
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.0,  # Deterministic routing
            max_tokens=200,
            api_key=openai_api_key,
        )

        # Create messages
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"User query: {state.user_message}"),
        ]

        logger.info(f"Routing query with LLM: {state.user_message[:100]}...")

        # Call LLM
        response = llm.invoke(messages)
        response_text = response.content.strip()

        logger.debug(f"LLM routing response: {response_text}")

        # Parse JSON response
        try:
            # Extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                result_dict = json.loads(json_str)

                # Convert legacy "chitchat" to "unmatched"
                if result_dict.get("target_agent") == "chitchat":
                    result_dict["target_agent"] = "unmatched"
                    logger.info("Converted legacy 'chitchat' to 'unmatched'")
                
                # Validate and create RouterDecision
                decision = RouterDecision(**result_dict)
                logger.info(f"Routed to {decision.target_agent}: {decision.rationale}")
                return decision.model_dump()
            else:
                raise ValueError("No JSON found in LLM response")

        except ValueError as exc:
            logger.warning(f"Failed to parse LLM response as JSON: {exc}. Falling back to keyword routing.")
            return _fallback_keyword_routing(state)

    except Exception as exc:
        logger.error(f"Error in LLM-based routing: {exc}. Falling back to keyword routing.", exc_info=True)
        return _fallback_keyword_routing(state)


def _fallback_keyword_routing(state: RouterState) -> dict:
    """Fallback keyword-based routing when LLM is unavailable.

    This is the original keyword-based implementation, used as a backup.
    """
    text = state.user_message.lower()

    # Medical/Safety intent: medication safety, side effects, interactions, dosage questions, clinical guidelines
    medical_safety_keywords = [
        # Safety and side effects
        "side effect", "side effects", "adverse", "reaction", "interaction", "interactions",
        "safe to take", "can i take", "should i take", "is it safe", "is safe",
        # Dosage
        "dose", "dosage", "increase dose", "decrease dose", "change dose", "adjust dose",
        "overdose", "double dose", "extra dose", "missed dose", "skip dose",
        # Clinical warnings
        "contraindication", "contraindicated", "warning", "warnings", "precaution",
        "harmful", "dangerous", "risk", "risky", "compatible", "incompatible",
        "prescription", "prescribed", "doctor said", "doctor told", "healthcare provider",
        # Clinical guidelines and standards
        "guideline", "guidelines", "recommendation", "recommendations", "protocol", "protocols",
        "MOH", "ministry of health", "ADA", "american diabetes", "WHO", "world health",
        "clinical standard", "medical standard", "best practice", "evidence-based",
        "medical guideline", "treatment guideline", "diabetes guideline", "clinical protocol"
    ]

    # Lifestyle/Tracking intent: medication adherence, logging, history, recent medications
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
    # Fallback: if query contains "medication" or "med" but doesn't match above patterns
    elif "medication" in text or "med " in text or " medicine" in text:
        if any(phrase in text for phrase in ["my medication", "my med", "medications i", "meds i"]):
            decision = RouterDecision(
                intent=Intent.LIFESTYLE,
                rationale="User asked about their medications (likely tracking/adherence). Requires lifestyle analyst.",
                target_agent="lifestyle_analyst",
            )
        else:
            decision = RouterDecision(
                intent=Intent.MEDICAL,
                rationale="Ambiguous medication query - defaulting to clinical safety agent for safety.",
                target_agent="clinical_safety",
            )
    else:
        decision = RouterDecision(
            intent=Intent.MEDICAL,  # Use MEDICAL as default enum value, but target_agent is "unmatched"
            rationale="Query does not clearly fit medical or lifestyle categories.",
            target_agent="unmatched",
        )

    logger.info(f"Keyword routing fallback: {decision.target_agent}")
    return decision.model_dump()


