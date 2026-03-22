from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from supabase import Client

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
from app.schemas.enhanced_patient_context import (
    EnhancedPatientContext,
    RecentGlucoseReading,
    RecentMealLog,
    RecentMedicationLog,
    RecentActivityLog,
    RecentWeightLog,
)
from app.core.supabase_client import get_supabase_client
from app.core.timezone_utils import (
    get_singapore_now,
    get_singapore_timezone,
    get_today_start_singapore,
    format_singapore_datetime,
    parse_iso_to_utc_datetime,
)
from app.core.system_prompt_builder import build_system_prompt
from app.core.context_summarizer import summarize_enhanced_context

logger = logging.getLogger(__name__)

DEFAULT_UNMATCHED_RESPONSE = (
    "I'm a specialized diabetes management assistant. I can only assist with:\n\n"
    "• **Clinical Safety**: Medication safety, side effects, drug interactions, dosage questions, "
    "and clinical guidelines (MOH, ADA, WHO recommendations)\n\n"
    "• **Lifestyle Management**: Glucose tracking, meal logging, activity patterns, "
    "medication adherence, and diabetes lifestyle insights\n\n"
    "• **Food Analysis**: Nutritional information for Singaporean foods and meal planning\n\n"
    "I'm unable to assist with general conversation, unrelated health topics, or queries outside "
    "diabetes management. Please ask me about your diabetes care, medications, glucose readings, "
    "meals, or activity patterns."
)


def _fetch_basic_patient_context(supabase: Client, user_id: str) -> PatientContext:
    """Fetch profile, conditions, and medications from Supabase. Shared by _extract_enhanced_patient_context and _extract_patient_context."""
    profile_resp = (
        supabase.table("profiles")
        .select("first_name, last_name, age, sex, ethnicity, height, activity_level, location")
        .eq("id", user_id)
        .execute()
        .data
    )
    profile = profile_resp[0] if profile_resp else {}

    conditions_resp = (
        supabase.table("conditions")
        .select("condition_name")
        .eq("user_id", user_id)
        .execute()
        .data
        or []
    )
    conditions = [c.get("condition_name") for c in conditions_resp if c.get("condition_name")]

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
        first_name=profile.get("first_name"),
        last_name=profile.get("last_name"),
        age=profile.get("age", 30),
        sex=profile.get("sex"),
        ethnicity=profile.get("ethnicity", "Unknown"),
        height=profile.get("height"),
        activity_level=profile.get("activity_level"),
        location=profile.get("location"),
        conditions=conditions,
        medications=medications,
    )


