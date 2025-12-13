from __future__ import annotations

from typing import List, Optional

from langchain_core.tools import tool
from pydantic import BaseModel
from pydantic.config import ConfigDict

from app.schemas.patient_context import PatientContext
from app.schemas.enhanced_patient_context import EnhancedPatientContext


class FoodItem(BaseModel):
    name: str
    serving_size: str
    carbs_g: float
    calories_kcal: Optional[float] = None
    cuisine: Optional[str] = None


class CulturalDietitianState(BaseModel):
    """Input state for the Cultural Dietitian Agent.

    `image_url` or `image_path` should point to a food image (e.g. Supabase Storage URL).
    The actual Vision API integration is expected to be implemented later.
    """

    patient: PatientContext
    image_url: Optional[str] = None
    image_path: Optional[str] = None
    enhanced_context: Optional[EnhancedPatientContext] = None  # Full context with recent logs

    model_config = ConfigDict(extra="ignore")


class CulturalDietitianResult(BaseModel):
    """Structured nutritional mapping for Singaporean food."""

    detected_items: List[FoodItem]
    summary: str
    cultural_notes: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


@tool("analyze_food_image", return_direct=False)
def analyze_food_image(state: CulturalDietitianState) -> dict:
    """Analyze a food image and map it to Singaporean nutritional data.

    Uses OpenAI Vision API (GPT-4o-mini) to detect dishes and provide nutritional analysis.
    Specializes in Singaporean cuisine recognition.
    """
    from app.services.image_analysis_service import (
        analyze_meal_image,
        analyze_meal_image_fallback,
        ImageAnalysisError,
    )
    import logging

    logger = logging.getLogger(__name__)

    # Get image URL from state
    image_url = state.image_url or state.image_path
    if not image_url:
        logger.warning("No image URL provided to cultural dietitian agent")
        # Return fallback result
        return CulturalDietitianResult(
            detected_items=[],
            summary="No image provided for analysis.",
            cultural_notes="Please upload an image of your meal for nutritional analysis.",
        ).model_dump()

    try:
        # Use the image analysis service
        logger.info(f"Analyzing food image: {image_url}")
        analysis = analyze_meal_image(
            image_url=image_url,
            enhanced_context=state.enhanced_context,
            model="gpt-4o-mini",
        )

        # Convert analysis result to CulturalDietitianResult format
        detected = [
            FoodItem(
                name=analysis.meal_name,
                serving_size=analysis.portion_size or "Unknown",
                carbs_g=analysis.estimated_carbs_g or 0.0,
                calories_kcal=analysis.estimated_calories_kcal,
                cuisine=analysis.cuisine_type,
            )
        ]

        result = CulturalDietitianResult(
            detected_items=detected,
            summary=analysis.description,
            cultural_notes=analysis.dietary_notes,
        )

        logger.info(f"Food analysis complete: {analysis.meal_name}")
        return result.model_dump()

    except ImageAnalysisError as exc:
        logger.error(f"Image analysis failed: {exc}")
        # Return fallback result
        fallback = analyze_meal_image_fallback(image_url, state.enhanced_context)
        return CulturalDietitianResult(
            detected_items=[],
            summary=fallback.description,
            cultural_notes=fallback.dietary_notes,
        ).model_dump()
    except Exception as exc:
        logger.error(f"Unexpected error in food analysis: {exc}", exc_info=True)
        # Return generic fallback
        return CulturalDietitianResult(
            detected_items=[],
            summary="Image uploaded but analysis failed. Please add meal details manually.",
            cultural_notes="For best results, manually enter nutritional information.",
        ).model_dump()


