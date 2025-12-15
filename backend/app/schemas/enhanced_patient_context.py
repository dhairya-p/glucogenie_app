"""Enhanced patient context with recent logs and data."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel
from pydantic.config import ConfigDict

from app.schemas.patient_context import PatientContext
from app.schemas.pattern_analysis import PatternAnalysisResult
from app.core.constants import UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX


class RecentGlucoseReading(BaseModel):
    """Recent glucose reading."""
    reading: float
    timing: Optional[str] = None
    timestamp: str
    notes: Optional[str] = None


class RecentMealLog(BaseModel):
    """Recent meal log."""
    meal: str
    description: Optional[str] = None
    timestamp: str


class RecentMedicationLog(BaseModel):
    """Recent medication log entry."""
    medication_name: str
    quantity: Optional[str] = None
    timestamp: str
    notes: Optional[str] = None


class RecentActivityLog(BaseModel):
    """Recent activity log."""
    activity_type: str
    duration_minutes: int
    intensity: str
    timestamp: str


class RecentWeightLog(BaseModel):
    """Recent weight log."""
    weight: float
    unit: str
    timestamp: str


class EnhancedPatientContext(BaseModel):
    """Enhanced patient context with all demographic and recent log data.
    
    This context is fetched ONCE per request and shared across all agents
    to avoid redundant Supabase calls.
    """
    
    # Basic patient info (from PatientContext)
    patient: PatientContext
    
    # Recent logs (last 7-30 days, depending on use case)
    recent_glucose_readings: List[RecentGlucoseReading] = []
    recent_meal_logs: List[RecentMealLog] = []
    recent_medication_logs: List[RecentMedicationLog] = []
    recent_activity_logs: List[RecentActivityLog] = []
    recent_weight_logs: List[RecentWeightLog] = []
    
    # Summary statistics (pre-computed to avoid recalculation)
    latest_glucose: Optional[float] = None
    latest_glucose_timestamp: Optional[str] = None
    avg_glucose_7d: Optional[float] = None
    total_medication_logs_7d: int = 0
    total_meal_logs_7d: int = 0
    total_activity_minutes_7d: int = 0
    latest_weight: Optional[float] = None
    
    # Pattern analysis (computed on-demand)
    pattern_analysis: Optional[PatternAnalysisResult] = None
    
    # Metadata
    data_fetched_at: datetime
    days_of_history: int = 7  # Default to 7 days
    
    # Long-horizon summary text (e.g. last 30 days), computed once per request
    historical_summary: Optional[str] = None
    
    model_config = ConfigDict(extra="ignore")
    
    def get_summary_string(self) -> str:
        """Get a human-readable summary of patient context and recent data."""
        parts = []
        
        # Basic info
        if self.patient.full_name and self.patient.full_name != "there":
            parts.append(f"Name: {self.patient.full_name}")
        if self.patient.age:
            parts.append(f"Age: {self.patient.age}")
        if self.patient.sex:
            parts.append(f"Sex: {self.patient.sex}")
        if self.patient.ethnicity and self.patient.ethnicity != "Unknown":
            parts.append(f"Ethnicity: {self.patient.ethnicity}")
        if self.patient.height:
            parts.append(f"Height: {self.patient.height} cm")
        if self.patient.activity_level:
            parts.append(f"Activity Level: {self.patient.activity_level}")
        if self.patient.location:
            parts.append(f"Location: {self.patient.location}")
        
        # Medical info
        if self.patient.conditions:
            parts.append(f"Medical Conditions: {', '.join(self.patient.conditions)}")
        if self.patient.medications:
            parts.append(f"Medications: {', '.join(self.patient.medications)}")
        
        # Recent data summary
        if self.latest_glucose:
            parts.append(f"Latest Glucose: {self.latest_glucose:.0f} mg/dL")
        if self.avg_glucose_7d:
            parts.append(f"Average Glucose (7d): {self.avg_glucose_7d:.0f} mg/dL")
        if self.latest_weight:
            parts.append(f"Latest Weight: {self.latest_weight:.1f} kg")
        if self.total_medication_logs_7d > 0:
            parts.append(f"Medication Logs (7d): {self.total_medication_logs_7d}")
        if self.total_meal_logs_7d > 0:
            parts.append(f"Meal Logs (7d): {self.total_meal_logs_7d}")
        if self.total_activity_minutes_7d > 0:
            parts.append(f"Activity (7d): {self.total_activity_minutes_7d} minutes")
        
        # Add weight trend if available
        if len(self.recent_weight_logs) >= 2:
            weights_kg = []
            for wl in self.recent_weight_logs:
                weight_kg = wl.weight
                if wl.unit.lower() == "lbs":
                    weight_kg = weight_kg * 0.453592
                weights_kg.append(weight_kg)
            
            if weights_kg:
                first_weight = weights_kg[-1]  # Oldest
                last_weight = weights_kg[0]  # Most recent
                change = last_weight - first_weight
                if abs(change) > 0.1:
                    trend = "gained" if change > 0 else "lost"
                    parts.append(f"Weight Trend: {trend} {abs(change):.1f} kg over {self.days_of_history} days")
        
        # Add activity summary if available
        if self.recent_activity_logs:
            total_min = sum(a.duration_minutes for a in self.recent_activity_logs)
            avg_daily = total_min / self.days_of_history if self.days_of_history > 0 else 0
            parts.append(f"Activity Average: {avg_daily:.0f} min/day over {self.days_of_history} days")
        
        return "\n".join(parts)
    
    def get_recent_meals_string(self, limit: int = 10) -> str:
        """Get a formatted string of recent meals."""
        if not self.recent_meal_logs:
            return "No recent meals logged."
        
        from app.core.timezone_utils import parse_and_format_timestamp
        
        meals_list = []
        for meal in self.recent_meal_logs[:limit]:
            date_str = parse_and_format_timestamp(meal.timestamp)
            
            meal_desc = meal.meal
            if meal.description:
                meal_desc += f" ({meal.description})"
            meals_list.append(f"- {date_str}: {meal_desc}")
        
        return f"Recent Meals (last {len(self.recent_meal_logs[:limit])}):\n" + "\n".join(meals_list)
    
    def get_recent_medications_string(self, limit: int = 10) -> str:
        """Get a formatted string of recent medication logs."""
        if not self.recent_medication_logs:
            return "No recent medication logs."
        
        from app.core.timezone_utils import (
            parse_and_format_timestamp,
            get_today_start_singapore,
            get_singapore_timezone,
        )
        from datetime import datetime, timezone as tz
        
        meds_list = []
        today_meds = []
        today_start = get_today_start_singapore()
        
        for med in self.recent_medication_logs[:limit]:
            date_str = parse_and_format_timestamp(med.timestamp)
            
            # Check if this medication was taken today
            try:
                dt = datetime.fromisoformat(med.timestamp.replace(UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=tz.utc)
                dt_sg = dt.astimezone(get_singapore_timezone())
                if dt_sg >= today_start:
                    today_meds.append(med)
            except Exception:
                pass
            
            med_desc = med.medication_name
            if med.quantity:
                med_desc += f" - {med.quantity}"
            if med.notes:
                med_desc += f" ({med.notes})"
            meds_list.append(f"- {date_str}: {med_desc}")
        
        result = f"Recent Medication Logs (last {len(self.recent_medication_logs[:limit])}):\n" + "\n".join(meds_list)
        
        # Add today's medications summary if any
        if today_meds:
            today_list = []
            for med in today_meds:
                med_desc = med.medication_name
                if med.quantity:
                    med_desc += f" - {med.quantity}"
                today_list.append(med_desc)
            result += f"\n\nMedications taken TODAY: {', '.join(today_list)}"
        else:
            result += "\n\nNo medications logged for TODAY."
        
        return result
    
    def get_recent_weight_string(self, limit: int = 10) -> str:
        """Get a formatted string of recent weight logs with trend information."""
        if not self.recent_weight_logs:
            return "No recent weight logs."
        
        from app.core.timezone_utils import parse_and_format_timestamp
        
        weight_list = []
        weights_kg = []
        
        for weight_log in self.recent_weight_logs[:limit]:
            date_str = parse_and_format_timestamp(weight_log.timestamp)
            # Convert to kg for consistency
            weight_kg = weight_log.weight
            if weight_log.unit.lower() == "lbs":
                weight_kg = weight_kg * 0.453592
            weights_kg.append(weight_kg)
            weight_list.append(f"- {date_str}: {weight_kg:.1f} kg")
        
        result = f"Recent Weight Logs (last {len(self.recent_weight_logs[:limit])}):\n" + "\n".join(weight_list)
        
        # Add trend information if we have multiple logs
        if len(weights_kg) >= 2:
            first_weight = weights_kg[-1]  # Oldest (last in list since logs are ordered desc)
            last_weight = weights_kg[0]  # Most recent (first in list)
            change = last_weight - first_weight
            change_pct = (change / first_weight) * 100 if first_weight > 0 else 0
            
            if abs(change) > 0.1:  # Only show if significant change
                trend = "gained" if change > 0 else "lost"
                result += f"\n\nWeight Trend: {trend} {abs(change):.1f} kg ({abs(change_pct):.1f}%) over this period."
            else:
                result += f"\n\nWeight Trend: Stable (change: {change:+.1f} kg)."
        
        return result
    
    def get_recent_activity_string(self, limit: int = 10) -> str:
        """Get a formatted string of recent activity logs with summary."""
        if not self.recent_activity_logs:
            return "No recent activity logs."
        
        from app.core.timezone_utils import parse_and_format_timestamp
        
        activity_list = []
        total_minutes = 0
        intensity_counts = {}
        
        for activity_log in self.recent_activity_logs[:limit]:
            date_str = parse_and_format_timestamp(activity_log.timestamp)
            duration = activity_log.duration_minutes
            total_minutes += duration
            intensity = activity_log.intensity or "unknown"
            intensity_counts[intensity] = intensity_counts.get(intensity, 0) + 1
            
            activity_desc = activity_log.activity_type or "Activity"
            activity_list.append(f"- {date_str}: {activity_desc} ({duration} min, {intensity})")
        
        result = f"Recent Activity Logs (last {len(self.recent_activity_logs[:limit])}):\n" + "\n".join(activity_list)
        
        # Add summary
        avg_daily = total_minutes / len(self.recent_activity_logs[:limit]) if self.recent_activity_logs[:limit] else 0
        intensity_summary = ", ".join([f"{k}: {v}" for k, v in intensity_counts.items()])
        result += f"\n\nActivity Summary: Total {total_minutes} minutes, Average {avg_daily:.0f} min/session. Intensity breakdown: {intensity_summary}."
        
        return result
    
    def get_recent_glucose_string(self, limit: int = 10) -> str:
        """Get a formatted string of recent glucose readings with times in Singapore timezone."""
        if not self.recent_glucose_readings:
            return "No recent glucose readings logged."
        
        from app.core.timezone_utils import parse_and_format_timestamp
        
        glucose_list = []
        for reading in self.recent_glucose_readings[:limit]:
            # Format timestamp in Singapore timezone
            date_str = parse_and_format_timestamp(reading.timestamp, format_str="%Y-%m-%d %H:%M")
            
            reading_desc = f"{reading.reading:.1f} mg/dL"
            if reading.timing:
                reading_desc += f" ({reading.timing})"
            if reading.notes:
                reading_desc += f" - {reading.notes}"
            
            glucose_list.append(f"- {date_str} SGT: {reading_desc}")
        
        result = f"Recent Glucose Readings (last {len(self.recent_glucose_readings[:limit])}, times in Singapore timezone):\n" + "\n".join(glucose_list)
        
        # Add summary if available
        if self.latest_glucose and self.latest_glucose_timestamp:
            latest_time_str = parse_and_format_timestamp(self.latest_glucose_timestamp, format_str="%Y-%m-%d %H:%M")
            result += f"\n\nLatest Reading: {self.latest_glucose:.1f} mg/dL at {latest_time_str} SGT"
        if self.avg_glucose_7d:
            result += f"\nAverage (7 days): {self.avg_glucose_7d:.1f} mg/dL"
        
        return result

