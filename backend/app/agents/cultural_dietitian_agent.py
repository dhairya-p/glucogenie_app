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

    This is a stub implementation that returns a plausible structure.
    In production, this would:
    - Call a Vision API to detect dishes.
    - Map them to a nutrition database tuned for Singaporean cuisine.
    """

    # Placeholder logic: pretend we detected a plate of chicken rice.
    detected = [
      FoodItem(
          name="Hainanese chicken rice",
          serving_size="1 plate",
          carbs_g=60.0,
          calories_kcal=600.0,
          cuisine="Singaporean",
      )
    ]

    result = CulturalDietitianResult(
        detected_items=detected,
        summary=(
            "Based on the image, this looks like a plate of Hainanese chicken rice. "
            "It is relatively high in carbohydrates, so consider pairing with more "
            "non-starchy vegetables if you are watching your glucose levels."
        ),
        cultural_notes=(
            "Hainanese chicken rice is a common dish in Singapore. "
            "Portion control and balancing with greens can help with glycemic control."
        ),
    )

    return result.model_dump()


