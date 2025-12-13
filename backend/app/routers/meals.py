"""Meal logging endpoints for image upload and analysis."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from supabase import Client

from app.core.chat_graph import _extract_enhanced_patient_context
from app.dependencies import extract_user_id, get_current_user, get_supabase
from app.services.image_analysis_service import (
    ImageAnalysisError,
    MealAnalysisResult,
    analyze_meal_image,
    analyze_meal_image_fallback,
)
from app.services.supabase_storage_service import ImageUploadError, upload_meal_image

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meals", tags=["meals"])


class MealLogResponse(BaseModel):
    """Response for meal log creation."""

    success: bool
    meal_log: dict
    analysis: Optional[dict] = None
    message: Optional[str] = None


class MealLogListResponse(BaseModel):
    """Response for meal log list."""

    success: bool
    meal_logs: list[dict]
    total: int


@router.post("/analyze-image", response_model=MealLogResponse)
async def analyze_and_log_meal_image(
    file: UploadFile = File(...),
    user: Any = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
) -> MealLogResponse:
    """Upload and analyze a meal image, then create a meal log entry.

    **Process:**
    1. Upload image to Supabase Storage
    2. Analyze image with GPT-4o-mini Vision API
    3. Save meal log to database
    4. Return analysis and meal log entry

    **Args:**
        file: Uploaded image file (JPEG, PNG, HEIC, WebP)
        user: Authenticated user (from JWT)
        supabase: Supabase client

    **Returns:**
        MealLogResponse with meal log and analysis results
    """
    try:
        # Extract user_id
        user_id = extract_user_id(user)
        logger.info(f"Analyzing meal image for user: {user_id}")

        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No filename provided",
            )

        # Read file content
        file_content = await file.read()

        if len(file_content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file uploaded",
            )

        # Step 1: Upload image to Supabase Storage
        try:
            image_url = upload_meal_image(
                file_content=file_content,
                filename=file.filename,
                user_id=user_id,
                resize=True,
            )
            logger.info(f"Image uploaded successfully: {image_url}")
        except ImageUploadError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        # Step 2: Analyze image with Vision API
        analysis_result = None
        try:
            # Fetch enhanced patient context for personalized analysis
            enhanced_context = None
            try:
                enhanced_context = _extract_enhanced_patient_context(user_id, days=7)
            except Exception as ctx_exc:
                logger.warning(f"Failed to fetch patient context: {ctx_exc}")

            # Analyze meal image
            analysis_result = analyze_meal_image(
                image_url=image_url,
                enhanced_context=enhanced_context,
                model="gpt-4o-mini",
            )

            logger.info(f"Image analysis complete: {analysis_result.meal_name}")

        except ImageAnalysisError as exc:
            logger.error(f"Image analysis failed: {exc}")
            # Use fallback analysis
            analysis_result = analyze_meal_image_fallback(image_url)

        # Step 3: Save to meal_logs table
        meal_name = analysis_result.meal_name or "Meal"
        meal_description = analysis_result.description

        # Add nutritional info to description if available
        nutrition_parts = []
        if analysis_result.estimated_carbs_g:
            nutrition_parts.append(f"Carbs: ~{analysis_result.estimated_carbs_g:.0f}g")
        if analysis_result.estimated_calories_kcal:
            nutrition_parts.append(f"Calories: ~{analysis_result.estimated_calories_kcal:.0f} kcal")
        if analysis_result.estimated_protein_g:
            nutrition_parts.append(f"Protein: ~{analysis_result.estimated_protein_g:.0f}g")
        if analysis_result.estimated_fat_g:
            nutrition_parts.append(f"Fat: ~{analysis_result.estimated_fat_g:.0f}g")

        if nutrition_parts:
            meal_description += f"\n\nNutritional Estimates: {', '.join(nutrition_parts)}"

        if analysis_result.dietary_notes:
            meal_description += f"\n\nDietary Advice: {analysis_result.dietary_notes}"

        # Insert into database
        try:
            result = (
                supabase.table("meal_logs")
                .insert({
                    "user_id": user_id,
                    "meal": meal_name,
                    "description": meal_description,
                    "image_url": image_url,
                })
                .execute()
            )

            meal_log = result.data[0] if result.data else None
            if not meal_log:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create meal log entry",
                )

            logger.info(f"Meal log created: {meal_log.get('id')}")

        except Exception as db_exc:
            logger.error(f"Database insertion failed: {db_exc}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save meal log to database",
            ) from db_exc

        # Step 4: Return response
        return MealLogResponse(
            success=True,
            meal_log=meal_log,
            analysis=analysis_result.model_dump() if analysis_result else None,
            message="Meal logged successfully",
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Unexpected error in analyze_and_log_meal_image: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(exc)}",
        ) from exc


@router.get("/", response_model=MealLogListResponse)
async def get_meal_logs(
    limit: int = 50,
    offset: int = 0,
    user: Any = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
) -> MealLogListResponse:
    """Get meal logs for the authenticated user.

    **Args:**
        limit: Maximum number of logs to return (default: 50)
        offset: Number of logs to skip (default: 0)
        user: Authenticated user
        supabase: Supabase client

    **Returns:**
        List of meal logs with pagination
    """
    try:
        # Extract user_id
        user_id = extract_user_id(user)

        # Fetch meal logs
        result = (
            supabase.table("meal_logs")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        meal_logs = result.data or []

        # Get total count
        count_result = (
            supabase.table("meal_logs")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )

        total = count_result.count if hasattr(count_result, "count") else len(meal_logs)

        return MealLogListResponse(
            success=True,
            meal_logs=meal_logs,
            total=total,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error fetching meal logs: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch meal logs: {str(exc)}",
        ) from exc


@router.delete("/{meal_id}")
async def delete_meal_log(
    meal_id: str,
    user: Any = Depends(get_current_user),
    supabase: Client = Depends(get_supabase),
) -> dict:
    """Delete a meal log entry.

    **Args:**
        meal_id: ID of the meal log to delete
        user: Authenticated user
        supabase: Supabase client

    **Returns:**
        Success message
    """
    try:
        # Extract user_id
        user_id = extract_user_id(user)

        # Verify meal log belongs to user
        meal_log_result = (
            supabase.table("meal_logs")
            .select("*")
            .eq("id", meal_id)
            .eq("user_id", user_id)
            .execute()
        )

        if not meal_log_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meal log not found",
            )

        # Delete meal log
        supabase.table("meal_logs").delete().eq("id", meal_id).execute()

        # Note: We're not deleting the image from storage to preserve audit trail
        # Images can be cleaned up separately via a background job if needed

        logger.info(f"Meal log deleted: {meal_id}")

        return {
            "success": True,
            "message": "Meal log deleted successfully",
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error deleting meal log: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete meal log: {str(exc)}",
        ) from exc
