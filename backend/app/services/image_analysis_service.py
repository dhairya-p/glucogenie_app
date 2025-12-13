"""Image analysis service using OpenAI Vision API for meal recognition."""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from app.schemas.enhanced_patient_context import EnhancedPatientContext

logger = logging.getLogger(__name__)


class MealAnalysisResult(BaseModel):
    """Structured result from meal image analysis."""

    meal_name: str = Field(..., description="Name of the meal (e.g., 'Hainanese Chicken Rice')")
    description: str = Field(..., description="Detailed description of ingredients and portion")
    estimated_carbs_g: Optional[float] = Field(None, description="Estimated carbohydrates in grams")
    estimated_calories_kcal: Optional[float] = Field(None, description="Estimated calories in kcal")
    estimated_protein_g: Optional[float] = Field(None, description="Estimated protein in grams")
    estimated_fat_g: Optional[float] = Field(None, description="Estimated fat in grams")
    cuisine_type: Optional[str] = Field(None, description="Type of cuisine (e.g., 'Singaporean', 'Chinese')")
    dietary_notes: str = Field(..., description="Dietary advice for diabetes management")
    portion_size: Optional[str] = Field(None, description="Estimated portion size")
    confidence_score: Optional[str] = Field("medium", description="Confidence in analysis: low, medium, high")


class ImageAnalysisError(Exception):
    """Custom exception for image analysis errors."""
    pass


def _build_analysis_prompt(enhanced_context: Optional[EnhancedPatientContext] = None) -> str:
    """Build the system prompt for meal image analysis.

    Args:
        enhanced_context: Patient context with health data

    Returns:
        System prompt for Vision API
    """
    base_prompt = """You are an expert dietitian specializing in Singaporean cuisine and diabetes management.

Analyze this meal image and provide detailed nutritional information.

**Your task:**
1. Identify the meal name (especially Singaporean dishes like Chicken Rice, Laksa, Roti Prata, Nasi Lemak, etc.)
2. Describe the visible ingredients and cooking method
3. Estimate portion size (small/medium/large or specific measurements)
4. Provide approximate nutritional values:
   - Carbohydrates (grams)
   - Calories (kcal)
   - Protein (grams)
   - Fat (grams)
5. Identify cuisine type (Singaporean, Chinese, Indian, Malay, Western, etc.)
6. Provide diabetes-specific dietary advice

**Important guidelines:**
- Be specific about Singaporean dishes - recognize local favorites
- Focus on carbohydrate content as it's crucial for diabetes management
- Consider glycemic index and glycemic load
- Provide practical, actionable dietary advice
- If uncertain, indicate your confidence level
"""

    # Add patient context if available
    if enhanced_context and enhanced_context.patient:
        patient = enhanced_context.patient
        context_parts = []

        context_parts.append("\n**Patient Information:**")

        if patient.age:
            context_parts.append(f"- Age: {patient.age}")
        if patient.sex:
            context_parts.append(f"- Sex: {patient.sex}")
        if patient.ethnicity:
            context_parts.append(f"- Ethnicity: {patient.ethnicity}")
        if patient.conditions:
            context_parts.append(f"- Medical Conditions: {', '.join(patient.conditions)}")

        # Add glucose context if available
        if enhanced_context.avg_glucose_7d:
            context_parts.append(f"- Average Glucose (7d): {enhanced_context.avg_glucose_7d:.1f} mmol/L")

        if enhanced_context.latest_glucose:
            context_parts.append(f"- Latest Glucose: {enhanced_context.latest_glucose:.1f} mmol/L")

        base_prompt += "\n".join(context_parts)

    base_prompt += """

**Output Format (JSON):**
{
    "meal_name": "Name of the dish",
    "description": "Detailed description of ingredients and preparation",
    "estimated_carbs_g": 60.0,
    "estimated_calories_kcal": 600.0,
    "estimated_protein_g": 25.0,
    "estimated_fat_g": 15.0,
    "cuisine_type": "Singaporean",
    "dietary_notes": "Practical advice for blood sugar management",
    "portion_size": "1 standard plate (300g rice, 150g protein)",
    "confidence_score": "high"
}
"""

    return base_prompt


def analyze_meal_image(
    image_url: str,
    enhanced_context: Optional[EnhancedPatientContext] = None,
    model: str = "gpt-4o-mini",
) -> MealAnalysisResult:
    """Analyze a meal image using OpenAI Vision API.

    Args:
        image_url: Public URL of the meal image
        enhanced_context: Patient context for personalized analysis
        model: OpenAI model to use (default: gpt-4o-mini)

    Returns:
        Structured meal analysis result

    Raises:
        ImageAnalysisError: If analysis fails
    """
    try:
        # Get OpenAI API key
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ImageAnalysisError("OPENAI_API_KEY not found in environment variables")

        # Build prompt
        system_prompt = _build_analysis_prompt(enhanced_context)

        # Initialize Vision-capable LLM
        llm = ChatOpenAI(
            model=model,
            temperature=0.3,  # Low temperature for consistent output
            max_tokens=800,
            api_key=openai_api_key,
        )

        # Create message with image
        message = HumanMessage(
            content=[
                {"type": "text", "text": system_prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": image_url, "detail": "auto"},
                },
            ]
        )

        logger.info(f"Analyzing meal image with {model}: {image_url}")

        # Call Vision API
        response = llm.invoke([message])

        # Parse response
        response_text = response.content.strip()
        logger.info(f"Vision API response: {response_text[:200]}...")

        # Try to parse as JSON
        try:
            # Extract JSON from response (in case there's extra text)
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                result_dict = json.loads(json_str)
                result = MealAnalysisResult(**result_dict)
            else:
                raise ValueError("No JSON found in response")

        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(f"Failed to parse JSON response: {exc}")
            # Fallback: create a basic result from the text response
            result = MealAnalysisResult(
                meal_name="Meal",
                description=response_text[:500],  # Use response as description
                estimated_carbs_g=None,
                estimated_calories_kcal=None,
                cuisine_type=None,
                dietary_notes="Please consult with your dietitian for accurate nutritional information.",
                confidence_score="low",
            )

        logger.info(f"Meal analysis complete: {result.meal_name}")
        return result

    except Exception as exc:
        logger.error(f"Error analyzing meal image: {exc}", exc_info=True)
        raise ImageAnalysisError(f"Failed to analyze meal image: {str(exc)}") from exc


def analyze_meal_image_fallback(
    image_url: str,
    enhanced_context: Optional[EnhancedPatientContext] = None,
) -> MealAnalysisResult:
    """Fallback meal analysis when Vision API fails.

    Returns a generic result encouraging manual entry.

    Args:
        image_url: Public URL of the meal image (not used in fallback)
        enhanced_context: Patient context (not used in fallback)

    Returns:
        Generic meal analysis result
    """
    return MealAnalysisResult(
        meal_name="Meal",
        description="Image uploaded successfully. Please add meal details manually for accurate tracking.",
        estimated_carbs_g=None,
        estimated_calories_kcal=None,
        cuisine_type=None,
        dietary_notes="For best results, manually enter carbohydrate content and portion size.",
        portion_size="Unknown",
        confidence_score="low",
    )
