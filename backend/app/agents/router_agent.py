from __future__ import annotations

import json
import logging
import os
from typing import Literal

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from pydantic.config import ConfigDict

from app.schemas.patient_context import PatientContext

logger = logging.getLogger(__name__)

# Single naming scheme for routing - used everywhere
TARGET_AGENT_LITERAL = Literal[
    "clinical_safety",
    "lifestyle_analyst",
    "cultural_dietitian",
    "unmatched",
]


class RouterState(BaseModel):
    """Typed input state for the Router Agent."""

    patient: PatientContext
    user_message: str

    model_config = ConfigDict(extra="ignore")


class RouterDecision(BaseModel):
    """Structured output from the Router Agent. Uses target_agent as the single routing field."""

    target_agent: TARGET_AGENT_LITERAL
    rationale: str

    model_config = ConfigDict(extra="ignore")


def _build_routing_prompt(patient: PatientContext) -> str:
    """Build the system prompt for LLM-based agent routing.

    Args:
        patient: Patient context for personalized routing

    Returns:
        System prompt for target agent classification
    """
    prompt = """You are an intelligent routing agent for a diabetes management application. Your task is to classify the user's query and choose the most appropriate specialist agent.

**Target Agents (use EXACTLY these values):**

1. **clinical_safety**:
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

2. **lifestyle_analyst**:
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
     * "How is my diabetes management?"

3. **cultural_dietitian**:
   - Singapore-specific meal suggestions and recommendations
   - Culturally appropriate meals based on ethnicity, location, and diabetes
   - Portion size, serving size, carb portions, and plate balance questions
   - Questions like:
     * "Give me meal suggestions for diabetes-friendly Singaporean food."
     * "What should I eat for breakfast as a Malay patient in Singapore?"
     * "What can I cook this week that fits my diabetes diet?"
     * "How much rice should I eat per meal?"
     * "What is a good portion size for noodles?"

**Classification Rules:**

- **Safety First**: If there's ANY mention of medication safety, side effects, interactions, or dosage changes → clinical_safety
- **Clinical Guidelines**: Any query about clinical guidelines, recommendations, protocols, standards (MOH, ADA, WHO, medical societies) → clinical_safety
- **Tracking vs Safety**: Distinguish between:
  * Medication SAFETY questions (side effects, interactions) → clinical_safety
  * Medication TRACKING questions (did I take it, when did I take it) → lifestyle_analyst
- **Data Analysis**: Questions about logs, trends, patterns, history, recent data → lifestyle_analyst
- **Avoidance/Safety**: Any question about "avoid", "wary", "mindful", "safe", "interaction" → clinical_safety
- **General Management**: Broad questions about overall diabetes management without safety/interaction terms → lifestyle_analyst
- **Portion Size**: Any question about portion size, serving size, or carb portions → cultural_dietitian
- **Recipes/Cooking**: Requests for recipes, cooking instructions, or how-to-cook → unmatched

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
    "target_agent": "clinical_safety" | "lifestyle_analyst" | "cultural_dietitian" | "unmatched",
    "rationale": "Brief explanation of why this agent was chosen (1-2 sentences)"
}

**Important Notes:**
- Use EXACTLY one of: clinical_safety, lifestyle_analyst, cultural_dietitian, unmatched
- If the query does not clearly fit, use target_agent "unmatched"
- Only route to a specialist if the query is clearly related to diabetes management
- General conversation, greetings, or unrelated queries → unmatched

**Important:**
- Respond ONLY with valid JSON, no additional text
- Be precise in your classification
- Consider patient context when making decisions
- Prioritize safety for medication-related queries
"""

    return prompt


@tool("route_intent", return_direct=False)
def route_intent(state: RouterState) -> dict:
    """Route user query to the appropriate specialist agent using LLM-based classification.

    Uses GPT-4o-mini to classify queries based on:
    - User question content
    - Patient context (medications, conditions, demographics)
    - Safety-first approach for medication queries

    Target agents:
    - clinical_safety: Medication safety, side effects, interactions, dosage, clinical guidelines
    - lifestyle_analyst: Glucose tracking, meal logs, activity patterns, adherence tracking
    - cultural_dietitian: Singapore-specific meal recommendations, portion sizes
    - unmatched: General conversation, greetings, or unrelated topics

    Returns:
        Dict with target_agent and rationale
    """

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OPENAI_API_KEY not found; routing to unmatched")
        return RouterDecision(
            target_agent="unmatched",
            rationale="Router unavailable (missing OPENAI_API_KEY).",
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
            target_agent="unmatched",
            rationale="Router returned non-JSON output.",
        ).model_dump()

    result_dict = json.loads(response_text[json_start:json_end])

    # Normalize target_agent: map common LLM mistakes to valid values
    raw_agent = result_dict.get("target_agent") or result_dict.get("intent")
    if raw_agent:
        raw_agent = str(raw_agent).strip().lower()
        # Map old intent-style values to target_agent
        agent_map = {
            "medical": "clinical_safety",
            "lifestyle": "lifestyle_analyst",
            "meal_suggestions": "cultural_dietitian",
            "chitchat": "unmatched",
            "general": "unmatched",
            "other": "unmatched",
            "none": "unmatched",
        }
        result_dict["target_agent"] = agent_map.get(raw_agent, raw_agent)
    # Ensure we have target_agent and rationale
    if "rationale" not in result_dict:
        result_dict["rationale"] = "No rationale provided."

    try:
        decision = RouterDecision(**result_dict)
    except Exception as exc:
        logger.warning("RouterDecision validation failed: %s; routing to unmatched", exc)
        return RouterDecision(
            target_agent="unmatched",
            rationale="Router output validation failed.",
        ).model_dump()
    logger.info("Routed to %s: %s", decision.target_agent, decision.rationale)
    return decision.model_dump()


