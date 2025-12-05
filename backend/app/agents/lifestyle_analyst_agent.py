from __future__ import annotations

from typing import List, Optional
import logging

import os
from datetime import datetime, timedelta, timezone

import pandas as pd
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict
from supabase import Client, create_client

from app.schemas.patient_context import PatientContext

logger = logging.getLogger(__name__)


class GlucoseLog(BaseModel):
    timestamp: str
    reading_mg_dl: float
    timing: Optional[str] = None  # 'Just woke up', 'Before meal', 'After meal', 'Bedtime'
    notes: Optional[str] = None


class ActivityLog(BaseModel):
    timestamp: str
    minutes: int
    intensity: str


class MealLog(BaseModel):
    timestamp: str
    carbs_g: float
    description: Optional[str] = None


class WeightLog(BaseModel):
    timestamp: str
    weight: float
    unit: str  # 'kg' or 'lbs'
    notes: Optional[str] = None


class MedicationLog(BaseModel):
    timestamp: str
    medication_name: str
    quantity: Optional[str] = None
    notes: Optional[str] = None


class LifestyleState(BaseModel):
    """Input state for the Lifestyle Analyst Agent.

    Patient-level context is always required.
    Logs are fetched from Supabase using the provided user identifier.
    """

    patient: PatientContext
    user_id: str
    days: int = Field(
        default=7,
        description="Number of days of history to include in the analysis.",
    )

    model_config = ConfigDict(extra="ignore")


class LifestyleInsight(BaseModel):
    title: str
    detail: str


class LifestyleAnalysisResult(BaseModel):
    """Structured output for the Lifestyle Analyst."""

    avg_glucose: Optional[float] = None
    latest_glucose: Optional[float] = None
    latest_glucose_timestamp: Optional[str] = None
    glucose_readings_count: int = 0
    total_activity_minutes: int = 0
    meals_count: int = 0
    weight_logs_count: int = 0
    medication_logs_count: int = 0
    insights: List[LifestyleInsight] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


def _get_supabase_client() -> Client:
    """Create a Supabase client from environment variables.

    This mirrors the configuration used in `app.main.Settings`.
    """

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Supabase URL or key not configured in environment.")

    return create_client(url, key)


