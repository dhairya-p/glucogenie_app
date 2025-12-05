from __future__ import annotations

from typing import List

from langchain_core.tools import tool
from pydantic import BaseModel
from pydantic.config import ConfigDict

from app.schemas.patient_context import PatientContext


class ClinicalSafetyState(BaseModel):
    """Input state for the Clinical Safety Agent."""

    patient: PatientContext
    user_message: str

    model_config = ConfigDict(extra="ignore")


class ClinicalSafetyResult(BaseModel):
    """Structured safety assessment result."""

    is_safe: bool
    warnings: List[str]
    rationale: str

    model_config = ConfigDict(extra="ignore")


@tool("check_clinical_safety", return_direct=False)
def check_clinical_safety(state: ClinicalSafetyState) -> dict:
    """Check a user query against medications and conditions for safety flags.

    This is a rule-based stub; in production, you'd look up drug-condition
    interactions from a trusted medical source or knowledge graph.
    """

    text = state.user_message.lower()
    warnings: List[str] = []

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

    if state.patient.conditions:
        conditions_str = ", ".join(state.patient.conditions)
        warnings.append(
            f"User has recorded conditions: {conditions_str}. "
            "AI responses must not contradict established care plans."
        )

    is_safe = not warnings
    rationale = (
        "No obvious red-flag patterns detected in the query."
        if is_safe
        else "One or more safety concerns were detected. A clinician should review."
    )

    result = ClinicalSafetyResult(
        is_safe=is_safe,
        warnings=warnings,
        rationale=rationale,
    )

    return result.model_dump()


