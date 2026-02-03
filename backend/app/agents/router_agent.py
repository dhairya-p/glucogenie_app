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
    MEAL_SUGGESTIONS = "meal_suggestions"


class RouterState(BaseModel):
    """Typed input state for the Router Agent."""

    patient: PatientContext
    user_message: str

    model_config = ConfigDict(extra="ignore")


class RouterDecision(BaseModel):
    """Structured output from the Router Agent."""

    intent: Intent
    rationale: str
    target_agent: Literal[
        "clinical_safety",
        "lifestyle_analyst",
        "cultural_dietitian",
        "unmatched",
    ]

    model_config = ConfigDict(extra="ignore")


def _build_routing_prompt(patient: PatientContext) -> str:
    """Build the system prompt for LLM-based intent classification.

    Args:
        patient: Patient context for personalized routing

    Returns:
        System prompt for intent classification
    """
    prompt = """You are an intelligent routing agent for a diabetes management application. Your task is to classify the user's query into one of three intents, and then choose the most appropriate specialist agent.

**Intent Categories:**

1. **MEDICAL** (clinical_safety agent):
   - Medication safety, side effects, drug interactions, contraindications
   - Dosage questions, prescription advice, medication risks
   - Clinical warnings, precautions, adverse reactions
   - Questions about what to avoid or be wary of with medications or conditions
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
     * "What foods or drugs should I avoid?"
     * "What should I be wary/mindful of with my medications?"

2. **LIFESTYLE** (lifestyle_analyst agent):
   - Glucose tracking, blood sugar trends, readings analysis
   - Meal logging, food intake, carbohydrate tracking, diet patterns
   - Exercise tracking, activity logs, physical activity
   - Weight tracking, BMI, health metrics
   - Medication adherence tracking (did I take my meds, logging history)
   - Recent logs, historical data analysis, patterns, trends
   - Examples (lifestyle_analyst):
     * "What was my average glucose this week?"
     * "Show me my recent meals"
     * "Did I take my medication today?"
     * "What's my glucose trend over the past month?"
     * "Have I been exercising regularly?"
     * "What medications did I log recently?"
     * "How is my diabetes management?"

3. **MEAL_SUGGESTIONS** (cultural_dietitian agent):
   - Singapore-specific meal suggestions and recommendations
   - Culturally appropriate meals based on ethnicity, location, and diabetes
   - Questions like:
     * "Give me meal suggestions for diabetes-friendly Singaporean food."
     * "What should I eat for breakfast as a Malay patient in Singapore?"
     * "What can I cook this week that fits my diabetes diet?"

**Classification Rules:**

- **Safety First**: If there's ANY mention of medication safety, side effects, interactions, or dosage changes → MEDICAL
- **Clinical Guidelines**: Any query about clinical guidelines, recommendations, protocols, standards (MOH, ADA, WHO, medical societies) → MEDICAL
- **Tracking vs Safety**: Distinguish between:
  * Medication SAFETY questions (side effects, interactions) → MEDICAL
  * Medication TRACKING questions (did I take it, when did I take it) → LIFESTYLE
- **Data Analysis**: Questions about logs, trends, patterns, history, recent data → LIFESTYLE
- **Avoidance/Safety**: Any question about "avoid", "wary", "mindful", "safe", "interaction" → MEDICAL
- **General Management**: Broad questions about overall diabetes management without safety/interaction terms → LIFESTYLE

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
    "intent": "medical" | "lifestyle" | "meal_suggestions",
    "rationale": "Brief explanation of why this intent was chosen (1-2 sentences)",
    "target_agent": "clinical_safety" | "lifestyle_analyst" | "cultural_dietitian" | "unmatched"
}

**Important Notes:**
- If the query does not clearly fit into MEDICAL or LIFESTYLE categories, use "unmatched" as target_agent
- Only route to clinical_safety, lifestyle_analyst, or cultural_dietitian if the query is clearly related to diabetes management
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
    - MEAL_SUGGESTIONS: Culturally appropriate meal recommendations and what to eat/cook
    - UNMATCHED: Queries that don't fit these categories (general conversation, unrelated topics)

    Returns:
        RouterDecision with intent, rationale, and target_agent (or "unmatched" if query doesn't fit)
    """

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OPENAI_API_KEY not found; routing to unmatched")
        return RouterDecision(
            intent=Intent.MEDICAL,
            rationale="Router unavailable (missing OPENAI_API_KEY).",
            target_agent="unmatched",
        ).model_dump()

    system_prompt = _build_routing_prompt(state.patient)
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.0,  # Deterministic routing
        max_tokens=200,
        api_key=openai_api_key,
    )
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User query: {state.user_message}"),
    ]

    logger.info("Routing query with LLM: %s...", state.user_message[:100])
    response = llm.invoke(messages)
    response_text = response.content.strip()
    logger.debug("LLM routing response: %s", response_text)

    json_start = response_text.find("{")
    json_end = response_text.rfind("}") + 1
    if json_start < 0 or json_end <= json_start:
        logger.warning("No JSON found in LLM routing response; routing to unmatched")
        return RouterDecision(
            intent=Intent.MEDICAL,
            rationale="Router returned non-JSON output.",
            target_agent="unmatched",
        ).model_dump()

    result_dict = json.loads(response_text[json_start:json_end])
    if result_dict.get("target_agent") == "chitchat":
        result_dict["target_agent"] = "unmatched"
    decision = RouterDecision(**result_dict)
    logger.info("Routed to %s: %s", decision.target_agent, decision.rationale)
    return decision.model_dump()


