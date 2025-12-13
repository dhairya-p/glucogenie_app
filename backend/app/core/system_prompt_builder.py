"""System prompt builder for LLM context."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone as tz
from typing import Optional, List

from app.core.constants import (
    ADHERENCE_PHRASES,
    ACTIVITY_KEYWORDS,
    MEDICATION_KEYWORDS_SPECIFIC,
    MEDICATION_PHRASES,
    MEAL_KEYWORDS,
    WEIGHT_KEYWORDS,
    UTC_Z_SUFFIX,
    UTC_OFFSET_SUFFIX,
)
from app.core.timezone_utils import (
    get_current_datetime_string,
    format_singapore_datetime,
    get_singapore_now,
    get_today_start_singapore,
)
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

    # Add hyperpersonalized features (3 essential features for individual analysis)
    if enhanced_context:
        # FEATURE 1: Recent event correlations (individual meal/activity impacts)
        event_correlations = _get_recent_event_correlations(enhanced_context)
        if event_correlations:
            parts.append(f"\n{event_correlations}\n")

        # FEATURE 2: Trend alerts (recent changes in last 2-3 days)
        trend_alerts = _get_trend_alerts(enhanced_context)
        if trend_alerts:
            parts.append(f"\n{trend_alerts}\n")

        # FEATURE 3: Contextual insights (current state vs patterns)
        contextual_insights = _get_contextual_insights(enhanced_context)
        if contextual_insights:
            parts.append(f"\n{contextual_insights}\n")

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


def _get_recent_event_correlations(enhanced_context: EnhancedPatientContext, limit: int = 5) -> str:
    """Get recent meal/activity events with specific glucose impacts (FEATURE 1).

    Performance: Only analyzes last 5 events, not full history.

    Args:
        enhanced_context: Enhanced patient context
        limit: Number of recent events to analyze (default: 5)

    Returns:
        Formatted string of recent event correlations
    """
    correlations = []

    # Get recent meals (last 5 only for performance)
    recent_meals = enhanced_context.recent_meal_logs[:limit]

    # Create glucose lookup (dict for O(1) access)
    glucose_by_time = {}
    for reading in enhanced_context.recent_glucose_readings:
        try:
            dt = datetime.fromisoformat(reading.timestamp.replace(UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz.utc)
            glucose_by_time[dt] = reading.reading
        except Exception:
            continue

    if not glucose_by_time:
        return ""

    # Analyze each recent meal
    for meal in recent_meals:
        try:
            meal_dt = datetime.fromisoformat(meal.timestamp.replace(UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX))
            if meal_dt.tzinfo is None:
                meal_dt = meal_dt.replace(tzinfo=tz.utc)

            meal_time_str = format_singapore_datetime(meal_dt, "%b %d at %I:%M %p")

            # Find baseline glucose (before or at meal time)
            baseline = None
            for dt in sorted(glucose_by_time.keys()):
                if dt <= meal_dt:
                    baseline = glucose_by_time[dt]
                else:
                    break

            # Find post-meal glucose (1-3 hours after)
            meal_end = meal_dt + timedelta(hours=3)
            post_meal_readings = [
                (dt, glucose) for dt, glucose in glucose_by_time.items()
                if meal_dt < dt <= meal_end
            ]

            if baseline and post_meal_readings:
                max_glucose = max(g for _, g in post_meal_readings)
                max_time = next(dt for dt, g in post_meal_readings if g == max_glucose)
                max_time_str = format_singapore_datetime(max_time, "%I:%M %p")
                spike = max_glucose - baseline

                # Add correlation
                impact = "high" if spike > 40 else "moderate" if spike > 20 else "low"
                correlations.append(
                    f"- {meal.meal} ({meal_time_str}): {baseline:.0f}→{max_glucose:.0f} mg/dL at {max_time_str} "
                    f"(+{spike:.0f} spike, {impact} impact)"
                )
        except Exception:
            continue

    # Analyze recent activity impacts (last 3 for performance)
    recent_activities = enhanced_context.recent_activity_logs[:3]
    for activity in recent_activities:
        try:
            activity_dt = datetime.fromisoformat(activity.timestamp.replace(UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX))
            if activity_dt.tzinfo is None:
                activity_dt = activity_dt.replace(tzinfo=tz.utc)

            activity_time_str = format_singapore_datetime(activity_dt, "%b %d at %I:%M %p")

            # Find glucose before (within 1 hour before)
            before_window = activity_dt - timedelta(hours=1)
            before_readings = [g for dt, g in glucose_by_time.items() if before_window <= dt < activity_dt]

            # Find glucose after (1-3 hours after)
            after_window_start = activity_dt + timedelta(hours=1)
            after_window_end = activity_dt + timedelta(hours=3)
            after_readings = [g for dt, g in glucose_by_time.items() if after_window_start <= dt <= after_window_end]

            if before_readings and after_readings:
                avg_before = sum(before_readings) / len(before_readings)
                avg_after = sum(after_readings) / len(after_readings)
                change = avg_after - avg_before

                direction = "reduced" if change < 0 else "increased"
                correlations.append(
                    f"- {activity.activity_type} ({activity_time_str}): {direction} glucose by {abs(change):.0f} mg/dL"
                )
        except Exception:
            continue

    if correlations:
        return "Recent Event Impacts (Individual):\n" + "\n".join(correlations[:8])  # Max 8 events
    return ""


def _get_trend_alerts(enhanced_context: EnhancedPatientContext) -> str:
    """Get trend alerts based on recent data (last 2-3 days only) (FEATURE 2).

    Performance: Only analyzes last 2-3 days, not full history.

    Args:
        enhanced_context: Enhanced patient context

    Returns:
        Formatted string of trend alerts
    """
    alerts = []

    # Alert 1: Recent glucose trend (last 2 days vs previous 2 days)
    if len(enhanced_context.recent_glucose_readings) >= 4:
        readings = enhanced_context.recent_glucose_readings

        # Split into recent (first half) vs earlier (second half)
        mid = len(readings) // 2
        recent_avg = sum(r.reading for r in readings[:mid]) / mid
        earlier_avg = sum(r.reading for r in readings[mid:mid*2]) / mid if len(readings) >= mid*2 else None

        if earlier_avg:
            change = recent_avg - earlier_avg
            if abs(change) > 15:  # Significant change
                direction = "increasing" if change > 0 else "decreasing"
                alerts.append(
                    f"⚠️ Glucose Trend: Your glucose is {direction} (recent avg: {recent_avg:.0f} vs earlier: {earlier_avg:.0f} mg/dL, change: {change:+.0f})"
                )

    # Alert 2: Missed medication today
    if enhanced_context.patient.medications:
        today_start = get_today_start_singapore()

        today_meds = []
        for med in enhanced_context.recent_medication_logs:
            try:
                dt = datetime.fromisoformat(med.timestamp.replace(UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=tz.utc)
                dt_sg = dt.astimezone(get_singapore_now().tzinfo)
                if dt_sg >= today_start:
                    today_meds.append(med.medication_name)
            except Exception:
                continue

        # Check if expected medications are logged today
        expected_meds = set(enhanced_context.patient.medications)
        logged_today = set(today_meds)
        missing_meds = expected_meds - logged_today

        if missing_meds and len(missing_meds) <= 3:  # Only if a few are missing
            alerts.append(
                f"📋 Medication Reminder: You haven't logged {', '.join(list(missing_meds)[:2])} today"
            )

    # Alert 3: Unusual pattern detection (glucose outside typical range)
    if enhanced_context.pattern_analysis and enhanced_context.pattern_analysis.personalized_targets:
        targets = enhanced_context.pattern_analysis.personalized_targets
        if enhanced_context.latest_glucose:
            if enhanced_context.latest_glucose > targets.suggested_glucose_range_max + 20:
                alerts.append(
                    f"⚠️ High Glucose Alert: Current reading ({enhanced_context.latest_glucose:.0f} mg/dL) is significantly above your target range ({targets.suggested_glucose_range_max:.0f} mg/dL)"
                )
            elif enhanced_context.latest_glucose < targets.suggested_glucose_range_min - 10:
                alerts.append(
                    f"⚠️ Low Glucose Alert: Current reading ({enhanced_context.latest_glucose:.0f} mg/dL) is below your target range ({targets.suggested_glucose_range_min:.0f} mg/dL)"
                )

    # Alert 4: Activity consistency (if no activity in last 2 days but usually active)
    if enhanced_context.pattern_analysis and enhanced_context.pattern_analysis.lifestyle_consistency:
        lc = enhanced_context.pattern_analysis.lifestyle_consistency
        if lc.activity_consistency > 0.5:  # Usually active
            # Check recent activity (last 2 days)
            now = get_singapore_now()
            two_days_ago = now - timedelta(days=2)

            recent_activities = []
            for activity in enhanced_context.recent_activity_logs:
                try:
                    dt = datetime.fromisoformat(activity.timestamp.replace(UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=tz.utc)
                    if dt >= two_days_ago.astimezone(tz.utc):
                        recent_activities.append(activity)
                except Exception:
                    continue

            if not recent_activities:
                alerts.append(
                    "💪 Activity Reminder: You haven't logged any physical activity in the last 2 days. Regular activity helps glucose control."
                )

    if alerts:
        return "Personalized Alerts:\n" + "\n".join(alerts[:3])  # Max 3 alerts to avoid overwhelming
    return ""


def _get_contextual_insights(enhanced_context: EnhancedPatientContext) -> str:
    """Get contextual insights comparing current state to patterns (FEATURE 3).

    Performance: Simple comparisons, no heavy computation.

    Args:
        enhanced_context: Enhanced patient context

    Returns:
        Formatted string of contextual insights
    """
    insights = []

    # Insight 1: Current glucose vs typical for this hour
    if (enhanced_context.latest_glucose and
        enhanced_context.pattern_analysis and
        enhanced_context.pattern_analysis.circadian_pattern):

        try:
            # Get current hour
            now = get_singapore_now()
            current_hour = now.hour

            # Get typical glucose for this hour from circadian pattern
            cp = enhanced_context.pattern_analysis.circadian_pattern

            # Find if this is a peak or low hour
            if current_hour in cp.peak_hours[:3]:
                insights.append(
                    f"🕐 Time Context: Your glucose is typically higher around {current_hour}:00 (peak hour). "
                    f"Current: {enhanced_context.latest_glucose:.0f} mg/dL"
                )
            elif current_hour in cp.low_hours[:3]:
                insights.append(
                    f"🕐 Time Context: Your glucose is typically lower around {current_hour}:00 (low hour). "
                    f"Current: {enhanced_context.latest_glucose:.0f} mg/dL"
                )
        except Exception:
            pass

    # Insight 2: Meal timing suggestion
    if enhanced_context.pattern_analysis and enhanced_context.pattern_analysis.personalized_targets:
        pt = enhanced_context.pattern_analysis.personalized_targets
        if pt.best_meal_times:
            now = get_singapore_now()
            current_time = f"{now.hour:02d}:{now.minute:02d}"

            # Check if near a recommended meal time
            for meal_time in pt.best_meal_times[:2]:
                try:
                    recommended_hour = int(meal_time.split(':')[0])
                    if abs(now.hour - recommended_hour) <= 1:
                        insights.append(
                            f"🍽️ Meal Timing: Now ({current_time}) is a good time for a meal (recommended: {meal_time}) based on your glucose patterns"
                        )
                        break
                except Exception:
                    continue

    # Insight 3: Recent meal impact prediction
    if enhanced_context.recent_meal_logs and enhanced_context.pattern_analysis:
        mc = enhanced_context.pattern_analysis.meal_glucose_correlations
        if mc and mc.correlations:
            # Check last meal
            last_meal = enhanced_context.recent_meal_logs[0]

            # Find correlation for this meal type
            for corr in mc.correlations:
                if corr.meal_name.lower() in last_meal.meal.lower() or last_meal.meal.lower() in corr.meal_name.lower():
                    insights.append(
                        f"🍴 Last Meal Insight: Your {last_meal.meal} typically causes a {corr.avg_glucose_spike:.0f} mg/dL spike. "
                        f"Monitor your glucose 1-2 hours after eating."
                    )
                    break

    if insights:
        return "Contextual Insights:\n" + "\n".join(insights[:3])  # Max 3 insights
    return ""

