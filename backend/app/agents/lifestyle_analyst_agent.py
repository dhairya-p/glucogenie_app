from __future__ import annotations

from typing import List, Optional
import logging

from datetime import datetime, timedelta, timezone as tz

import pandas as pd
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

from app.schemas.patient_context import PatientContext
from app.schemas.enhanced_patient_context import EnhancedPatientContext
from app.core.supabase_client import get_supabase_client
from app.core.timezone_utils import (
    get_singapore_now,
    get_singapore_timezone,
    get_today_start_singapore,
    format_singapore_datetime,
)
from app.core.constants import DEFAULT_HISTORY_DAYS, MAX_LOG_LIMIT, UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX
from app.schemas.pattern_analysis import PatternAnalysisResult

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
    meal: str
    description: Optional[str] = None
    # Note: carbs_g not in schema, but we can infer from meal name if needed


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
    If enhanced_context is provided, uses pre-fetched data to avoid redundant Supabase calls.
    Otherwise, fetches logs from Supabase using the provided user identifier.
    """

    patient: PatientContext
    user_id: str
    days: int = Field(
        default=7,
        description="Number of days of history to include in the analysis.",
    )
    enhanced_context: Optional[EnhancedPatientContext] = Field(
        default=None,
        description="Pre-fetched enhanced context with all logs. If provided, uses this data instead of fetching from Supabase.",
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
    top_insights: List[LifestyleInsight] = Field(default_factory=list, description="Top 2-3 insights for display")

    model_config = ConfigDict(extra="ignore")




@tool("analyze_lifestyle", return_direct=False)
def analyze_lifestyle(state: LifestyleState) -> dict:
    """Analyze glucose, activity, and meals for lifestyle insights.

    Uses pandas DataFrames under the hood to compute simple aggregates.
    This is intentionally lightweight; more advanced analysis can be added later.
    """

    insights: List[LifestyleInsight] = []

    # Use pre-fetched data if available (avoids redundant Supabase calls)
    if state.enhanced_context:
        # Convert enhanced context data to agent's internal format
        glucose_logs: List[GlucoseLog] = [
            GlucoseLog(
                timestamp=log.timestamp,
                reading_mg_dl=log.reading,
                timing=log.timing,
                notes=log.notes,
            )
            for log in state.enhanced_context.recent_glucose_readings
        ]
        
        activity_logs: List[ActivityLog] = [
            ActivityLog(
                timestamp=log.timestamp,
                minutes=log.duration_minutes,
                intensity=log.intensity,
            )
            for log in state.enhanced_context.recent_activity_logs
        ]
        
        meal_logs: List[MealLog] = [
            MealLog(
                timestamp=log.timestamp,
                meal=log.meal,
                description=log.description,
            )
            for log in state.enhanced_context.recent_meal_logs
        ]
        
        weight_logs: List[WeightLog] = [
            WeightLog(
                timestamp=log.timestamp,
                weight=log.weight,
                unit=log.unit,
                notes=None,  # Enhanced context doesn't include notes for weight
            )
            for log in state.enhanced_context.recent_weight_logs
        ]
        
        medication_logs: List[MedicationLog] = [
            MedicationLog(
                timestamp=log.timestamp,
                medication_name=log.medication_name,
                quantity=log.quantity,
                notes=log.notes,
            )
            for log in state.enhanced_context.recent_medication_logs
        ]
        
        logger.info(
            "Using pre-fetched data: %d glucose, %d meals, %d med logs, %d activities, %d weights",
            len(glucose_logs), len(meal_logs), len(medication_logs),
            len(activity_logs), len(weight_logs)
        )
    else:
        # Fallback: fetch from Supabase if enhanced_context not provided
        try:
            supabase = get_supabase_client()
        except Exception as exc:
            logger.error("Failed to create Supabase client: %s", exc, exc_info=True)
            return {"insights": [], "top_insights": [], "avg_glucose": None, "latest_glucose": None, "latest_glucose_timestamp": None, "glucose_readings_count": 0, "total_activity_minutes": 0, "meals_count": 0, "weight_logs_count": 0, "medication_logs_count": 0}
        
        # Time window cutoff - use Singapore timezone
        now = get_singapore_now()
        since = now - timedelta(days=state.days)
        since_iso = since.isoformat()

        # --- Fetch logs from Supabase -------------------------------------------------

        # Glucose logs - using 'glucose_readings' table
        try:
            glucose_rows = (
                supabase.table("glucose_readings")
                .select("*")
                .eq("user_id", state.user_id)
                .gte("created_at", since_iso)
                .execute()
                .data
                or []
            )
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
                        "meal": f"Meal ({row.get('timing', 'Unknown')})",
                        "description": f"Meal context: {row.get('timing')}",
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
                    meal=row.get("meal", ""),
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
        
        # Format timestamp for display (convert to Singapore timezone)
        try:
            dt = datetime.fromisoformat(latest_glucose_timestamp.replace(UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX))
            formatted_timestamp = format_singapore_datetime(dt, "%B %d, %Y at %I:%M %p")
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
        
        # Analyze meal patterns based on meal names
        meal_names = df_meals["meal"].value_counts().head(5).to_dict()
        meal_summary = ", ".join([f"{k}: {v}x" for k, v in meal_names.items()])
        
        # Format recent meals list for detailed responses
        recent_meals_list = []
        for meal in meal_logs[:10]:  # Last 10 meals
            try:
                dt = datetime.fromisoformat(meal.timestamp.replace(UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX))
                date_str = format_singapore_datetime(dt)
            except Exception:
                date_str = meal.timestamp[:16] if len(meal.timestamp) > 16 else meal.timestamp
            meal_desc = meal.meal
            if meal.description:
                meal_desc += f" ({meal.description})"
            recent_meals_list.append(f"{date_str}: {meal_desc}")
        
        recent_meals_str = "\n".join(recent_meals_list)
        
        insights.append(
            LifestyleInsight(
                title="Meal tracking",
                detail=f"You've logged {meals_count} meals in the last {state.days} days. Top meals: {meal_summary}. Recent meals:\n{recent_meals_str}",
            )
        )
        
        # Meal frequency analysis
        if meals_count >= state.days:
            avg_meals_per_day = meals_count / state.days if state.days > 0 else 0
            insights.append(
                LifestyleInsight(
                    title="Meal frequency",
                    detail=f"Average {avg_meals_per_day:.1f} meals per day. Consistent meal timing can help stabilize glucose levels.",
                )
            )
        
        # Check if we have descriptions that might contain carb info
        descriptions_with_carbs = df_meals[df_meals["description"].notna() & df_meals["description"].str.contains("carb|g|gram", case=False, na=False)]
        if len(descriptions_with_carbs) > 0:
            insights.append(
                LifestyleInsight(
                    title="Meal details",
                    detail="Some meals include detailed descriptions. Consider adding carbohydrate information to better track glucose impact.",
                )
            )
    
    # Cross-correlation insights (glucose + activity + meals)
    if glucose_logs and activity_logs:
        # Simple correlation: days with activity vs glucose
        activity_days = set()
        for log in activity_logs:
            try:
                dt = datetime.fromisoformat(log.timestamp.replace(UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX))
                activity_days.add(dt.date())
            except Exception:
                pass
        
        glucose_by_day = {}
        for log in glucose_logs:
            try:
                dt = datetime.fromisoformat(log.timestamp.replace(UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX))
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
            
            # BMI calculation if we have height
            if weights_kg and state.patient.height and state.patient.height > 0:
                current_weight = weights_kg[-1]
                height_m = state.patient.height / 100.0  # Convert cm to meters
                bmi = current_weight / (height_m * height_m)
                
                bmi_category = ""
                if bmi < 18.5:
                    bmi_category = "underweight"
                elif bmi < 25:
                    bmi_category = "normal weight"
                elif bmi < 30:
                    bmi_category = "overweight"
                else:
                    bmi_category = "obese"
                
                insights.append(
                    LifestyleInsight(
                        title="BMI analysis",
                        detail=f"Your BMI is {bmi:.1f} ({bmi_category}). For diabetes management, maintaining a healthy weight (BMI 18.5-25) can improve glucose control and reduce complications.",
                    )
                )
                
                if bmi >= 25 and "Type 2 Diabetes" in state.patient.conditions:
                    insights.append(
                        LifestyleInsight(
                            title="Weight management for diabetes",
                            detail=f"With a BMI of {bmi:.1f}, losing 5-10% of your body weight can significantly improve insulin sensitivity and glucose control. Consider working with your healthcare provider on a weight management plan.",
                        )
                    )

    # Medication adherence analysis
    medication_logs_count = len(medication_logs)
    if medication_logs:
        # Format recent medication logs list for detailed responses
        recent_meds_list = []
        for med in medication_logs[:10]:  # Last 10 medication logs
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(med.timestamp.replace(UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX))
                date_str = format_singapore_datetime(dt)
            except Exception:
                date_str = med.timestamp[:16] if len(med.timestamp) > 16 else med.timestamp
            med_desc = med.medication_name
            if med.quantity:
                med_desc += f" - {med.quantity}"
            if med.notes:
                med_desc += f" ({med.notes})"
            recent_meds_list.append(f"{date_str}: {med_desc}")
        
        recent_meds_str = "\n".join(recent_meds_list)
        
        if state.patient.medications:
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
                        detail="Lower adherence detected: " + " | ".join(adherence_insights) + ". Consistent medication timing is important for glucose control. Recent medication logs:\n" + recent_meds_str,
                    )
                )
            elif medication_logs_count >= expected_days * 0.8:
                insights.append(
                    LifestyleInsight(
                        title="Medication adherence",
                        detail=f"Good medication logging observed ({medication_logs_count} logs over {state.days} days). Recent medication logs:\n{recent_meds_str}",
                    )
                )
            else:
                # Even if adherence is okay, include the list
                insights.append(
                    LifestyleInsight(
                        title="Medication logs",
                        detail=f"You've logged {medication_logs_count} medications in the last {state.days} days. Recent medication logs:\n{recent_meds_str}",
                    )
                )
        else:
            # No medications in profile, but logs exist
            insights.append(
                LifestyleInsight(
                    title="Medication logs",
                    detail=f"You've logged {medication_logs_count} medications in the last {state.days} days. Recent medication logs:\n{recent_meds_str}",
                )
            )
        
        # Add specific insight for "Have I taken my medication?" type questions
        # Check if there are any logs from today
        if medication_logs:
            today_start = get_today_start_singapore()
            
            today_meds = []
            for med in medication_logs:
                try:
                    dt = datetime.fromisoformat(med.timestamp.replace(UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX))
                    # Convert UTC to Singapore timezone for comparison
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=tz.utc)
                    # Convert to Singapore timezone for comparison
                    dt_sg = dt.astimezone(get_singapore_timezone())
                    if dt_sg >= today_start:
                        today_meds.append(med)
                except Exception:
                    pass
            
            if today_meds:
                today_med_names = [med.medication_name for med in today_meds]
                insights.append(
                    LifestyleInsight(
                        title="Today's medication adherence",
                        detail=f"You have logged taking {len(today_meds)} medication(s) today: {', '.join(set(today_med_names))}. This indicates you have taken your medication today.",
                    )
                )
            else:
                insights.append(
                    LifestyleInsight(
                        title="Today's medication adherence",
                        detail="You have not logged taking any medications today. Based on your medication logs, it appears you have not taken your medication today, or you haven't logged it yet.",
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

    # Generate pattern-based insights if available
    if state.enhanced_context and state.enhanced_context.pattern_analysis:
        pattern_insights = _generate_pattern_insights(state.enhanced_context.pattern_analysis)
        insights.extend(pattern_insights)
    
    # Select top 2-3 insights for display (prioritize actionable, personalized insights)
    top_insights = _select_top_insights(insights)
    
    # Ensure at least one insight if we have any data
    if not top_insights and insights:
        # If no top insights selected but we have insights, use first few
        top_insights = insights[:3]
    elif not top_insights and not insights:
        # If no insights at all, check if we have any data to generate a basic insight
        if glucose_count > 0:
            top_insights = [
                LifestyleInsight(
                    title="Getting started",
                    detail="Keep logging your glucose readings to get personalized insights!",
                )
            ]
        elif meals_count > 0 or medication_logs_count > 0 or len(activity_logs) > 0:
            top_insights = [
                LifestyleInsight(
                    title="Keep logging",
                    detail="Continue logging your data to receive personalized insights and recommendations.",
                )
            ]
    
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
        top_insights=top_insights,
    )

    # Serialize to dict, ensuring nested Pydantic models are converted
    result_dict = result.model_dump(mode='json')
    
    # Ensure top_insights are dicts (model_dump should handle this, but double-check)
    if "top_insights" in result_dict and result_dict["top_insights"]:
        top_insights_list = []
        for insight in result_dict["top_insights"]:
            if isinstance(insight, dict):
                top_insights_list.append(insight)
            else:
                # Handle Pydantic model (shouldn't happen with mode='json', but safety check)
                top_insights_list.append({
                    "title": getattr(insight, "title", ""),
                    "detail": getattr(insight, "detail", ""),
                })
        result_dict["top_insights"] = top_insights_list
    
    return result_dict


def _generate_pattern_insights(pattern_analysis) -> List[LifestyleInsight]:
    """Generate insights from pattern analysis."""
    from app.schemas.pattern_analysis import PatternAnalysisResult
    
    insights = []
    
    if not isinstance(pattern_analysis, PatternAnalysisResult):
        return insights
    
    # Circadian pattern insights
    if pattern_analysis.circadian_pattern:
        cp = pattern_analysis.circadian_pattern
        if cp.peak_hours and cp.low_hours:
            peak_str = ", ".join([f"{h}:00" for h in cp.peak_hours[:2]])
            low_str = ", ".join([f"{h}:00" for h in cp.low_hours[:2]])
            insights.append(
                LifestyleInsight(
                    title="Circadian glucose pattern",
                    detail=f"Your glucose tends to peak around {peak_str} and is lowest around {low_str}. Plan meals and activities accordingly.",
                )
            )
    
    # Best meals insight
    if pattern_analysis.meal_glucose_correlations and pattern_analysis.meal_glucose_correlations.best_meals:
        best_meals = ", ".join(pattern_analysis.meal_glucose_correlations.best_meals[:3])
        insights.append(
            LifestyleInsight(
                title="Best meals for glucose control",
                detail=f"Based on your data, these meals cause the smallest glucose spikes: {best_meals}. Consider including them more often.",
            )
        )
    
    # Medication timing insights
    if pattern_analysis.medication_effectiveness:
        for med_eff in pattern_analysis.medication_effectiveness:
            if med_eff.optimal_timing_hour is not None:
                insights.append(
                    LifestyleInsight(
                        title=f"Optimal timing for {med_eff.medication_name}",
                        detail=f"Your data suggests taking {med_eff.medication_name} around {med_eff.optimal_timing_hour}:00 may be most effective. Current adherence: {med_eff.adherence_rate:.0f}%.",
                    )
                )
    
    # Lifestyle consistency insights
    if pattern_analysis.lifestyle_consistency:
        lc = pattern_analysis.lifestyle_consistency
        if lc.areas_needing_improvement:
            areas = ", ".join(lc.areas_needing_improvement[:2])
            insights.append(
                LifestyleInsight(
                    title="Lifestyle consistency",
                    detail=f"Areas to focus on: {areas}. Improving consistency can help stabilize your glucose levels.",
                )
            )
    
    # Personalized targets
    if pattern_analysis.personalized_targets:
        pt = pattern_analysis.personalized_targets
        insights.append(
            LifestyleInsight(
                title="Personalized glucose target",
                detail=f"Your recommended glucose range is {pt.suggested_glucose_range_min:.0f}-{pt.suggested_glucose_range_max:.0f} mg/dL. {pt.rationale}",
            )
        )
    
    # Hypoglycemia risk
    if pattern_analysis.hypoglycemia_risk and pattern_analysis.hypoglycemia_risk.risk_score > 0.4:
        hr = pattern_analysis.hypoglycemia_risk
        factors = ", ".join(hr.contributing_factors[:2])
        insights.append(
            LifestyleInsight(
                title="Hypoglycemia risk alert",
                detail=f"Moderate risk of low glucose detected. Contributing factors: {factors}. Monitor closely and consider a snack.",
            )
        )
    
    return insights


def _select_top_insights(all_insights: List[LifestyleInsight]) -> List[LifestyleInsight]:
    """Select top 2-3 most actionable insights for display."""
    if len(all_insights) <= 3:
        return all_insights
    
    # Prioritize: risk alerts > personalized targets > pattern insights > general insights
    priority_keywords = {
        "risk": 4,
        "alert": 4,
        "personalized": 3,
        "optimal": 3,
        "best": 3,
        "pattern": 2,
        "circadian": 2,
        "consistency": 2,
    }
    
    def get_priority(insight: LifestyleInsight) -> int:
        title_lower = insight.title.lower()
        detail_lower = insight.detail.lower()
        text = title_lower + " " + detail_lower
        
        for keyword, priority in priority_keywords.items():
            if keyword in text:
                return priority
        return 1
    
    # Sort by priority and take top 3
    sorted_insights = sorted(all_insights, key=get_priority, reverse=True)
    return sorted_insights[:3]