@tool("analyze_lifestyle", return_direct=False)
def analyze_lifestyle(state: LifestyleState) -> dict:
    """Analyze glucose, activity, and meals for lifestyle insights.

    Uses pandas DataFrames under the hood to compute simple aggregates.
    This is intentionally lightweight; more advanced analysis can be added later.
    """

    logger.info("analyze_lifestyle called for user_id: %s, days: %d", state.user_id, state.days)
    
    try:
        supabase = _get_supabase_client()
        logger.info("Supabase client created successfully")
    except Exception as exc:
        logger.error("Failed to create Supabase client: %s", exc, exc_info=True)
        return {"insights": [], "avg_glucose": None, "latest_glucose": None, "latest_glucose_timestamp": None, "glucose_readings_count": 0, "total_activity_minutes": 0, "meals_count": 0, "weight_logs_count": 0, "medication_logs_count": 0}
    
    insights: List[LifestyleInsight] = []

    # Time window cutoff
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=state.days)
    since_iso = since.isoformat()
    logger.info("Fetching logs since: %s", since_iso)

    # --- Fetch logs from Supabase -------------------------------------------------

    # Glucose logs - using 'glucose_readings' table
    try:
        logger.info("Fetching glucose logs for user_id: %s", state.user_id)
        glucose_rows = (
            supabase.table("glucose_readings")
            .select("*")
            .eq("user_id", state.user_id)
            .gte("created_at", since_iso)
            .execute()
            .data
            or []
        )
        logger.info("Fetched %d glucose logs", len(glucose_rows))
    except Exception as exc:
        logger.error("Error fetching glucose logs: %s", exc, exc_info=True)
        glucose_rows = []
    glucose_logs: List[GlucoseLog] = []
    for row in glucose_rows:
        # Map from glucose_readings schema: reading, created_at, timing, notes
        glucose_logs.append(
            GlucoseLog(
                timestamp=row.get("created_at") or row.get("timestamp") or "",
                reading_mg_dl=float(row.get("reading") or 0.0),
                timing=row.get("timing"),
                notes=row.get("notes"),
            )
        )

    # Activity logs - using 'activity_logs' table
    try:
        logger.info("Fetching activity logs for user_id: %s", state.user_id)
        activity_rows = (
            supabase.table("activity_logs")
            .select("*")
            .eq("user_id", state.user_id)
            .gte("created_at", since_iso)
            .execute()
            .data
            or []
        )
        logger.info("Fetched %d activity logs", len(activity_rows))
    except Exception as exc:
        logger.error("Error fetching activity logs: %s", exc, exc_info=True)
        activity_rows = []
    activity_logs: List[ActivityLog] = []
    for row in activity_rows:
        # Map from activity_logs schema: duration_minutes, intensity, created_at
        activity_logs.append(
            ActivityLog(
                timestamp=row.get("created_at") or row.get("timestamp") or "",
                minutes=int(row.get("duration_minutes") or row.get("minutes") or 0),
                intensity=row.get("intensity") or "unknown",
            )
        )

    # Meal logs - Note: meals might be stored in glucose_readings with timing field
    # or in a separate table. For now, we'll extract meal-related data from glucose_readings
    # where timing indicates a meal context (e.g., "Before meal", "After meal")
    try:
        logger.info("Fetching meal-related data for user_id: %s", state.user_id)
        # Check if there's a separate meal logs table, otherwise use glucose_readings timing
        meal_rows = []
        try:
            meal_rows = (
                supabase.table("meal_logs")
                .select("*")
                .eq("user_id", state.user_id)
                .gte("created_at", since_iso)
                .execute()
                .data
                or []
            )
            logger.info("Found meal_logs table with %d entries", len(meal_rows))
        except Exception:
            # No meal_logs table, extract from glucose_readings where timing indicates meals
            logger.info("No meal_logs table found, extracting from glucose_readings timing field")
            meal_related_glucose = [
                row for row in glucose_rows
                if row.get("timing") and ("meal" in str(row.get("timing", "")).lower())
            ]
            # Create meal log entries from glucose readings with meal timing
            for row in meal_related_glucose:
                meal_rows.append({
                    "created_at": row.get("created_at"),
                    "description": f"Meal context: {row.get('timing')}",
                    "carbs_g": 0.0,  # Not available in glucose_readings
                })
            logger.info("Extracted %d meal-related entries from glucose_readings", len(meal_rows))
    except Exception as exc:
        logger.error("Error fetching meal logs: %s", exc, exc_info=True)
        meal_rows = []
    meal_logs: List[MealLog] = []
    for row in meal_rows:
        meal_logs.append(
            MealLog(
                timestamp=row.get("created_at") or row.get("timestamp") or "",
                carbs_g=float(row.get("carbs_g") or row.get("carbs") or 0.0),
                description=row.get("description"),
            )
        )

    # Weight logs
    weight_rows = []
    try:
        logger.info("Fetching weight logs for user_id: %s", state.user_id)
        weight_rows = (
            supabase.table("weight_logs")
            .select("*")
            .eq("user_id", state.user_id)
            .gte("created_at", since_iso)
            .order("created_at", desc=False)
            .execute()
            .data
            or []
        )
        logger.info("Fetched %d weight logs", len(weight_rows))
    except Exception as exc:
        logger.error("Error fetching weight logs: %s", exc, exc_info=True)
        weight_rows = []
    weight_logs: List[WeightLog] = []
    for row in weight_rows:
        weight_logs.append(
            WeightLog(
                timestamp=row.get("created_at") or row.get("timestamp") or "",
                weight=float(row.get("weight") or 0.0),
                unit=row.get("unit", "kg"),
                notes=row.get("notes"),
            )
        )

    # Medication logs
    medication_log_rows = []
    try:
        logger.info("Fetching medication logs for user_id: %s", state.user_id)
        medication_log_rows = (
            supabase.table("medication_logs")
            .select("*")
            .eq("user_id", state.user_id)
            .gte("created_at", since_iso)
            .execute()
            .data
            or []
        )
        logger.info("Fetched %d medication logs", len(medication_log_rows))
    except Exception as exc:
        logger.error("Error fetching medication logs: %s", exc, exc_info=True)
        medication_log_rows = []
    medication_logs: List[MedicationLog] = []
    for row in medication_log_rows:
        medication_logs.append(
            MedicationLog(
                timestamp=row.get("created_at") or row.get("timestamp") or "",
                medication_name=row.get("medication_name", ""),
                quantity=row.get("quantity"),
                notes=row.get("notes"),
            )
        )

    # --- Compute aggregates -------------------------------------------------------

    insights: List[LifestyleInsight] = []

    # Comprehensive Glucose analysis
    avg_glucose: Optional[float] = None
    latest_glucose: Optional[float] = None
    latest_glucose_timestamp: Optional[str] = None
    glucose_count = len(glucose_logs)
    low_readings: List[float] = []  # Initialize for use in medication insights
    readings = None  # Initialize for use in medication insights
    if glucose_logs:
        df_glucose = pd.DataFrame([log.model_dump() for log in glucose_logs])
        df_glucose["timestamp"] = pd.to_datetime(df_glucose["timestamp"], errors="coerce")
        df_glucose = df_glucose.sort_values("timestamp")
        
        readings = df_glucose["reading_mg_dl"].values
        avg_glucose = float(readings.mean())
        min_glucose = float(readings.min())
        max_glucose = float(readings.max())
        std_glucose = float(readings.std())
        
        # Find the latest glucose reading (most recent timestamp)
        latest_log = max(glucose_logs, key=lambda x: x.timestamp)
        latest_glucose = latest_log.reading_mg_dl
        latest_glucose_timestamp = latest_log.timestamp
        
        # Format timestamp for display
        try:
            dt = datetime.fromisoformat(latest_glucose_timestamp.replace('Z', '+00:00'))
            formatted_timestamp = dt.strftime("%B %d, %Y at %I:%M %p")
        except Exception:
            formatted_timestamp = latest_glucose_timestamp
        
        # Basic stats
        insights.append(
            LifestyleInsight(
                title="Latest glucose reading",
                detail=f"Your most recent glucose reading is {latest_glucose:.1f} mg/dL (recorded on {formatted_timestamp}).",
            )
        )
        
        insights.append(
            LifestyleInsight(
                title="Glucose statistics",
                detail=f"Average: {avg_glucose:.1f} mg/dL | Range: {min_glucose:.1f}-{max_glucose:.1f} mg/dL | Variability (std dev): {std_glucose:.1f} mg/dL",
            )
        )
        
        # Analyze by timing
        timing_analysis = {}
        for log in glucose_logs:
            if log.timing:
                timing_key = log.timing.lower()
                if timing_key not in timing_analysis:
                    timing_analysis[timing_key] = []
                timing_analysis[timing_key].append(log.reading_mg_dl)
        
        if timing_analysis:
            timing_insights = []
            for timing, values in timing_analysis.items():
                avg = sum(values) / len(values)
                timing_insights.append(f"{timing.title()}: {avg:.1f} mg/dL (n={len(values)})")
            
            if timing_insights:
                insights.append(
                    LifestyleInsight(
                        title="Glucose by timing",
                        detail="Average readings: " + " | ".join(timing_insights),
                    )
                )
        
        # Identify high and low readings
        high_readings = [r for r in readings if r > 180]  # Hyperglycemia threshold
        low_readings = [r for r in readings if r < 70]    # Hypoglycemia threshold
        
        if high_readings:
            high_pct = (len(high_readings) / len(readings)) * 100
            insights.append(
                LifestyleInsight(
                    title="High glucose readings",
                    detail=f"{len(high_readings)} readings above 180 mg/dL ({high_pct:.1f}% of readings). Target: <180 mg/dL for most people with diabetes.",
                )
            )
        
        if low_readings:
            low_pct = (len(low_readings) / len(readings)) * 100
            insights.append(
                LifestyleInsight(
                    title="Low glucose readings",
                    detail=f"{len(low_readings)} readings below 70 mg/dL ({low_pct:.1f}% of readings). This may indicate hypoglycemia - monitor closely.",
                )
            )
        
        # Trend analysis (comparing first half vs second half of period)
        if len(readings) >= 4:
            mid_point = len(readings) // 2
            first_half_avg = float(readings[:mid_point].mean())
            second_half_avg = float(readings[mid_point:].mean())
            trend = "improving" if second_half_avg < first_half_avg else "increasing"
            change = abs(second_half_avg - first_half_avg)
            
            if change > 5:  # Only report if significant change
                insights.append(
                    LifestyleInsight(
                        title="Glucose trend",
                        detail=f"Your glucose levels are {trend} over the {state.days}-day period. Early period average: {first_half_avg:.1f} mg/dL, recent period: {second_half_avg:.1f} mg/dL (change: {change:.1f} mg/dL).",
                    )
                )
        
        # Variability assessment
        if std_glucose > 40:
            insights.append(
                LifestyleInsight(
                    title="Glucose variability",
                    detail=f"Your glucose shows high variability (std dev: {std_glucose:.1f} mg/dL). High variability can increase diabetes complications risk. Consider more consistent meal timing and medication adherence.",
                )
            )
        elif std_glucose < 20:
            insights.append(
                LifestyleInsight(
                    title="Glucose stability",
                    detail=f"Your glucose shows good stability (std dev: {std_glucose:.1f} mg/dL). This indicates consistent management.",
                )
            )
        
        # Target range assessment (for Type 2 Diabetes: 80-130 mg/dL fasting, <180 mg/dL post-meal)
        in_range = [r for r in readings if 80 <= r <= 180]
        in_range_pct = (len(in_range) / len(readings)) * 100 if readings.size > 0 else 0
        
        if in_range_pct < 50:
            insights.append(
                LifestyleInsight(
                    title="Time in range",
                    detail=f"Only {in_range_pct:.1f}% of your readings are in the target range (80-180 mg/dL). Consider discussing with your healthcare provider about adjusting your management plan.",
                )
            )
        elif in_range_pct >= 70:
            insights.append(
                LifestyleInsight(
                    title="Time in range",
                    detail=f"Excellent! {in_range_pct:.1f}% of your readings are in the target range (80-180 mg/dL). Keep up the good work!",
                )
            )

    # Activity analysis with correlation to glucose
    total_minutes = 0
    if activity_logs:
        df_activity = pd.DataFrame([log.model_dump() for log in activity_logs])
        total_minutes = int(df_activity["minutes"].sum())
        avg_daily_minutes = total_minutes / state.days if state.days > 0 else 0
        
        # Activity intensity breakdown
        intensity_counts = df_activity["intensity"].value_counts().to_dict()
        intensity_summary = ", ".join([f"{k}: {v} sessions" for k, v in intensity_counts.items()])
        
        insights.append(
            LifestyleInsight(
                title="Activity summary",
                detail=f"Total: {total_minutes} minutes over {state.days} days (avg {avg_daily_minutes:.0f} min/day). Intensity: {intensity_summary}.",
            )
        )
        
        # Activity recommendation
        if avg_daily_minutes < 30:
            insights.append(
                LifestyleInsight(
                    title="Activity recommendation",
                    detail=f"Consider increasing activity. Current average: {avg_daily_minutes:.0f} min/day. Target: 150+ minutes/week (about 21+ min/day) of moderate activity for diabetes management.",
                )
            )
        elif avg_daily_minutes >= 21:
            insights.append(
                LifestyleInsight(
                    title="Activity status",
                    detail=f"Great! You're meeting the recommended activity level ({avg_daily_minutes:.0f} min/day). Regular activity helps improve insulin sensitivity.",
                )
            )

    # Meal analysis with glucose correlation
    meals_count = len(meal_logs)
    if meal_logs:
        df_meals = pd.DataFrame([log.model_dump() for log in meal_logs])
        avg_carbs = float(df_meals["carbs_g"].mean()) if "carbs_g" in df_meals.columns and df_meals["carbs_g"].sum() > 0 else None
        
        if avg_carbs and avg_carbs > 0:
            insights.append(
                LifestyleInsight(
                    title="Meal patterns",
                    detail=f"Average meal contains {avg_carbs:.0f} g of carbohydrates. Typical target: 45-60g per meal for diabetes management.",
                )
            )
            
            # Carb intake assessment
            if avg_carbs > 75:
                insights.append(
                    LifestyleInsight(
                        title="Carbohydrate intake",
                        detail=f"Your average meal has {avg_carbs:.0f}g carbs, which is higher than typical recommendations (45-60g). Consider portion control or spreading carbs across meals.",
                    )
                )
            elif avg_carbs < 30:
                insights.append(
                    LifestyleInsight(
                        title="Carbohydrate intake",
                        detail=f"Your average meal has {avg_carbs:.0f}g carbs. Very low carb intake may require monitoring for hypoglycemia, especially if on insulin or certain medications.",
                    )
                )
    
    # Cross-correlation insights (glucose + activity + meals)
    if glucose_logs and activity_logs:
        # Simple correlation: days with activity vs glucose
        activity_days = set()
        for log in activity_logs:
            try:
                dt = datetime.fromisoformat(log.timestamp.replace('Z', '+00:00'))
                activity_days.add(dt.date())
            except Exception:
                pass
        
        glucose_by_day = {}
        for log in glucose_logs:
            try:
                dt = datetime.fromisoformat(log.timestamp.replace('Z', '+00:00'))
                day = dt.date()
                if day not in glucose_by_day:
                    glucose_by_day[day] = []
                glucose_by_day[day].append(log.reading_mg_dl)
            except Exception:
                pass
        
        if activity_days and glucose_by_day:
            active_day_readings = []
            inactive_day_readings = []
            
            for day, readings in glucose_by_day.items():
                avg_reading = sum(readings) / len(readings)
                if day in activity_days:
                    active_day_readings.append(avg_reading)
                else:
                    inactive_day_readings.append(avg_reading)
            
            if active_day_readings and inactive_day_readings:
                active_avg = sum(active_day_readings) / len(active_day_readings)
                inactive_avg = sum(inactive_day_readings) / len(inactive_day_readings)
                difference = inactive_avg - active_avg
                
                if difference > 10:  # Significant difference
                    insights.append(
                        LifestyleInsight(
                            title="Activity impact on glucose",
                            detail=f"On days with activity, your average glucose was {active_avg:.1f} mg/dL vs {inactive_avg:.1f} mg/dL on inactive days (difference: {difference:.1f} mg/dL). Regular activity appears to help lower your glucose levels.",
                        )
                    )

    # Weight analysis
    weight_logs_count = len(weight_logs)
    if weight_logs:
        # Convert all weights to kg for consistent analysis
        weights_kg = []
        for log in weight_logs:
            if log.unit.lower() == "lbs":
                weights_kg.append(log.weight * 0.453592)  # Convert lbs to kg
            else:
                weights_kg.append(log.weight)
        
        if weights_kg:
            current_weight = weights_kg[-1]  # Most recent
            if len(weights_kg) > 1:
                initial_weight = weights_kg[0]
                weight_change = current_weight - initial_weight
                weight_change_pct = (weight_change / initial_weight) * 100 if initial_weight > 0 else 0
                
                insights.append(
                    LifestyleInsight(
                        title="Weight tracking",
                        detail=f"Current weight: {current_weight:.1f} kg. Change over period: {weight_change:+.1f} kg ({weight_change_pct:+.1f}%).",
                    )
                )
                
                # Weight change recommendations
                if weight_change < -2:  # Lost more than 2kg
                    insights.append(
                        LifestyleInsight(
                            title="Weight loss",
                            detail=f"You've lost {abs(weight_change):.1f} kg. For Type 2 Diabetes, even 5-10% weight loss can significantly improve glucose control. Monitor for any unintended rapid weight loss.",
                        )
                    )
                elif weight_change > 2:  # Gained more than 2kg
                    insights.append(
                        LifestyleInsight(
                            title="Weight gain",
                            detail=f"You've gained {weight_change:.1f} kg. Weight gain can worsen insulin resistance. Consider reviewing diet and activity levels with your healthcare provider.",
                        )
                    )
            else:
                insights.append(
                    LifestyleInsight(
                        title="Weight tracking",
                        detail=f"Current weight: {current_weight:.1f} kg. Continue tracking to identify trends.",
                    )
                )
            
            # BMI calculation if we have height (we don't, but we can note it)
            # For now, just track weight trends

    # Medication adherence analysis
    medication_logs_count = len(medication_logs)
    if medication_logs and state.patient.medications:
        # Group by medication name
        med_frequency = {}
        for log in medication_logs:
            med_name = log.medication_name
            if med_name not in med_frequency:
                med_frequency[med_name] = 0
            med_frequency[med_name] += 1
        
        # Expected frequency (assuming daily for most diabetes meds)
        expected_days = state.days
        adherence_insights = []
        
        for med_name, logged_count in med_frequency.items():
            adherence_rate = (logged_count / expected_days) * 100 if expected_days > 0 else 0
            if adherence_rate < 70:
                adherence_insights.append(f"{med_name}: {adherence_rate:.0f}% adherence (target: ≥80%)")
        
        if adherence_insights:
            insights.append(
                LifestyleInsight(
                    title="Medication adherence",
                    detail="Lower adherence detected: " + " | ".join(adherence_insights) + ". Consistent medication timing is important for glucose control.",
                )
            )
        elif medication_logs_count >= expected_days * 0.8:
            insights.append(
                LifestyleInsight(
                    title="Medication adherence",
                    detail=f"Good medication logging observed ({medication_logs_count} logs over {state.days} days). Consistent medication adherence helps maintain stable glucose levels.",
                )
            )

    # Patient-aware personalized insights
    if state.patient.conditions:
        # Type 2 Diabetes specific insights
        if "Type 2 Diabetes" in state.patient.conditions or any("diabetes" in c.lower() for c in state.patient.conditions):
            if avg_glucose:
                if avg_glucose > 180:
                    insights.append(
                        LifestyleInsight(
                            title="Personalized recommendation",
                            detail=f"Your average glucose ({avg_glucose:.1f} mg/dL) is above the recommended target for Type 2 Diabetes (<180 mg/dL). Consider discussing medication adjustments with your healthcare provider, and focus on consistent meal timing and portion control.",
                        )
                    )
                elif avg_glucose < 100:
                    insights.append(
                        LifestyleInsight(
                            title="Personalized recommendation",
                            detail=f"Your average glucose ({avg_glucose:.1f} mg/dL) is quite low. If you're experiencing symptoms of hypoglycemia (shaking, sweating, confusion), check with your healthcare provider about medication timing or dosage.",
                        )
                    )
        
        # Hypertension considerations
        if "Hypertension" in state.patient.conditions or any("hypertension" in c.lower() or "high blood pressure" in c.lower() for c in state.patient.conditions):
            if activity_logs and total_minutes < (state.days * 20):
                insights.append(
                    LifestyleInsight(
                        title="Hypertension management",
                        detail="Regular physical activity (150+ minutes/week) can help manage both diabetes and hypertension. Consider increasing your activity level.",
                    )
                )
    
    # Medication-aware insights
    if state.patient.medications:
        # Insulin-specific insights
        if any("insulin" in m.lower() for m in state.patient.medications):
            if low_readings and readings is not None and readings.size > 0 and len(low_readings) > readings.size * 0.1:  # More than 10% low
                insights.append(
                    LifestyleInsight(
                        title="Insulin monitoring",
                        detail=f"You're experiencing low glucose readings ({len(low_readings)} instances). If on insulin, this may indicate the need to adjust timing or dosage. Always consult your healthcare provider before making changes.",
                    )
                )
        
        # Metformin-specific insights
        if any("metformin" in m.lower() for m in state.patient.medications):
            if avg_glucose and avg_glucose > 160:
                insights.append(
                    LifestyleInsight(
                        title="Medication effectiveness",
                        detail=f"While on Metformin, your average glucose is {avg_glucose:.1f} mg/dL. If consistently above target, discuss with your healthcare provider about potential medication adjustments or additional therapies.",
                    )
                )

    result = LifestyleAnalysisResult(
        avg_glucose=avg_glucose,
        latest_glucose=latest_glucose,
        latest_glucose_timestamp=latest_glucose_timestamp,
        glucose_readings_count=glucose_count,
        total_activity_minutes=total_minutes,
        meals_count=meals_count,
        weight_logs_count=weight_logs_count,
        medication_logs_count=medication_logs_count,
        insights=insights,
    )

    logger.info("Lifestyle analysis complete: %d insights, %d glucose readings, %d activity logs, %d meal logs",
               len(insights), glucose_count, len(activity_rows), meals_count)
    
    return result.model_dump()


