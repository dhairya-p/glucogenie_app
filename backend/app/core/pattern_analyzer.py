"""Pattern analysis engine for hyper-personalized insights."""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from app.core.constants import UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX
from app.core.timezone_utils import get_singapore_timezone, get_singapore_now
from app.schemas.enhanced_patient_context import EnhancedPatientContext
from app.schemas.pattern_analysis import (
    ActivityGlucoseCorrelation,
    CircadianPattern,
    GlucoseMealCorrelationMatrix,
    GlucoseSpikePattern,
    HypoglycemiaRiskFactors,
    LifestyleConsistency,
    MealGlucoseCorrelation,
    MedicationTimingEffectiveness,
    PatternAnalysisResult,
    PersonalizedTargets,
    WeightGlucoseCorrelation,
)

logger = logging.getLogger(__name__)


def analyze_patterns(context: EnhancedPatientContext) -> PatternAnalysisResult:
    """Analyze all patterns from enhanced patient context.
    
    Args:
        context: Enhanced patient context with recent logs
        
    Returns:
        PatternAnalysisResult with all analyzed patterns
    """
    logger.info("Starting pattern analysis for user")
    
    # 1. Circadian glucose patterns
    circadian = _analyze_circadian_patterns(context)
    
    # 2. Meal-glucose correlations
    meal_correlations = _analyze_meal_glucose_correlations(context)
    
    # 3. Medication timing effectiveness
    medication_effectiveness = _analyze_medication_timing(context)
    
    # 4. Glucose spike patterns
    spike_patterns = _analyze_glucose_spikes(context)
    
    # 5. Activity-glucose correlations
    activity_correlations = _analyze_activity_glucose_correlations(context)
    
    # 6. Weight-glucose correlations
    weight_correlations = _analyze_weight_glucose_correlation(context)
    
    # 7. Hypoglycemia risk factors
    hypoglycemia_risk = _analyze_hypoglycemia_risk(context)
    
    # 8. Lifestyle consistency
    lifestyle_consistency = _analyze_lifestyle_consistency(context)
    
    # 9. Personalized targets
    personalized_targets = _generate_personalized_targets(
        context, circadian, meal_correlations, medication_effectiveness, lifestyle_consistency
    )
    
    return PatternAnalysisResult(
        circadian_pattern=circadian,
        meal_glucose_correlations=meal_correlations,
        medication_effectiveness=medication_effectiveness,
        spike_patterns=spike_patterns,
        activity_correlations=activity_correlations,
        weight_correlations=weight_correlations,
        hypoglycemia_risk=hypoglycemia_risk,
        lifestyle_consistency=lifestyle_consistency,
        personalized_targets=personalized_targets,
    )


