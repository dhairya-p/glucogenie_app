from __future__ import annotations

from typing import List, Optional
import logging

from langchain_core.tools import tool
from pydantic import BaseModel
from pydantic.config import ConfigDict

from app.schemas.patient_context import PatientContext
from app.schemas.enhanced_patient_context import EnhancedPatientContext
from app.services.rag_service import get_rag_service

logger = logging.getLogger(__name__)


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

        # Query RAG for nutritional data to enhance/validate analysis
        rag = get_rag_service()
        rag_nutritional_data = None
        rag_context = ""
        rag_citations = []
        
        logger.info(f"[Cultural Dietitian Agent] RAG service available: {rag.is_available()}")
        logger.info(f"[Cultural Dietitian Agent] Meal detected: '{analysis.meal_name}'")
        
        if rag.is_available() and analysis.meal_name:
            try:
                logger.info(f"[Cultural Dietitian Agent] Querying RAG for nutritional data: '{analysis.meal_name}'")
                rag_results = rag.query_cultural_diet(analysis.meal_name, top_k=1)
                if rag_results:
                    rag_nutritional_data = rag_results[0]
                    logger.info(f"[Cultural Dietitian Agent] RAG returned nutritional data for: {analysis.meal_name}")
                    metadata = rag_nutritional_data.get('metadata', {})
                    logger.debug(f"[Cultural Dietitian Agent] RAG data - Carbs: {metadata.get('carbs_g', 'N/A')}g, Calories: {metadata.get('calories_kcal', 'N/A')}kcal, Source: {metadata.get('source', 'Unknown')}")
                    
                    # Get formatted context for system prompt
                    rag_context = rag.get_context_for_llm(
                        analysis.meal_name,
                        namespace="cultural-diet",
                        top_k=1,
                        include_citations=True
                    )
                    source = metadata.get('source', 'Unknown')
                    if source != 'Unknown':
                        rag_citations.append(source)
                else:
                    logger.warning(f"[Cultural Dietitian Agent] No RAG data found for: {analysis.meal_name} - using Vision API estimates only")
            except Exception as e:
                logger.error(f"[Cultural Dietitian Agent] RAG query failed: {e}", exc_info=True)
        elif not rag.is_available():
            logger.warning("[Cultural Dietitian Agent] RAG service not available - using Vision API estimates only")
        elif not analysis.meal_name:
            logger.debug("[Cultural Dietitian Agent] No meal name detected - skipping RAG query")
        
        # Use RAG data if available, otherwise use analysis estimates
        carbs_g = analysis.estimated_carbs_g or 0.0
        calories_kcal = analysis.estimated_calories_kcal
        serving_size = analysis.portion_size or "Unknown"
        
        if rag_nutritional_data:
            metadata = rag_nutritional_data.get('metadata', {})
            # Prefer RAG data as it's from authoritative sources (HPB)
            if metadata.get('carbs_g'):
                carbs_g = float(metadata['carbs_g'])
            if metadata.get('calories_kcal'):
                calories_kcal = float(metadata['calories_kcal'])
            
            # Enhance summary with RAG nutritional information
            if rag_nutritional_data.get('content'):
                rag_content = rag_nutritional_data['content']
                # Extract key nutritional info from RAG content
                if "Glycemic Index" in rag_content:
                    analysis.description += f" {rag_content}"

        # Convert analysis result to CulturalDietitianResult format
        detected = [
            FoodItem(
                name=analysis.meal_name,
                serving_size=serving_size,
                carbs_g=carbs_g,
                calories_kcal=calories_kcal,
                cuisine=analysis.cuisine_type,
            )
        ]

        # Enhance cultural notes with RAG data if available
        cultural_notes = analysis.dietary_notes
        if rag_nutritional_data:
            source = rag_nutritional_data.get('metadata', {}).get('source', '')
            if source:
                cultural_notes = f"{cultural_notes} (Nutritional data from {source})"

        result = CulturalDietitianResult(
            detected_items=detected,
            summary=analysis.description,
            cultural_notes=cultural_notes,
        )

        logger.info(f"Food analysis complete: {analysis.meal_name}")
        result_dict = result.model_dump()
        # Include RAG context for system prompt
        result_dict['rag_context'] = rag_context
        result_dict['rag_citations'] = list(set(rag_citations))
        return result_dict

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