def _extract_enhanced_patient_context(user_id: str, days: int = 7) -> EnhancedPatientContext:
    """Fetch complete patient context including recent logs from Supabase.
    
    This function fetches ALL patient data ONCE to avoid redundant Supabase calls.
    The enhanced context is then shared across all agents.
    
    Args:
        user_id: User ID to fetch context for
        days: Number of days of history to fetch (default: 7)
    
    Returns:
        EnhancedPatientContext with all patient data and recent logs
    """
    from datetime import datetime, timedelta, timezone as tz
    
    supabase = get_supabase_client()
    now = get_singapore_now()
    # Add 1 minute buffer to ensure we catch very recent readings (timezone/clock skew)
    since = now - timedelta(days=days, minutes=1)
    # Convert to UTC for Supabase query (Supabase stores timestamps in UTC)
    since_utc = since.astimezone(tz.utc) if since.tzinfo else since.replace(tzinfo=get_singapore_timezone()).astimezone(tz.utc)

    # 1. Fetch basic patient context (shared with _extract_patient_context)
    patient = _fetch_basic_patient_context(supabase, user_id)

    # 2. Fetch recent glucose readings
    glucose_readings = []
    try:
        # Fetch the most recent readings (no time filter to ensure we get absolute latest)
        # Then filter in Python with proper timezone handling
        glucose_rows = (
            supabase.table("glucose_readings")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
            .data
            or []
        )
        
        # Filter by time in Python to ensure timezone-aware comparison
        filtered_rows = []
        for row in glucose_rows:
            row_created_at = row.get("created_at")
            if row_created_at:
                row_dt = parse_iso_to_utc_datetime(row_created_at)
                if row_dt is not None and row_dt >= since_utc:
                    filtered_rows.append(row)
            else:
                filtered_rows.append(row)
        
        glucose_readings = [
            RecentGlucoseReading(
                reading=float(row.get("reading", 0)),
                timing=row.get("timing"),
                timestamp=row.get("created_at", ""),
                notes=row.get("notes"),
            )
            for row in filtered_rows
        ]
    except Exception as exc:
        logger.error("Error fetching glucose readings: %s", exc, exc_info=True)
    
    # 3. Fetch recent meal logs
    meal_logs = []
    try:
        meal_rows = (
            supabase.table("meal_logs")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
            .data
            or []
        )
        
        # Filter by time in Python
        filtered_meal_rows = []
        for row in meal_rows:
            row_created_at = row.get("created_at")
            if row_created_at:
                row_dt = parse_iso_to_utc_datetime(row_created_at)
                if row_dt is not None and row_dt >= since_utc:
                    filtered_meal_rows.append(row)
            else:
                filtered_meal_rows.append(row)
        
        meal_rows = filtered_meal_rows
        meal_logs = [
            RecentMealLog(
                meal=row.get("meal", ""),
                description=row.get("description"),
                timestamp=row.get("created_at", ""),
            )
            for row in meal_rows
        ]
    except Exception as exc:
        logger.error("Error fetching meal logs: %s", exc, exc_info=True)
    
    # 4. Fetch recent medication logs
    medication_logs = []
    try:
        med_log_rows = (
            supabase.table("medication_logs")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
            .data
            or []
        )
        
        # Filter by time in Python
        filtered_med_rows = []
        for row in med_log_rows:
            row_created_at = row.get("created_at")
            if row_created_at:
                row_dt = parse_iso_to_utc_datetime(row_created_at)
                if row_dt is not None and row_dt >= since_utc:
                    filtered_med_rows.append(row)
            else:
                filtered_med_rows.append(row)
        
        med_log_rows = filtered_med_rows
        medication_logs = [
            RecentMedicationLog(
                medication_name=row.get("medication_name", ""),
                quantity=row.get("quantity"),
                timestamp=row.get("created_at", ""),
                notes=row.get("notes"),
            )
            for row in med_log_rows
        ]
    except Exception as exc:
        logger.error("Error fetching medication logs: %s", exc, exc_info=True)
    
    # 5. Fetch recent activity logs
    activity_logs = []
    try:
        activity_rows = (
            supabase.table("activity_logs")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
            .data
            or []
        )
        
        # Filter by time in Python
        filtered_activity_rows = []
        for row in activity_rows:
            row_created_at = row.get("created_at")
            if row_created_at:
                row_dt = parse_iso_to_utc_datetime(row_created_at)
                if row_dt is not None and row_dt >= since_utc:
                    filtered_activity_rows.append(row)
            else:
                filtered_activity_rows.append(row)
        
        activity_rows = filtered_activity_rows
        activity_logs = [
            RecentActivityLog(
                activity_type=row.get("activity_type", ""),
                duration_minutes=int(row.get("duration_minutes", 0)),
                intensity=row.get("intensity", "unknown"),
                timestamp=row.get("created_at", ""),
            )
            for row in activity_rows
        ]
    except Exception as exc:
        logger.error("Error fetching activity logs: %s", exc, exc_info=True)
    
    # 6. Fetch recent weight logs
    weight_logs = []
    try:
        weight_rows = (
            supabase.table("weight_logs")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(30)
            .execute()
            .data
            or []
        )
        
        # Filter by time in Python
        filtered_weight_rows = []
        for row in weight_rows:
            row_created_at = row.get("created_at")
            if row_created_at:
                row_dt = parse_iso_to_utc_datetime(row_created_at)
                if row_dt is not None and row_dt >= since_utc:
                    filtered_weight_rows.append(row)
            else:
                filtered_weight_rows.append(row)
        
        weight_rows = filtered_weight_rows
        weight_logs = [
            RecentWeightLog(
                weight=float(row.get("weight", 0)),
                unit=row.get("unit", "kg"),
                timestamp=row.get("created_at", ""),
            )
            for row in weight_rows
        ]
    except Exception as exc:
        logger.error("Error fetching weight logs: %s", exc, exc_info=True)
    
    # 7. Compute summary statistics
    latest_glucose = None
    latest_glucose_timestamp = None
    if glucose_readings:
        latest_glucose = glucose_readings[0].reading
        latest_glucose_timestamp = glucose_readings[0].timestamp
    
    avg_glucose_7d = None
    if glucose_readings:
        avg_glucose_7d = sum(g.reading for g in glucose_readings) / len(glucose_readings)
    
    latest_weight = None
    if weight_logs:
        # Convert to kg if needed
        latest_weight_kg = weight_logs[0].weight
        if weight_logs[0].unit.lower() == "lbs":
            latest_weight_kg = latest_weight_kg * 0.453592
        latest_weight = latest_weight_kg
    
    total_activity_minutes_7d = sum(a.duration_minutes for a in activity_logs)
    
    enhanced_context = EnhancedPatientContext(
        patient=patient,
        recent_glucose_readings=glucose_readings,
        recent_meal_logs=meal_logs,
        recent_medication_logs=medication_logs,
        recent_activity_logs=activity_logs,
        recent_weight_logs=weight_logs,
        latest_glucose=latest_glucose,
        latest_glucose_timestamp=latest_glucose_timestamp,
        avg_glucose_7d=avg_glucose_7d,
        total_medication_logs_7d=len(medication_logs),
        total_meal_logs_7d=len(meal_logs),
        total_activity_minutes_7d=total_activity_minutes_7d,
        latest_weight=latest_weight,
        data_fetched_at=now,
        days_of_history=days,
    )
    
    # Perform pattern analysis if we have sufficient data
    try:
        from app.core.pattern_analyzer import analyze_patterns
        if (
            len(glucose_readings) >= 3
            or len(meal_logs) >= 2
            or len(medication_logs) >= 2
            or len(activity_logs) >= 2
        ):
            logger.info("Performing pattern analysis...")
            pattern_analysis = analyze_patterns(enhanced_context)
            enhanced_context.pattern_analysis = pattern_analysis
            logger.info("Pattern analysis completed")
    except Exception as exc:
        logger.error("Error performing pattern analysis: %s", exc, exc_info=True)
        enhanced_context.pattern_analysis = None
    
    # Compute a longer-horizon summary string once per request
    try:
        summary_text = summarize_enhanced_context(enhanced_context)
        if summary_text:
            enhanced_context.historical_summary = summary_text
    except Exception as exc:
        logger.error("Error summarizing enhanced patient context: %s", exc, exc_info=True)
        enhanced_context.historical_summary = None
    
    # Log summary metadata for debugging longer context window
    try:
        logger.info(
            "Enhanced context built: days_of_history=%d, historical_summary_len=%d",
            enhanced_context.days_of_history,
            len(enhanced_context.historical_summary or ""),
        )
    except Exception:
        # Logging must never break the request flow
        pass
    
    return enhanced_context