def _analyze_circadian_patterns(context: EnhancedPatientContext) -> Optional[CircadianPattern]:
    """Analyze circadian glucose patterns."""
    if not context.recent_glucose_readings:
        return None
    
    from datetime import timezone as tz
    
    # Group readings by hour of day
    hourly_readings: Dict[int, List[float]] = defaultdict(list)
    
    for reading in context.recent_glucose_readings:
        try:
            dt = datetime.fromisoformat(reading.timestamp.replace(UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz.utc)
            dt_sg = dt.astimezone(get_singapore_timezone())
            hour = dt_sg.hour
            hourly_readings[hour].append(reading.reading)
        except Exception:
            continue
    
    if not hourly_readings:
        return None
    
    # Calculate average glucose per hour
    hourly_avg: Dict[int, float] = {
        hour: sum(readings) / len(readings)
        for hour, readings in hourly_readings.items()
    }
    
    # Find peak and low hours (top 3 and bottom 3)
    sorted_hours = sorted(hourly_avg.items(), key=lambda x: x[1], reverse=True)
    peak_hours = [h for h, _ in sorted_hours[:3]]
    low_hours = [h for h, _ in sorted_hours[-3:]]
    
    peak_avg = hourly_avg[peak_hours[0]] if peak_hours else None
    low_avg = hourly_avg[low_hours[0]] if low_hours else None
    
    # Calculate pattern stability (lower std dev = more stable)
    all_avgs = list(hourly_avg.values())
    if len(all_avgs) > 1:
        mean_avg = sum(all_avgs) / len(all_avgs)
        variance = sum((x - mean_avg) ** 2 for x in all_avgs) / len(all_avgs)
        std_dev = variance ** 0.5
        # Normalize stability (lower std dev = higher stability, max at 50 mg/dL std dev)
        stability = max(0, 1 - (std_dev / 50))
    else:
        stability = 0.5
    
    return CircadianPattern(
        peak_hours=peak_hours,
        low_hours=low_hours,
        peak_avg_glucose=peak_avg,
        low_avg_glucose=low_avg,
        pattern_stability=stability,
    )


def _analyze_meal_glucose_correlations(context: EnhancedPatientContext) -> GlucoseMealCorrelationMatrix:
    """Analyze correlations between meals and glucose spikes."""
    if not context.recent_meal_logs or not context.recent_glucose_readings:
        return GlucoseMealCorrelationMatrix()
    
    from datetime import timezone as tz
    
    # Create time-indexed glucose readings
    glucose_by_time: Dict[datetime, float] = {}
    for reading in context.recent_glucose_readings:
        try:
            dt = datetime.fromisoformat(reading.timestamp.replace(UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz.utc)
            dt_sg = dt.astimezone(get_singapore_timezone())
            glucose_by_time[dt_sg] = reading.reading
        except Exception:
            continue
    
    # For each meal, find glucose readings 1-3 hours after
    meal_correlations: Dict[str, List[float]] = defaultdict(list)
    
    for meal in context.recent_meal_logs:
        try:
            meal_dt = datetime.fromisoformat(meal.timestamp.replace(UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX))
            if meal_dt.tzinfo is None:
                meal_dt = meal_dt.replace(tzinfo=tz.utc)
            meal_dt_sg = meal_dt.astimezone(get_singapore_timezone())
            
            # Find baseline (glucose before meal or at meal time)
            baseline = None
            for dt, glucose in sorted(glucose_by_time.items()):
                if dt <= meal_dt_sg:
                    baseline = glucose
                else:
                    break
            
            if baseline is None:
                continue
            
            # Find glucose 1-3 hours after meal
            meal_end = meal_dt_sg + timedelta(hours=3)
            post_meal_readings = [
                glucose for dt, glucose in glucose_by_time.items()
                if meal_dt_sg < dt <= meal_end
            ]
            
            if post_meal_readings:
                max_spike = max(post_meal_readings) - baseline
                meal_correlations[meal.meal].append(max_spike)
        except Exception:
            continue
    
    # Calculate average spikes per meal
    correlations = []
    for meal_name, spikes in meal_correlations.items():
        if spikes:
            avg_spike = sum(spikes) / len(spikes)
            correlations.append(MealGlucoseCorrelation(
                meal_name=meal_name,
                avg_glucose_spike=avg_spike,
                spike_duration_hours=2.0,  # Estimate
                occurrences=len(spikes),
                is_high_spike=avg_spike > 40,
            ))
    
    # Sort by spike magnitude
    correlations.sort(key=lambda x: x.avg_glucose_spike)
    
    best_meals = [c.meal_name for c in correlations[:5] if not c.is_high_spike]
    worst_meals = [c.meal_name for c in correlations[-5:] if c.is_high_spike]
    
    avg_spike_all = sum(c.avg_glucose_spike for c in correlations) / len(correlations) if correlations else None
    
    return GlucoseMealCorrelationMatrix(
        best_meals=best_meals,
        worst_meals=worst_meals,
        correlations=correlations,
        avg_spike_all_meals=avg_spike_all,
    )


def _analyze_medication_timing(context: EnhancedPatientContext) -> List[MedicationTimingEffectiveness]:
    """Analyze medication timing and missed dose impact."""
    if not context.recent_medication_logs or not context.patient.medications:
        return []
    
    from datetime import timezone as tz
    
    results = []
    
    for med_name in context.patient.medications:
        # Find medication logs for this medication
        med_logs = [
            log for log in context.recent_medication_logs
            if log.medication_name.lower() == med_name.lower()
        ]
        
        if not med_logs:
            continue
        
        # Calculate adherence (assuming daily medication)
        expected_doses = context.days_of_history
        actual_doses = len(med_logs)
        adherence_rate = (actual_doses / expected_doses) * 100 if expected_doses > 0 else 0
        
        # Find optimal timing (most common hour)
        timing_hours = []
        for log in med_logs:
            try:
                dt = datetime.fromisoformat(log.timestamp.replace(UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=tz.utc)
                dt_sg = dt.astimezone(get_singapore_timezone())
                timing_hours.append(dt_sg.hour)
            except Exception:
                continue
        
        optimal_timing = None
        if timing_hours:
            from collections import Counter
            hour_counts = Counter(timing_hours)
            optimal_timing = hour_counts.most_common(1)[0][0]
        
        # Calculate missed dose impact (compare glucose on days with vs without medication)
        if context.recent_glucose_readings and len(med_logs) > 0:
            # Simple heuristic: compare glucose on medication days vs non-medication days
            # This is a simplified analysis - real analysis would need more sophisticated matching
            missed_dose_impact = None  # Would need more data for accurate calculation
        else:
            missed_dose_impact = None
        
        # Effectiveness score based on adherence and glucose control
        effectiveness_score = min(1.0, adherence_rate / 100)
        
        results.append(MedicationTimingEffectiveness(
            medication_name=med_name,
            optimal_timing_hour=optimal_timing,
            missed_dose_impact=missed_dose_impact,
            adherence_rate=adherence_rate,
            effectiveness_score=effectiveness_score,
        ))
    
    return results


def _analyze_glucose_spikes(context: EnhancedPatientContext) -> Optional[GlucoseSpikePattern]:
    """Analyze glucose spike patterns."""
    if not context.recent_glucose_readings or len(context.recent_glucose_readings) < 2:
        return None
    
    from datetime import timezone as tz
    
    # Sort readings by time
    sorted_readings = sorted(
        context.recent_glucose_readings,
        key=lambda r: r.timestamp
    )
    
    spikes = []
    spike_times = []
    
    for i in range(1, len(sorted_readings)):
        try:
            prev_dt = datetime.fromisoformat(sorted_readings[i-1].timestamp.replace(UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX))
            curr_dt = datetime.fromisoformat(sorted_readings[i].timestamp.replace(UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX))
            
            if prev_dt.tzinfo is None:
                prev_dt = prev_dt.replace(tzinfo=tz.utc)
            if curr_dt.tzinfo is None:
                curr_dt = curr_dt.replace(tzinfo=tz.utc)
            
            prev_dt_sg = prev_dt.astimezone(get_singapore_timezone())
            curr_dt_sg = curr_dt.astimezone(get_singapore_timezone())
            
            time_diff = (curr_dt_sg - prev_dt_sg).total_seconds() / 3600  # hours
            
            if 0.5 <= time_diff <= 4:  # Within 4 hours
                spike = sorted_readings[i].reading - sorted_readings[i-1].reading
                if spike > 20:  # Significant spike
                    spikes.append(spike)
                    spike_times.append(curr_dt_sg.hour)
        except Exception:
            continue
    
    if not spikes:
        return None
    
    avg_spike = sum(spikes) / len(spikes)
    spike_freq = len(spikes) / context.days_of_history if context.days_of_history > 0 else 0
    
    # Most common spike times
    from collections import Counter
    common_times = [h for h, _ in Counter(spike_times).most_common(3)]
    
    return GlucoseSpikePattern(
        avg_spike_magnitude=avg_spike,
        spike_frequency=spike_freq,
        common_spike_times=common_times,
        spike_triggers={},  # Would need meal data correlation
    )


def _analyze_activity_glucose_correlations(context: EnhancedPatientContext) -> List[ActivityGlucoseCorrelation]:
    """Analyze correlations between activity and glucose."""
    if not context.recent_activity_logs or not context.recent_glucose_readings:
        return []
    
    from datetime import timezone as tz
    
    # Group activities by type
    activity_types = set(log.activity_type for log in context.recent_activity_logs)
    
    # Create time-indexed glucose readings
    glucose_by_time: Dict[datetime, float] = {}
    for reading in context.recent_glucose_readings:
        try:
            dt = datetime.fromisoformat(reading.timestamp.replace(UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz.utc)
            dt_sg = dt.astimezone(get_singapore_timezone())
            glucose_by_time[dt_sg] = reading.reading
        except Exception:
            continue
    
    correlations = []
    
    for activity_type in activity_types:
        activity_logs = [log for log in context.recent_activity_logs if log.activity_type == activity_type]
        
        before_readings = []
        after_readings = []
        activity_hours = []
        
        for activity in activity_logs:
            try:
                activity_dt = datetime.fromisoformat(activity.timestamp.replace(UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX))
                if activity_dt.tzinfo is None:
                    activity_dt = activity_dt.replace(tzinfo=tz.utc)
                activity_dt_sg = activity_dt.astimezone(get_singapore_timezone())
                activity_hours.append(activity_dt_sg.hour)
                
                # Find glucose before (within 1 hour before)
                before_window = activity_dt_sg - timedelta(hours=1)
                before_glucose = [
                    glucose for dt, glucose in glucose_by_time.items()
                    if before_window <= dt < activity_dt_sg
                ]
                if before_glucose:
                    before_readings.append(before_glucose[-1])  # Closest to activity
                
                # Find glucose after (1-3 hours after)
                after_window_start = activity_dt_sg + timedelta(hours=1)
                after_window_end = activity_dt_sg + timedelta(hours=3)
                after_glucose = [
                    glucose for dt, glucose in glucose_by_time.items()
                    if after_window_start <= dt <= after_window_end
                ]
                if after_glucose:
                    after_readings.append(after_glucose[0])  # First reading after
            except Exception:
                continue
        
        if before_readings and after_readings:
            avg_before = sum(before_readings) / len(before_readings)
            avg_after = sum(after_readings) / len(after_readings)
            change = avg_after - avg_before
            
            # Optimal timing (most common hour)
            optimal_timing = None
            if activity_hours:
                from collections import Counter
                optimal_timing = Counter(activity_hours).most_common(1)[0][0]
            
            correlations.append(ActivityGlucoseCorrelation(
                activity_type=activity_type,
                avg_glucose_before=avg_before,
                avg_glucose_after=avg_after,
                glucose_change=change,
                optimal_timing_hour=optimal_timing,
            ))
    
    return correlations


def _analyze_weight_glucose_correlation(context: EnhancedPatientContext) -> Optional[WeightGlucoseCorrelation]:
    """Analyze correlation between weight changes and glucose."""
    if not context.recent_weight_logs or len(context.recent_weight_logs) < 2:
        return None
    
    if not context.recent_glucose_readings or len(context.recent_glucose_readings) < 2:
        return None
    
    # Convert weights to kg and sort by time
    weights_kg = []
    for wl in context.recent_weight_logs:
        weight_kg = wl.weight
        if wl.unit.lower() == "lbs":
            weight_kg = weight_kg * 0.453592
        weights_kg.append((wl.timestamp, weight_kg))
    
    weights_kg.sort(key=lambda x: x[0])
    
    if len(weights_kg) < 2:
        return None
    
    weight_change = weights_kg[-1][1] - weights_kg[0][1]
    
    # Calculate average glucose change over same period
    sorted_glucose = sorted(context.recent_glucose_readings, key=lambda r: r.timestamp)
    if len(sorted_glucose) < 2:
        return None
    
    early_glucose = sorted_glucose[:len(sorted_glucose)//2]
    late_glucose = sorted_glucose[len(sorted_glucose)//2:]
    
    early_avg = sum(r.reading for r in early_glucose) / len(early_glucose)
    late_avg = sum(r.reading for r in late_glucose) / len(late_glucose)
    glucose_change = late_avg - early_avg
    
    # Simple correlation (would need more sophisticated analysis for real correlation)
    correlation = -0.3 if weight_change < 0 else 0.2  # Simplified
    
    return WeightGlucoseCorrelation(
        weight_change_kg=weight_change,
        glucose_change_mg_dl=glucose_change,
        correlation_strength=correlation,
        days_to_see_effect=context.days_of_history,
    )


def _analyze_hypoglycemia_risk(context: EnhancedPatientContext) -> Optional[HypoglycemiaRiskFactors]:
    """Analyze risk factors for imminent hypoglycemia."""
    if not context.recent_glucose_readings:
        return None
    
    from datetime import timezone as tz
    
    factors = []
    risk_score = 0.0
    
    # Check recent low readings
    recent_lows = [r for r in context.recent_glucose_readings[:5] if r.reading < 80]
    if recent_lows:
        risk_score += 0.3
        factors.append("Recent low glucose readings")
    
    # Check glucose trend
    if len(context.recent_glucose_readings) >= 3:
        recent_avg = sum(r.reading for r in context.recent_glucose_readings[:3]) / 3
        earlier_avg = sum(r.reading for r in context.recent_glucose_readings[3:6]) / 3 if len(context.recent_glucose_readings) >= 6 else recent_avg
        if recent_avg < earlier_avg - 10:
            risk_score += 0.2
            factors.append("Decreasing glucose trend")
            trend = "decreasing"
        elif recent_avg > earlier_avg + 10:
            trend = "increasing"
        else:
            trend = "stable"
    else:
        trend = "stable"
    
    # Check last meal timing
    if context.recent_meal_logs:
        try:
            last_meal_dt = datetime.fromisoformat(context.recent_meal_logs[0].timestamp.replace(UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX))
            if last_meal_dt.tzinfo is None:
                last_meal_dt = last_meal_dt.replace(tzinfo=tz.utc)
            last_meal_dt_sg = last_meal_dt.astimezone(get_singapore_timezone())
            now = get_singapore_now()
            hours_since_meal = (now - last_meal_dt_sg).total_seconds() / 3600
            
            if hours_since_meal > 6:
                risk_score += 0.2
                factors.append("Long time since last meal")
        except Exception:
            hours_since_meal = None
    else:
        hours_since_meal = None
    
    # Check recent activity
    if context.recent_activity_logs:
        try:
            last_activity_dt = datetime.fromisoformat(context.recent_activity_logs[0].timestamp.replace(UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX))
            if last_activity_dt.tzinfo is None:
                last_activity_dt = last_activity_dt.replace(tzinfo=tz.utc)
            last_activity_dt_sg = last_activity_dt.astimezone(get_singapore_timezone())
            now = get_singapore_now()
            hours_since_activity = (now - last_activity_dt_sg).total_seconds() / 3600
            
            if hours_since_activity < 4:  # Recent activity
                risk_score += 0.15
                factors.append("Recent physical activity")
                recent_activity = True
            else:
                recent_activity = False
        except Exception:
            recent_activity = False
    else:
        recent_activity = False
    
    # Check medication timing
    medication_timing_risk = False
    if context.recent_medication_logs and context.patient.medications:
        # Check if insulin was taken recently without meal
        insulin_logs = [log for log in context.recent_medication_logs if "insulin" in log.medication_name.lower()]
        if insulin_logs:
            try:
                last_insulin_dt = datetime.fromisoformat(insulin_logs[0].timestamp.replace(UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX))
                if last_insulin_dt.tzinfo is None:
                    last_insulin_dt = last_insulin_dt.replace(tzinfo=tz.utc)
                last_insulin_dt_sg = last_insulin_dt.astimezone(get_singapore_timezone())
                
                # Check if meal was taken after insulin
                if context.recent_meal_logs:
                    last_meal_dt = datetime.fromisoformat(context.recent_meal_logs[0].timestamp.replace(UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX))
                    if last_meal_dt.tzinfo is None:
                        last_meal_dt = last_meal_dt.replace(tzinfo=tz.utc)
                    last_meal_dt_sg = last_meal_dt.astimezone(get_singapore_timezone())
                    
                    if last_insulin_dt_sg > last_meal_dt_sg:
                        risk_score += 0.15
                        factors.append("Insulin taken without recent meal")
                        medication_timing_risk = True
            except Exception:
                pass
    
    risk_score = min(1.0, risk_score)
    
    return HypoglycemiaRiskFactors(
        risk_score=risk_score,
        contributing_factors=factors,
        last_meal_hours_ago=hours_since_meal,
        recent_activity=recent_activity,
        medication_timing_risk=medication_timing_risk,
        glucose_trend=trend,
    )


def _analyze_lifestyle_consistency(context: EnhancedPatientContext) -> Optional[LifestyleConsistency]:
    """Analyze lifestyle consistency."""
    if not context.recent_meal_logs and not context.recent_medication_logs and not context.recent_activity_logs:
        return None
    
    from datetime import timezone as tz
    
    areas_needing_improvement = []
    
    # Meal timing consistency
    meal_consistency = 0.5
    meal_timing_scores = []
    if context.recent_meal_logs:
        meal_times = []
        for meal in context.recent_meal_logs:
            try:
                dt = datetime.fromisoformat(meal.timestamp.replace(UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=tz.utc)
                dt_sg = dt.astimezone(get_singapore_timezone())
                meal_times.append(dt_sg.hour * 60 + dt_sg.minute)  # Minutes since midnight
            except Exception:
                continue
        
        if len(meal_times) >= 2:
            # Calculate variance in meal times
            mean_time = sum(meal_times) / len(meal_times)
            variance = sum((t - mean_time) ** 2 for t in meal_times) / len(meal_times)
            std_dev = variance ** 0.5
            # Normalize (lower std dev = higher consistency, max at 120 minutes)
            meal_consistency = max(0, 1 - (std_dev / 120))
            meal_timing_scores.append(meal_consistency)
            
            if meal_consistency < 0.6:
                areas_needing_improvement.append("Meal timing consistency")
    else:
        meal_consistency = 0.5
        areas_needing_improvement.append("Regular meal logging")
    
    # Medication timing consistency
    medication_consistency = 0.5
    if context.recent_medication_logs:
        med_times = []
        for med in context.recent_medication_logs:
            try:
                dt = datetime.fromisoformat(med.timestamp.replace(UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=tz.utc)
                dt_sg = dt.astimezone(get_singapore_timezone())
                med_times.append(dt_sg.hour * 60 + dt_sg.minute)
            except Exception:
                continue
        
        if len(med_times) >= 2:
            mean_time = sum(med_times) / len(med_times)
            variance = sum((t - mean_time) ** 2 for t in med_times) / len(med_times)
            std_dev = variance ** 0.5
            medication_consistency = max(0, 1 - (std_dev / 120))
            
            if medication_consistency < 0.6:
                areas_needing_improvement.append("Medication timing consistency")
    else:
        areas_needing_improvement.append("Regular medication logging")
    
    # Activity consistency
    activity_consistency = 0.5
    if context.recent_activity_logs:
        activity_days = set()
        for activity in context.recent_activity_logs:
            try:
                dt = datetime.fromisoformat(activity.timestamp.replace(UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=tz.utc)
                dt_sg = dt.astimezone(get_singapore_timezone())
                activity_days.add(dt_sg.date())
            except Exception:
                continue
        
        # Consistency = percentage of days with activity
        activity_consistency = len(activity_days) / context.days_of_history if context.days_of_history > 0 else 0
        
        if activity_consistency < 0.5:
            areas_needing_improvement.append("Regular physical activity")
    else:
        areas_needing_improvement.append("Activity logging")
    
    # Overall score
    overall_score = (meal_consistency + medication_consistency + activity_consistency) / 3
    
    return LifestyleConsistency(
        overall_score=overall_score,
        meal_timing_consistency=meal_consistency,
        medication_timing_consistency=medication_consistency,
        activity_consistency=activity_consistency,
        areas_needing_improvement=areas_needing_improvement,
    )


def _generate_personalized_targets(
    context: EnhancedPatientContext,
    circadian: Optional[CircadianPattern],
    meal_correlations: GlucoseMealCorrelationMatrix,
    medication_effectiveness: List[MedicationTimingEffectiveness],
    lifestyle_consistency: Optional[LifestyleConsistency],
) -> Optional[PersonalizedTargets]:
    """Generate personalized targets based on analysis."""
    if not context.recent_glucose_readings:
        return None
    
    # Calculate suggested glucose range based on current readings
    readings = [r.reading for r in context.recent_glucose_readings]
    avg_glucose = sum(readings) / len(readings)
    
    # Adjust range based on age, conditions, and current control
    if "Type 2 Diabetes" in context.patient.conditions:
        if avg_glucose < 140:
            # Good control - tighter range
            range_min = 80
            range_max = 140
            rationale = "Your glucose control is good. Maintaining 80-140 mg/dL will help prevent complications."
        else:
            # Need improvement - slightly wider range
            range_min = 80
            range_max = 180
            rationale = "Your glucose levels are elevated. Aim for 80-180 mg/dL initially, then work toward 80-140 mg/dL with your healthcare provider."
    else:
        range_min = 70
        range_max = 140
        rationale = "Standard target range for diabetes management."
    
    # Best meal times based on circadian patterns
    best_meal_times = []
    if circadian and circadian.low_hours:
        for hour in circadian.low_hours[:2]:  # Top 2 low hours
            best_meal_times.append(f"{hour}:00")
    
    if not best_meal_times:
        best_meal_times = ["08:00", "12:00", "18:00"]  # Default
    
    # Best activity times (avoid peak glucose hours)
    best_activity_times = []
    if circadian and circadian.peak_hours:
        # Suggest activity 1-2 hours before peak
        for peak_hour in circadian.peak_hours[:2]:
            activity_hour = (peak_hour - 2) % 24
            best_activity_times.append(f"{activity_hour}:00")
    
    if not best_activity_times:
        best_activity_times = ["06:00", "18:00"]  # Default
    
    # Medication optimization
    medication_optimization = {}
    for med_eff in medication_effectiveness:
        if med_eff.optimal_timing_hour is not None:
            medication_optimization[med_eff.medication_name] = f"{med_eff.optimal_timing_hour}:00"
    
    return PersonalizedTargets(
        suggested_glucose_range_min=range_min,
        suggested_glucose_range_max=range_max,
        rationale=rationale,
        best_meal_times=best_meal_times,
        best_activity_times=best_activity_times,
        medication_optimization=medication_optimization,
    )

