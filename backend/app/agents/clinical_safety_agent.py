from __future__ import annotations

from typing import List, Optional, Dict, Any

from langchain_core.tools import tool
from pydantic import BaseModel
from pydantic.config import ConfigDict

from app.schemas.patient_context import PatientContext
from app.schemas.enhanced_patient_context import EnhancedPatientContext
from app.services.rag_service import get_rag_service, NAMESPACE_CLINICAL_SAFETY
from app.services.neo4j_service import query_kg_relationships, format_kg_context


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
    
    # Get RAG service for evidence-based safety checks
    rag = get_rag_service()
    rag_context = ""
    rag_citations = []  # Store citations separately for system prompt
    kg_context = ""
    specific_findings: List[str] = []
    
    logger.info(f"[Clinical Safety Agent] RAG service available: {rag.is_available()}")
    
    # Build patient context for RAG query enhancement
    patient_context: Dict[str, Any] = {
        "age": state.patient.age,
        "conditions": state.patient.conditions or [],
        "medications": state.patient.medications or [],
        "sex": state.patient.sex,
        "ethnicity": state.patient.ethnicity,
    }
    logger.debug(f"[Clinical Safety Agent] Patient context: age={patient_context['age']}, conditions={patient_context['conditions']}, medications={patient_context['medications']}")
    
    # Query Neo4j KG for relationships first (GraphRAG)
    try:
        if any(keyword in text for keyword in ["metformin", "insulin", "glipizide", "jardiance", "ozempic", "lantus"]):
            logger.info("[Clinical Safety Agent] Querying Neo4j KG for drug interactions...")
            kg_results = query_kg_relationships(state.user_message, limit=20)
            kg_context = format_kg_context(kg_results)
            if kg_results:
                for item in kg_results[:6]:
                    subject = item.get("subject", "Unknown")
                    relation = str(item.get("relation", "related_to")).replace("_", " ").lower()
                    obj = item.get("object", "Unknown")
                    specific_findings.append(f"{subject} {relation} {obj}.")
            if kg_context:
                logger.info("[Clinical Safety Agent] KG context formatted: %d characters", len(kg_context))
            else:
                logger.info("[Clinical Safety Agent] No KG relationships found")
    except Exception as exc:
        logger.error("[Clinical Safety Agent] Neo4j KG query failed: %s", exc, exc_info=True)

    # Query RAG for relevant clinical safety information
    if rag.is_available():
        try:
            logger.info("[Clinical Safety Agent] Checking user message for RAG-triggering keywords...")
            # Extract key terms from user message for RAG query
            rag_query_parts = []
            
            # Medication-specific keywords
            if any(med in text for med in ["metformin", "insulin", "sulphonylurea", "glipizide", "glyburide"]):
                for med in ["metformin", "insulin", "sulphonylurea", "glipizide", "glyburide"]:
                    if med in text:
                        rag_query_parts.append(med)
                        logger.info(f"[Clinical Safety Agent] Detected medication keyword: {med}")
                        break
            
            # Clinical condition keywords
            if any(term in text for term in ["kidney", "renal", "eGFR"]):
                rag_query_parts.append("kidney disease contraindication")
                logger.info("[Clinical Safety Agent] Detected kidney-related keyword")
            if any(term in text for term in ["skip meal", "skip meals", "fasting"]):
                rag_query_parts.append("meal skipping hypoglycemia")
                logger.info("[Clinical Safety Agent] Detected meal-skipping keyword")
            if any(term in text for term in ["increase dose", "higher dose", "more medication"]):
                rag_query_parts.append("dose adjustment")
                logger.info("[Clinical Safety Agent] Detected dose adjustment keyword")

            # General safety/avoidance queries should still use patient context
            if any(term in text for term in ["avoid", "wary", "mindful", "watch out", "precaution", "risky", "dangerous"]):
                rag_query_parts.append("drug food interactions precautions contraindications")
                logger.info("[Clinical Safety Agent] Detected general safety/avoidance query")
            
            # Clinical guidelines and recommendations keywords
            guideline_keywords = [
                "guideline", "guidelines", "recommendation", "recommendations", "protocol", "protocols",
                "moh", "ministry of health", "ada", "american diabetes", "who", "world health",
                "clinical standard", "medical standard", "best practice", "evidence-based",
                "medical guideline", "treatment guideline", "diabetes guideline", "clinical protocol"
            ]
            if any(term in text for term in guideline_keywords):
                logger.info("[Clinical Safety Agent] Detected clinical guidelines keyword")
                # Extract the main topic from user message for guideline query
                rag_query_parts.append(state.user_message[:200])  # Use user message as query
            
            # Build RAG query - use specific keywords if found, otherwise use user message
            if rag_query_parts:
                rag_query = " ".join(rag_query_parts)
                logger.info(f"[Clinical Safety Agent] Querying RAG with: '{rag_query[:150]}...'")
            else:
                # Default: query RAG with user message for any clinical safety query
                rag_query = state.user_message[:300]  # Use first 300 chars of user message
                # If the user asks a generic safety question, add meds/conditions context
                if any(term in text for term in ["avoid", "wary", "mindful", "watch out", "precaution"]):
                    meds = ", ".join(state.patient.medications or [])
                    conditions = ", ".join(state.patient.conditions or [])
                    if meds or conditions:
                        rag_query = f"{rag_query} medications {meds} conditions {conditions}"
                logger.info(f"[Clinical Safety Agent] No specific keywords found, querying RAG with user message: '{rag_query[:150]}...'")
            
            rag_results = rag.query_clinical_safety(rag_query, patient_context, top_k=3)
            
            if rag_results:
                logger.info(f"[Clinical Safety Agent] RAG returned {len(rag_results)} results")
                rag_context = rag.get_context_for_llm(
                    rag_query,
                    namespace=NAMESPACE_CLINICAL_SAFETY,
                    top_k=3,
                    include_citations=True
                )
                # Extract citations for system prompt
                for result in rag_results:
                    source = result.get('metadata', {}).get('source', 'Unknown')
                    if source != 'Unknown':
                        rag_citations.append(source)
                logger.info(f"[Clinical Safety Agent] RAG context formatted: {len(rag_context)} characters")
                logger.debug(f"[Clinical Safety Agent] RAG context preview: {rag_context[:200]}...")
            else:
                logger.warning("[Clinical Safety Agent] RAG query returned no results")
        except Exception as e:
            logger.error(f"[Clinical Safety Agent] RAG query failed: {e}", exc_info=True)
    else:
        logger.warning("[Clinical Safety Agent] RAG service not available - using fallback heuristics only")

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
    
    # Build rationale (RAG context is passed separately to system prompt, not included here)
    meds_list = ", ".join(state.patient.medications or [])
    conditions_list = ", ".join(state.patient.conditions or [])
    meds_note = f"Your current medications: {meds_list}." if meds_list else "Your current medications: not available."
    conditions_note = f"Your conditions: {conditions_list}." if conditions_list else "Your conditions: not available."
    profile_note = ""
    if meds_list and conditions_list:
        profile_note = f"Given you're on {meds_list} and have {conditions_list}, "
    elif meds_list:
        profile_note = f"Given you're on {meds_list}, "
    elif conditions_list:
        profile_note = f"Given you have {conditions_list}, "

    rationale_core = (
        "no obvious red-flag patterns detected in the query based on patient context and recent data."
        if is_safe
        else f"one or more safety concerns were detected based on patient demographics, conditions, medications, and recent logs ({len(warnings)} warning(s)). A clinician should review."
    )
    rationale = f"{meds_note} {conditions_note} {profile_note}{rationale_core}"
    
    # Note: RAG context is passed separately via rag_context field to system prompt
    # It should NOT be included in the rationale to avoid duplication

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

    # Combine KG + Pinecone RAG contexts for system prompt (KG first for deterministic relationships)
    result_dict = result.model_dump()
    combined_context = "\n\n".join([c for c in [kg_context, rag_context] if c])
    result_dict['rag_context'] = combined_context  # Full RAG context for system prompt
    result_dict['specific_findings'] = specific_findings
    result_dict['rag_citations'] = list(set(rag_citations))  # Unique citations
    
    return result_dict

