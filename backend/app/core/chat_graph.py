from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from supabase import Client, create_client

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    # Load .env from backend directory (3 levels up from this file)
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    # python-dotenv not available, rely on environment variables being set
    pass

from app.agents.clinical_safety_agent import ClinicalSafetyState, check_clinical_safety
from app.agents.cultural_dietitian_agent import CulturalDietitianState, analyze_food_image
from app.agents.lifestyle_analyst_agent import LifestyleState, analyze_lifestyle
from app.agents.router_agent import RouterState, route_intent
from app.schemas.patient_context import PatientContext

logger = logging.getLogger(__name__)


def _get_supabase_client() -> Client:
    """Get Supabase client from environment variables."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Supabase URL or key not configured in environment.")
    return create_client(url, key)


def _extract_patient_context(user_id: str) -> PatientContext:
    """Fetch patient context from Supabase for a given user_id."""
    supabase = _get_supabase_client()

    # Fetch profile with all relevant fields
    profile_resp = (
        supabase.table("profiles")
        .select("first_name, last_name, age, sex, ethnicity, activity_level")
        .eq("id", user_id)
        .execute()
        .data
    )
    profile = profile_resp[0] if profile_resp else {}
    first_name = profile.get("first_name")
    last_name = profile.get("last_name")
    age = profile.get("age", 30)
    sex = profile.get("sex")
    ethnicity = profile.get("ethnicity", "Unknown")
    activity_level = profile.get("activity_level")

    # Fetch conditions
    conditions_resp = (
        supabase.table("conditions")
        .select("condition_name")
        .eq("user_id", user_id)
        .execute()
        .data
        or []
    )
    conditions = [c.get("condition_name") for c in conditions_resp if c.get("condition_name")]

    # Fetch medications
    meds_resp = (
        supabase.table("medications")
        .select("medication_name")
        .eq("user_id", user_id)
        .execute()
        .data
        or []
    )
    medications = [m.get("medication_name") for m in meds_resp if m.get("medication_name")]

    return PatientContext(
        first_name=first_name,
        last_name=last_name,
        age=age,
        sex=sex,
        ethnicity=ethnicity,
        activity_level=activity_level,
        conditions=conditions,
        medications=medications,
    )


def _route_and_process(input_data: dict[str, Any]) -> dict[str, Any]:
    """Main routing logic: determine intent and call the appropriate agent."""

    messages = input_data.get("messages", [])
    user_id = input_data.get("user_id", "")

    logger.info("_route_and_process called with user_id: %s, messages count: %d", user_id, len(messages))

    if not messages:
        return {"output": "No messages provided."}

    if not user_id:
        logger.warning("No user_id provided, cannot fetch patient context or logs")
        return {"output": "I'm here to help with your diabetes management. Ask me about your glucose logs, meals, or activity patterns!"}

    # Extract the latest user message
    last_message = messages[-1]
    user_text = last_message.get("content", "") if isinstance(last_message, dict) else str(last_message)
    logger.info("Processing user message: %s", user_text[:100])  # Log first 100 chars

    # Get patient context
    try:
        logger.info("Fetching patient context for user_id: %s", user_id)
        patient = _extract_patient_context(user_id)
        logger.info("Patient context fetched: name=%s, age=%d, sex=%s, ethnicity=%s, activity_level=%s, conditions=%s, medications=%s", 
                   patient.full_name, patient.age, patient.sex, patient.ethnicity, patient.activity_level, patient.conditions, patient.medications)
    except Exception as exc:
        logger.error("Failed to fetch patient context: %s", exc, exc_info=True)
        patient = PatientContext(age=30, ethnicity="Unknown", conditions=[], medications=None)

    # Route intent
    try:
        router_state = RouterState(patient=patient, user_message=user_text)
        routing_result = route_intent.invoke({"state": router_state})
        target_agent = routing_result.get("target_agent", "chitchat")
        logger.info("Router selected target_agent: %s", target_agent)
    except Exception as exc:
        logger.error("Error in router: %s", exc, exc_info=True)
        target_agent = "chitchat"

    # Call the appropriate agent
    try:
        if target_agent == "clinical_safety":
            logger.info("Calling clinical_safety agent")
            safety_state = ClinicalSafetyState(patient=patient, user_message=user_text)
            result = check_clinical_safety.invoke({"state": safety_state})
            output = f"Safety check: {result.get('rationale', '')}. Warnings: {result.get('warnings', [])}"
        elif target_agent == "lifestyle_analyst":
            logger.info("Calling lifestyle_analyst agent for user_id: %s", user_id)
            lifestyle_state = LifestyleState(patient=patient, user_id=user_id, days=7)
            result = analyze_lifestyle.invoke({"state": lifestyle_state})
            insights = result.get("insights", [])
            logger.info("Lifestyle analyst returned %d insights", len(insights))
            insight_texts = [f"{i.get('title', '')}: {i.get('detail', '')}" for i in insights]
            output = "\n".join(insight_texts) if insight_texts else "No lifestyle insights available."
            logger.info("Lifestyle analyst output: %s", output[:200])  # Log first 200 chars
        elif target_agent == "cultural_dietitian":
            logger.info("Calling cultural_dietitian agent")
            dietitian_state = CulturalDietitianState(patient=patient)
            result = analyze_food_image.invoke({"state": dietitian_state})
            output = result.get("summary", "Food analysis not available.")
        else:
            # Chitchat: use LLM directly
            logger.info("Using chitchat (no agent)")
            output = "I'm here to help with your diabetes management. Ask me about your glucose logs, meals, or activity patterns!"
    except Exception as exc:
        logger.error("Error calling agent %s: %s", target_agent, exc, exc_info=True)
        output = f"Error processing request: {str(exc)}"

    logger.info("_route_and_process returning output: %s", output[:200])  # Log first 200 chars
    return {"output": output}


def get_chat_runnable() -> Any:
    """Create and return a LangChain Runnable that processes chat messages.

    This runnable:
    1. Accepts messages + user_id
    2. Routes to the appropriate agent (Router -> Specialist Agent)
    3. Returns structured output that can be streamed via astream_events
    """

    # Initialize LLM for streaming responses
    # Get OpenAI API key from environment
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not found in environment variables. "
            "Please set it in your .env file."
        )

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        streaming=True,
        api_key=openai_api_key,
    )

    def prepare_messages(input_dict: dict[str, Any]) -> list:
        """Prepare messages with agent context and return as list for LLM."""
        messages = input_dict.get("messages", [])
        user_id = input_dict.get("user_id", "")

        # Convert messages to LangChain format
        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user") if isinstance(msg, dict) else "user"
            content = msg.get("content", str(msg)) if isinstance(msg, dict) else str(msg)

            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))

        # Get patient context for system prompt
        patient_context_str = ""
        try:
            patient = _extract_patient_context(user_id)
            context_parts = []
            if patient.full_name and patient.full_name != "there":
                context_parts.append(f"Name: {patient.full_name}")
            if patient.age:
                context_parts.append(f"Age: {patient.age}")
            if patient.sex:
                context_parts.append(f"Sex: {patient.sex}")
            if patient.ethnicity and patient.ethnicity != "Unknown":
                context_parts.append(f"Ethnicity: {patient.ethnicity}")
            if patient.activity_level:
                context_parts.append(f"Activity Level: {patient.activity_level}")
            if patient.conditions:
                context_parts.append(f"Medical Conditions: {', '.join(patient.conditions)}")
            if patient.medications:
                context_parts.append(f"Medications: {', '.join(patient.medications)}")
            
            if context_parts:
                patient_context_str = "\n".join(context_parts)
        except Exception as exc:
            logger.error("Error fetching patient context for system prompt: %s", exc)

        # Get agent output (this runs synchronously but quickly)
        try:
            agent_output = _route_and_process({"messages": messages, "user_id": user_id})
            agent_text = agent_output.get("output", "")

            # Build system prompt with patient context
            system_prompt_parts = [
                "You are a helpful diabetes management assistant.",
            ]
            
            if patient_context_str:
                system_prompt_parts.append(f"\nPatient Information:\n{patient_context_str}\n")
            
            # If we have agent output, use it as context for the LLM
            if agent_text and not agent_text.startswith("I'm here to help"):
                system_prompt_parts.append(
                    f"Use the following agent analysis to provide a clear, empathetic response to the user.\n"
                    f"Agent Analysis: {agent_text}\n\n"
                    "Respond naturally and conversationally based on this analysis."
                )
            else:
                system_prompt_parts.append(
                    "Help users with questions about their glucose logs, meals, activity, and general diabetes management."
                )
            
            system_prompt = "\n".join(system_prompt_parts)
            lc_messages.insert(0, SystemMessage(content=system_prompt))
        except Exception as exc:
            logger.error("Error in agent routing: %s", exc)
            # Fallback system prompt with patient context
            fallback_prompt = "You are a helpful diabetes management assistant. Respond to the user's question."
            if patient_context_str:
                fallback_prompt = f"You are a helpful diabetes management assistant.\n\nPatient Information:\n{patient_context_str}\n\nRespond to the user's question."
            lc_messages.insert(0, SystemMessage(content=fallback_prompt))

        # Return messages list directly (LLM accepts list of messages)
        return lc_messages

    # Create a proper chain: prepare messages -> LLM
    # The LLM will handle streaming via astream_events
    chain = (
        RunnableLambda(prepare_messages)
        | llm
    )
    
    return chain

