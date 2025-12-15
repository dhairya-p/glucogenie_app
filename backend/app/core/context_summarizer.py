"""Utilities to build a longer-horizon patient summary from EnhancedPatientContext.

This is a lightweight, deterministic summarizer that:
- Reuses existing fields from EnhancedPatientContext
- Avoids calling agents (e.g. analyze_lifestyle) or duplicating /api/insights logic
- Produces a compact text block suitable for:
  - System prompts in the chatbot
  - Future /api/context responses
"""

from __future__ import annotations

from typing import List

from app.schemas.enhanced_patient_context import EnhancedPatientContext


def summarize_enhanced_context(enhanced: EnhancedPatientContext) -> str:
    """Build a longer-horizon summary string for a patient.

    The goal is to compress the most important demographics, conditions,
    medications, and high-level behavioural patterns over the last N days
    (where N = enhanced.days_of_history) into a single text block.

    This reuses existing fields and helper methods on EnhancedPatientContext
    and does NOT call the lifestyle agent or /api/insights.
    """
    parts: List[str] = []

    # Base demographic + medical summary (already aggregated)
    base_summary = enhanced.get_summary_string()
    if base_summary:
        parts.append(f"Overall Profile (last {enhanced.days_of_history} days):\n{base_summary}")

    # High-level usage of recent logs: counts only (no heavy per-event analysis here)
    # We keep this short and aggregate-style to save tokens.
    log_summaries: List[str] = []

    if enhanced.recent_glucose_readings:
        log_summaries.append(
            f"- Glucose readings logged: {len(enhanced.recent_glucose_readings)} "
            f"(avg ~{enhanced.avg_glucose_7d:.0f} mg/dL over this period)"
            if enhanced.avg_glucose_7d
            else f"- Glucose readings logged: {len(enhanced.recent_glucose_readings)}"
        )

    if enhanced.recent_meal_logs:
        log_summaries.append(
            f"- Meals logged: {len(enhanced.recent_meal_logs)} "
            f"(showing patterns over ~{enhanced.days_of_history} days)"
        )

    if enhanced.recent_medication_logs:
        log_summaries.append(
            f"- Medication logs: {len(enhanced.recent_medication_logs)} "
            "(helps assess adherence patterns, not real-time dosing advice)"
        )

    if enhanced.recent_activity_logs:
        log_summaries.append(
            f"- Activity sessions logged: {len(enhanced.recent_activity_logs)} "
            f"(total {enhanced.total_activity_minutes_7d} minutes in this window)"
        )

    if enhanced.recent_weight_logs:
        log_summaries.append(
            f"- Weight logs: {len(enhanced.recent_weight_logs)} "
            "(used to track longer-term weight trend)"
        )

    if log_summaries:
        parts.append("Longer-Horizon Data Coverage:\n" + "\n".join(log_summaries))

    # Optional: tuck in 1–2 key pattern analysis highlights if available,
    # but keep it much shorter than the full pattern_analysis block used in system_prompt_builder.
    if enhanced.pattern_analysis:
        pa = enhanced.pattern_analysis
        pattern_bits: List[str] = []

        if pa.personalized_targets:
            pt = pa.personalized_targets
            pattern_bits.append(
                f"- Personalized glucose target range about "
                f"{pt.suggested_glucose_range_min:.0f}-{pt.suggested_glucose_range_max:.0f} mg/dL "
                f"based on your recent patterns."
            )

        if pa.circadian_pattern and pa.circadian_pattern.peak_hours:
            peak_hours = ", ".join(f"{h}:00" for h in pa.circadian_pattern.peak_hours[:2])
            pattern_bits.append(f"- Glucose tends to peak around {peak_hours} on many days.")

        if pa.meal_glucose_correlations and pa.meal_glucose_correlations.best_meals:
            best_meals = ", ".join(pa.meal_glucose_correlations.best_meals[:3])
            pattern_bits.append(f"- Best glucose-friendly meals so far: {best_meals}.")

        if pa.lifestyle_consistency and pa.lifestyle_consistency.areas_needing_improvement:
            areas = ", ".join(pa.lifestyle_consistency.areas_needing_improvement[:2])
            pattern_bits.append(f"- Areas to improve consistency: {areas}.")

        if pattern_bits:
            parts.append("Longer-Term Pattern Highlights:\n" + "\n".join(pattern_bits))

    return "\n\n".join(parts).strip()

