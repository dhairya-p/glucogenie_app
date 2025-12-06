"""Pattern analysis schemas for hyper-personalized insights."""
from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


class CircadianPattern(BaseModel):
    """Circadian glucose pattern analysis."""
    peak_hours: List[int] = Field(default_factory=list, description="Hours of day with highest average glucose (0-23)")
    low_hours: List[int] = Field(default_factory=list, description="Hours of day with lowest average glucose (0-23)")
    peak_avg_glucose: Optional[float] = None
    low_avg_glucose: Optional[float] = None
    pattern_stability: float = Field(default=0.0, description="Consistency score 0-1")


class MealGlucoseCorrelation(BaseModel):
    """Correlation between specific meals and glucose response."""
    meal_name: str
    avg_glucose_spike: float = Field(description="Average glucose increase after this meal")
    spike_duration_hours: float = Field(description="Hours until glucose returns to baseline")
    occurrences: int = Field(description="Number of times this meal was logged")
    is_high_spike: bool = Field(description="True if spike > 40 mg/dL")


class GlucoseMealCorrelationMatrix(BaseModel):
    """Matrix of glucose-meal correlations."""
    best_meals: List[str] = Field(default_factory=list, description="Meals with lowest glucose spikes")
    worst_meals: List[str] = Field(default_factory=list, description="Meals with highest glucose spikes")
    correlations: List[MealGlucoseCorrelation] = Field(default_factory=list)
    avg_spike_all_meals: Optional[float] = None


class MedicationTimingEffectiveness(BaseModel):
    """Analysis of medication timing and missed dose impact."""
    medication_name: str
    optimal_timing_hour: Optional[int] = Field(None, description="Best hour to take medication (0-23)")
    missed_dose_impact: Optional[float] = Field(None, description="Average glucose increase when dose is missed (mg/dL)")
    adherence_rate: float = Field(description="Percentage of doses taken on time")
    effectiveness_score: float = Field(default=0.0, description="0-1 score of medication effectiveness")


class GlucoseSpikePattern(BaseModel):
    """Patterns in glucose spikes."""
    avg_spike_magnitude: float = Field(description="Average spike size in mg/dL")
    spike_frequency: float = Field(description="Spikes per day")
    common_spike_times: List[int] = Field(default_factory=list, description="Hours when spikes commonly occur")
    spike_triggers: Dict[str, float] = Field(default_factory=dict, description="Trigger -> spike magnitude mapping")


class ActivityGlucoseCorrelation(BaseModel):
    """Correlation between activity and glucose."""
    activity_type: str
    avg_glucose_before: Optional[float] = None
    avg_glucose_after: Optional[float] = None
    glucose_change: float = Field(description="Average change in glucose after activity")
    optimal_timing_hour: Optional[int] = Field(None, description="Best hour for this activity type")


class WeightGlucoseCorrelation(BaseModel):
    """Correlation between weight changes and glucose."""
    weight_change_kg: float
    glucose_change_mg_dl: float
    correlation_strength: float = Field(description="Correlation coefficient -1 to 1")
    days_to_see_effect: int = Field(description="Days for weight change to affect glucose")


class HypoglycemiaRiskFactors(BaseModel):
    """Factors that predict imminent hypoglycemia."""
    risk_score: float = Field(description="0-1 risk score for hypoglycemia in next 24h")
    contributing_factors: List[str] = Field(default_factory=list)
    last_meal_hours_ago: Optional[float] = None
    recent_activity: bool = False
    medication_timing_risk: bool = False
    glucose_trend: str = Field(description="'decreasing', 'stable', 'increasing'")


class LifestyleConsistency(BaseModel):
    """Lifestyle consistency scoring."""
    overall_score: float = Field(description="0-1 consistency score")
    meal_timing_consistency: float = Field(description="Consistency of meal times")
    medication_timing_consistency: float = Field(description="Consistency of medication times")
    activity_consistency: float = Field(description="Consistency of activity patterns")
    areas_needing_improvement: List[str] = Field(default_factory=list)


class PersonalizedTargets(BaseModel):
    """Personalized targets for the user."""
    suggested_glucose_range_min: float = Field(description="Lower bound of target range")
    suggested_glucose_range_max: float = Field(description="Upper bound of target range")
    rationale: str = Field(description="Why these targets are recommended")
    best_meal_times: List[str] = Field(default_factory=list, description="Recommended meal times")
    best_activity_times: List[str] = Field(default_factory=list, description="Recommended activity times")
    medication_optimization: Dict[str, str] = Field(default_factory=dict, description="Medication -> optimal timing")


class PatternAnalysisResult(BaseModel):
    """Complete pattern analysis result."""
    circadian_pattern: Optional[CircadianPattern] = None
    meal_glucose_correlations: GlucoseMealCorrelationMatrix = Field(default_factory=GlucoseMealCorrelationMatrix)
    medication_effectiveness: List[MedicationTimingEffectiveness] = Field(default_factory=list)
    spike_patterns: Optional[GlucoseSpikePattern] = None
    activity_correlations: List[ActivityGlucoseCorrelation] = Field(default_factory=list)
    weight_correlations: Optional[WeightGlucoseCorrelation] = None
    hypoglycemia_risk: Optional[HypoglycemiaRiskFactors] = None
    lifestyle_consistency: Optional[LifestyleConsistency] = None
    personalized_targets: Optional[PersonalizedTargets] = None
    
    model_config = ConfigDict(extra="ignore")

