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
    user_message: Optional[str] = None  # Optional free-text query for meal recommendations

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


@tool("recommend_cultural_meals", return_direct=False)
def recommend_cultural_meals(state: CulturalDietitianState) -> dict:
    """Recommend culturally appropriate, Singapore-specific meals for the user.

    Uses the Cultural Diet RAG namespace to retrieve diabetes-friendly dishes
    tailored by ethnicity, location, and patient profile.
    """
    logger.info("[Cultural Dietitian Agent] recommend_cultural_meals invoked")
    rag = get_rag_service()
    rag_context = ""
    rag_citations: list[str] = []

    if not rag.is_available():
        logger.warning("[Cultural Dietitian Agent] RAG service not available - returning generic advice")
        summary = (
            "I don't have access to detailed nutritional data right now, but in general for diabetes-friendly "
            "Singaporean meals, focus on:\n"
            "- Smaller portions of refined carbohydrates (e.g., white rice, noodles)\n"
            "- More vegetables and lean protein (fish, tofu, skinless chicken)\n"
            "- Less sugary drinks and desserts.\n\n"
            "Ask again later once the medical knowledge base is available for more specific dish recommendations."
        )
        return {
            "summary": summary,
            "recommendations": [],
            "rag_context": "",
            "rag_citations": [],
        }

    # Build patient-aware query
    patient = state.patient
    base_query_parts = [
        "Singapore diabetes-friendly meal recommendations",
    ]
    if state.user_message:
        base_query_parts.append(state.user_message)
    if patient.ethnicity:
        base_query_parts.append(f"ethnicity {patient.ethnicity}")
    if patient.location:
        base_query_parts.append(f"location {patient.location}")
    if patient.conditions:
        base_query_parts.append(f"conditions {', '.join(patient.conditions)}")

    query = " ".join(base_query_parts)
    logger.info("[Cultural Dietitian Agent] Meal recommendation query: %s", query[:150])

    try:
        # STRICT NAMESPACE ISOLATION: Only query cultural-diet namespace
        from app.services.rag_service import NAMESPACE_CULTURAL_DIET

        results = rag.search(query, namespace=NAMESPACE_CULTURAL_DIET, top_k=5)
        logger.info(
            "[Cultural Dietitian Agent] RAG meal recommendation returned %d results from '%s' namespace",
            len(results),
            NAMESPACE_CULTURAL_DIET,
        )

        if not results:
            summary = (
                "I couldn't find specific diabetes-friendly Singaporean dishes in the knowledge base for your query. "
                "A safe starting point is to choose meals that are:\n"
                "- Lower in white rice and noodle portions\n"
                "- Higher in vegetables and lean protein\n"
                "- Less fried and less sweet.\n\n"
                "Once more cultural diet data is ingested, I can give you dish-level suggestions."
            )
            return {
                "summary": summary,
                "recommendations": [],
                "rag_context": "",
                "rag_citations": [],
            }

        # Build a simple recommendation list from metadata
        recommendations = []
        for idx, r in enumerate(results[:5], start=1):
            metadata = r.get("metadata", {}) or {}
            dish_name = metadata.get("dish_name") or metadata.get("title") or f"Dish {idx}"
            carbs = metadata.get("carbs_g")
            calories = metadata.get("calories_kcal")
            cuisine = metadata.get("cuisine") or metadata.get("cuisine_type")
            source = metadata.get("source", "Unknown")

            recommendations.append(
                {
                    "dish_name": dish_name,
                    "carbs_g": carbs,
                    "calories_kcal": calories,
                    "cuisine": cuisine,
                    "source": source,
                }
            )

            if source and source != "Unknown":
                rag_citations.append(source)

        # Get formatted RAG context for the LLM system prompt (mandatory citations)
        rag_context = rag.get_context_for_llm(
            query,
            namespace="cultural-diet",
            top_k=3,
            include_citations=True,
        )
        logger.info(
            "[Cultural Dietitian Agent] RAG context for meal recommendations: %d characters",
            len(rag_context) if rag_context else 0,
        )

        # High-level summary text for agent output (LLM will refine using rag_context)
        dish_names = [r["dish_name"] for r in recommendations if r.get("dish_name")]
        summary_lines = [
            "Here are some Singapore-specific, diabetes-friendly meal ideas based on your profile:",
        ]
        if dish_names:
            summary_lines.append("- Suggested dishes: " + ", ".join(dish_names[:5]))
        summary_lines.append(
            "These suggestions prioritize lower refined carbohydrates and higher vegetables/lean proteins, "
            "while respecting local Singaporean cuisine and personalising suggestions to user's demographics like age, ethnicity, location, etc. where possible."
        )

        summary = "\n".join(summary_lines)

        return {
            "summary": summary,
            "recommendations": recommendations,
            "rag_context": rag_context,
            "rag_citations": list(set(rag_citations)),
        }

    except Exception as exc:
        logger.error("[Cultural Dietitian Agent] Error in recommend_cultural_meals: %s", exc, exc_info=True)
        summary = (
            "I encountered an error while looking up cultural diet recommendations. "
            "For now, focus on smaller portions of rice/noodles, more vegetables, and lean protein. "
            "Avoid sugary drinks and desserts where possible."
        )
        return {
            "summary": summary,
            "recommendations": [],
            "rag_context": "",
            "rag_citations": [],
        }