def _extract_patient_context(user_id: str) -> PatientContext:
    """Fetch patient context from Supabase for a given user_id. Uses shared _fetch_basic_patient_context."""
    supabase = get_supabase_client()
    return _fetch_basic_patient_context(supabase, user_id)


def _route_and_process(input_data: dict[str, Any]) -> dict[str, Any]:
    """Main routing logic: determine intent and call the appropriate agent.
    
    Fetches enhanced patient context ONCE and shares it across all agents
    to avoid redundant Supabase calls.
    """

    messages = input_data.get("messages", [])
    user_id = input_data.get("user_id", "")
    days = input_data.get("days", 7)  # Default to 7 days of history
    
    logger.info(
        "_route_and_process called with user_id=%s, messages count=%d, days=%d",
        user_id,
        len(messages),
        days,
    )

    if not messages:
        return {"output": "No messages provided."}

    if not user_id:
        logger.warning("No user_id provided, cannot fetch patient context or logs")
        return {"output": "I'm here to help with your diabetes management. Ask me about your glucose logs, meals, or activity patterns!"}

    # Extract the latest user message
    last_message = messages[-1]
    user_text = last_message.get("content", "") if isinstance(last_message, dict) else str(last_message)

    # Fetch enhanced patient context ONCE (includes all data)
    try:
        enhanced_context = _extract_enhanced_patient_context(user_id, days=days)
        patient = enhanced_context.patient
    except Exception as exc:
        logger.error("Failed to fetch enhanced patient context: %s", exc, exc_info=True)
        # Fallback to basic context
        try:
            patient = _extract_patient_context(user_id)
        except Exception:
            patient = PatientContext(age=30, ethnicity="Unknown", conditions=[], medications=None)
        enhanced_context = None

    # Route intent
    try:
        router_state = RouterState(patient=patient, user_message=user_text)
        routing_result = route_intent.invoke({"state": router_state})
        target_agent = routing_result.get("target_agent", "unmatched")
        logger.info("Router selected target_agent: %s", target_agent)
    except Exception as exc:
        logger.error("Error in router: %s", exc, exc_info=True)
        target_agent = "unmatched"

    # Call the appropriate agent (all agents receive enhanced_context if available)
    rag_context = ""  # Collect RAG context from agent
    try:
        if target_agent == "clinical_safety":
            # Pass enhanced context to clinical safety agent
            safety_state = ClinicalSafetyState(
                patient=patient,
                user_message=user_text,
                enhanced_context=enhanced_context  # Pass full context
            )
            result = check_clinical_safety.invoke({"state": safety_state})
            specific = result.get("specific_findings", [])
            specific_text = ""
            if specific:
                specific_text = "Key interactions from your knowledge base:\n" + "\n".join(
                    f"- {item}" for item in specific
                )
            output = (
                f"Safety check: {result.get('rationale', '')}.\n"
                f"Warnings: {result.get('warnings', [])}\n"
                f"{specific_text}".strip()
            )
            rag_context = result.get('rag_context', '')
        elif target_agent == "lifestyle_analyst":
            # Pass enhanced context to lifestyle analyst (it can use pre-fetched data)
            lifestyle_state = LifestyleState(
                patient=patient,
                user_id=user_id,
                days=days,
                user_message=user_text,  # Pass user message for RAG queries
                enhanced_context=enhanced_context  # Pass pre-fetched data
            )
            result = analyze_lifestyle.invoke({"state": lifestyle_state})
            insights = result.get("insights", [])
            insight_texts = [f"{i.get('title', '')}: {i.get('detail', '')}" for i in insights]
            output = "\n".join(insight_texts) if insight_texts else "No lifestyle insights available."
            rag_context = result.get('rag_context', '')
            logger.info("Lifestyle analyst output: %s", output[:200])  # Log first 200 chars
        elif target_agent == "cultural_dietitian":
            # Cultural Dietitian Agent for Singapore-specific meal recommendations
            dietitian_state = CulturalDietitianState(
                patient=patient,
                enhanced_context=enhanced_context,
                user_message=user_text,
            )
            # Use text-based meal recommendation tool (not image analysis) for chat queries
            from app.agents.cultural_dietitian_agent import recommend_cultural_meals

            logger.info(
                "[Router] Invoking Cultural Dietitian Agent for meal recommendations for user_id=%s",
                user_id,
            )
            result = recommend_cultural_meals.invoke({"state": dietitian_state})
            output = result.get("summary", "Cultural meal recommendations are not available at the moment.")
            rag_context = result.get("rag_context", "")
            logger.info(
                "[Router] Cultural Dietitian Agent returned summary (first 200 chars): %s",
                output[:200],
            )
        else:
            # Unmatched query: return default response
            rag_context = ""
            output = DEFAULT_UNMATCHED_RESPONSE
    except Exception as exc:
        logger.error("Error calling agent %s: %s", target_agent, exc, exc_info=True)
        output = f"Error processing request: {str(exc)}"

    logger.info("_route_and_process returning output: %s", output[:200])  # Log first 200 chars
    rag_sources = []
    if rag_context:
        rag_sources = re.findall(r"Source:\s*([^\n|]+)", rag_context)
        rag_sources = list(dict.fromkeys([s.strip() for s in rag_sources if s.strip()]))

    return {
        "output": output,
        "enhanced_context": enhanced_context,
        "rag_context": rag_context,
        "target_agent": target_agent,
        "rag_sources": rag_sources,
    }  # Return RAG context for system prompt


