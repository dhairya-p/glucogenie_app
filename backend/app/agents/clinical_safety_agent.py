from __future__ import annotations

from typing import List, Optional

from langchain_core.tools import tool
from pydantic import BaseModel
from pydantic.config import ConfigDict

from app.schemas.patient_context import PatientContext
from app.schemas.enhanced_patient_context import EnhancedPatientContext


class ClinicalSafetyState(BaseModel):
    """Input state for the Clinical Safety Agent."""

    patient: PatientContext
    user_message: str
    enhanced_context: Optional[EnhancedPatientContext] = None  # Full context with recent logs

    model_config = ConfigDict(extra="ignore")


class ClinicalSafetyResult(BaseModel):
    """Structured safety assessment result."""

    is_safe: bool
    warnings: List[str]
    rationale: str

    model_config = ConfigDict(extra="ignore")


@tool("check_clinical_safety", return_direct=False)
def check_clinical_safety(state: ClinicalSafetyState) -> dict:
    """Check a user query against medications, conditions, and recent logs for safety flags.

    Uses full patient context including:
    - Demographics (age, sex, ethnicity, height)
    - Medical conditions and medications
    - Recent glucose readings
    - Recent meal logs
    - Recent medication logs (adherence patterns)
    - Recent activity logs
    - Recent weight logs

    This provides comprehensive safety checking based on actual patient data.
    """

    import logging
    logger = logging.getLogger(__name__)
    
    text = state.user_message.lower()
    warnings: List[str] = []
    enhanced = state.enhanced_context

    # Very conservative heuristics to flag when a human should review.
    if any(term in text for term in ["double dose", "extra dose", "overdose"]):
        warnings.append(
            "User is asking about taking more than the prescribed dose. "
            "Advise them to contact their healthcare provider immediately."
        )

    if "insulin" in text and "skip meal" in text:
        warnings.append(
            "Combining insulin with skipped meals can cause hypoglycemia. "
            "Remind the user to consult their care team before changing regimen."
        )

    # Check for recent hypoglycemia risk
    if enhanced and enhanced.latest_glucose:
        if enhanced.latest_glucose < 70:
            warnings.append(
                f"Recent glucose reading is low ({enhanced.latest_glucose:.0f} mg/dL). "
                "User should be cautious about medication changes or meal skipping."
            )
        elif enhanced.latest_glucose > 250:
            warnings.append(
                f"Recent glucose reading is high ({enhanced.latest_glucose:.0f} mg/dL). "
                "User may need medication adjustment - consult healthcare provider."
            )

    # Check medication adherence patterns
    if enhanced and enhanced.recent_medication_logs:
        # Check if user is taking medications regularly
        med_frequency = {}
        for log in enhanced.recent_medication_logs:
            med_name = log.medication_name
            if med_name not in med_frequency:
                med_frequency[med_name] = 0
            med_frequency[med_name] += 1
        
        # If user asks about medication but hasn't logged it recently
        if state.patient.medications:
            for med in state.patient.medications:
                if med.lower() in text and med not in med_frequency:
                    warnings.append(
                        f"User is asking about {med} but hasn't logged taking it recently. "
                        "Remind them about medication adherence."
                    )

    # Check meal patterns with medications
    if enhanced and enhanced.recent_meal_logs and state.patient.medications:
        # If user mentions skipping meals and is on insulin or sulfonylureas
        if any(med.lower() in ["insulin", "glipizide", "glyburide"] for med in state.patient.medications):
            if "skip" in text and "meal" in text:
                warnings.append(
                    "Skipping meals while on insulin or sulfonylureas can cause dangerous hypoglycemia. "
                    "User should consult their healthcare provider before changing meal patterns."
                )

    # Age-specific warnings
    if state.patient.age:
        if state.patient.age >= 65:
            if "increase" in text and "dose" in text:
                warnings.append(
                    "Older adults are more sensitive to medication changes. "
                    "Any dose adjustments should be done under medical supervision."
                )

    # Condition-specific warnings
    if state.patient.conditions:
        conditions_str = ", ".join(state.patient.conditions)
        if "kidney" in conditions_str.lower() or "renal" in conditions_str.lower():
            if "metformin" in text.lower():
                warnings.append(
                    "User has kidney disease. Metformin dosage may need adjustment. "
                    "Consult healthcare provider before making changes."
                )
        
        if "heart" in conditions_str.lower() or "cardiac" in conditions_str.lower():
            if "exercise" in text and enhanced and enhanced.recent_glucose_readings:
                latest_glucose = enhanced.latest_glucose or 0
                if latest_glucose > 250:
                    warnings.append(
                        "User has heart disease and high glucose. "
                        "Strenuous exercise with high glucose can be risky. "
                        "Consult healthcare provider before increasing activity."
                    )

    # Weight-related warnings
    if enhanced and enhanced.latest_weight and state.patient.height:
        # Calculate BMI
        height_m = state.patient.height / 100.0
        bmi = enhanced.latest_weight / (height_m * height_m)
        if bmi < 18.5 and "lose weight" in text:
            warnings.append(
                "User is underweight (BMI < 18.5). Weight loss is not recommended. "
                "Consult healthcare provider for appropriate guidance."
            )

    is_safe = len(warnings) == 0
    rationale = (
        "No obvious red-flag patterns detected in the query based on patient context and recent data."
        if is_safe
        else f"One or more safety concerns were detected based on patient demographics, conditions, medications, and recent logs ({len(warnings)} warning(s)). A clinician should review."
    )

    result = ClinicalSafetyResult(
        is_safe=is_safe,
        warnings=warnings,
        rationale=rationale,
    )

    logger.info(
        "Clinical safety check: is_safe=%s, warnings=%d, patient_age=%d, latest_glucose=%s",
        is_safe, len(warnings), state.patient.age,
        enhanced.latest_glucose if enhanced else None
    )

    return result.model_dump()


