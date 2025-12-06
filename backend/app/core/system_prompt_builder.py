"""System prompt builder for LLM context."""
from __future__ import annotations

from typing import Optional

from app.core.constants import (
    ADHERENCE_PHRASES,
    ACTIVITY_KEYWORDS,
    MEDICATION_KEYWORDS_SPECIFIC,
    MEDICATION_PHRASES,
    MEAL_KEYWORDS,
    WEIGHT_KEYWORDS,
)
from app.core.timezone_utils import get_current_datetime_string
from app.schemas.enhanced_patient_context import EnhancedPatientContext


def build_system_prompt(
    patient_context_str: str,
    enhanced_context: Optional[EnhancedPatientContext],
    user_message: str,
    agent_text: Optional[str],
) -> str:
    """Build system prompt with patient context, current date/time, and relevant logs.
    
    Args:
        patient_context_str: Formatted patient information string
        enhanced_context: Enhanced patient context with recent logs (optional)
        user_message: User's current message
        agent_text: Agent analysis output (optional)
        
    Returns:
        Complete system prompt string
    """
    # Get current date/time
    current_datetime_str, current_date_str = get_current_datetime_string()
    
    parts = [
        "You are a helpful diabetes management assistant.",
        f"\nCurrent Date and Time: {current_datetime_str} (Today is {current_date_str}).",
        "Use this information when answering questions about 'today', 'recent', or time-sensitive queries.",
    ]
    
    if patient_context_str:
        parts.append(f"\nPatient Information:\n{patient_context_str}\n")
    
    # Add pattern analysis insights if available (for chatbot context)
    if enhanced_context and enhanced_context.pattern_analysis:
        pattern = enhanced_context.pattern_analysis
        pattern_parts = []
        
        if pattern.personalized_targets:
            pt = pattern.personalized_targets
            pattern_parts.append(f"Personalized Glucose Target: {pt.suggested_glucose_range_min:.0f}-{pt.suggested_glucose_range_max:.0f} mg/dL. {pt.rationale}")
            if pt.best_meal_times:
                pattern_parts.append(f"Best meal times: {', '.join(pt.best_meal_times)}")
            if pt.best_activity_times:
                pattern_parts.append(f"Best activity times: {', '.join(pt.best_activity_times)}")
        
        if pattern.circadian_pattern and pattern.circadian_pattern.peak_hours:
            cp = pattern.circadian_pattern
            pattern_parts.append(f"Glucose peaks around {', '.join([f'{h}:00' for h in cp.peak_hours[:2]])} and is lowest around {', '.join([f'{h}:00' for h in cp.low_hours[:2]])}")
        
        if pattern.meal_glucose_correlations and pattern.meal_glucose_correlations.best_meals:
            best = ', '.join(pattern.meal_glucose_correlations.best_meals[:3])
            pattern_parts.append(f"Best meals for glucose control: {best}")
        
        if pattern.lifestyle_consistency and pattern.lifestyle_consistency.areas_needing_improvement:
            areas = ', '.join(pattern.lifestyle_consistency.areas_needing_improvement[:2])
            pattern_parts.append(f"Areas needing improvement: {areas}")
        
        if pattern_parts:
            parts.append(f"\nPersonalized Insights:\n" + "\n".join(f"- {p}" for p in pattern_parts) + "\n")
    
    # Add meal/medication/weight/activity logs if relevant
    if enhanced_context:
        user_lower = user_message.lower()
        
        # Check for meals
        if any(kw in user_lower for kw in MEAL_KEYWORDS):
            meals_str = enhanced_context.get_recent_meals_string(limit=10)
            if meals_str and "No recent meals" not in meals_str:
                parts.append(f"\n{meals_str}\n")
        
        # Check for medications
        if is_medication_query(user_lower):
            meds_str = enhanced_context.get_recent_medications_string(limit=10)
            if meds_str and "No recent medication" not in meds_str:
                parts.append(f"\n{meds_str}\n")
            
            if is_adherence_query(user_lower):
                parts.append(
                    "\nNote: The user is asking about whether they have taken their medication. "
                    "Use the medication logs above to determine if they have logged taking their medication recently (especially today). "
                    "If no recent logs are found, indicate that they haven't logged taking their medication."
                )
        
        # Check for weight
        if any(kw in user_lower for kw in WEIGHT_KEYWORDS):
            weight_str = enhanced_context.get_recent_weight_string(limit=10)
            if weight_str and "No recent weight" not in weight_str:
                parts.append(f"\n{weight_str}\n")
        
        # Check for activity
        if any(kw in user_lower for kw in ACTIVITY_KEYWORDS):
            activity_str = enhanced_context.get_recent_activity_string(limit=10)
            if activity_str and "No recent activity" not in activity_str:
                parts.append(f"\n{activity_str}\n")
    
    # Add agent output
    if agent_text and not agent_text.startswith("I'm here to help"):
        parts.append(
            f"Use the following agent analysis to provide a clear, empathetic response to the user.\n"
            f"Agent Analysis: {agent_text}\n\n"
            "Respond naturally and conversationally based on this analysis. When the user asks about specific meals or medications they logged, refer to the detailed lists provided above."
        )
    else:
        parts.append(
            "Help users with questions about their glucose logs, meals, activity, and general diabetes management. "
            "When they ask about recent meals or medications, use the detailed lists provided above."
        )
    
    return "\n".join(parts)


def is_medication_query(user_message_lower: str) -> bool:
    """Check if user message is about medications.
    
    Args:
        user_message_lower: User message in lowercase
        
    Returns:
        True if message is about medications, False otherwise
    """
    return (
        any(phrase in user_message_lower for phrase in MEDICATION_PHRASES) or
        (any(keyword in user_message_lower for keyword in MEDICATION_KEYWORDS_SPECIFIC) and
         "meal" not in user_message_lower and "food" not in user_message_lower)
    )


def is_adherence_query(user_message_lower: str) -> bool:
    """Check if user is asking about medication adherence.
    
    Args:
        user_message_lower: User message in lowercase
        
    Returns:
        True if message is about medication adherence, False otherwise
    """
    return any(phrase in user_message_lower for phrase in ADHERENCE_PHRASES)

