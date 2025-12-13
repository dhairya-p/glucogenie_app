"""Insights endpoints for personalized recommendations."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.agents.lifestyle_analyst_agent import LifestyleState, analyze_lifestyle
from app.core.chat_graph import _extract_enhanced_patient_context
from app.dependencies import extract_user_id, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("", response_model=dict)
async def get_insights(
    user: Any = Depends(get_current_user),
) -> dict:
    """Get personalized insights for the user.

    Returns top 2-3 insights calculated by the lifestyle analyst agent.
    Returns empty list if insufficient data.

    This endpoint fetches enhanced patient context ONCE and reuses it,
    avoiding redundant Supabase queries.
    """
    try:
        # Extract user_id
        user_id = extract_user_id(user)

        # Fetch enhanced context (this includes pattern analysis and all patient data)
        # This is the ONLY Supabase query needed - it fetches everything at once
        enhanced_context = _extract_enhanced_patient_context(user_id, days=7)

        # Extract patient context from enhanced context (no additional query)
        patient_context = enhanced_context.patient

        # Run lifestyle analysis (uses the pre-fetched enhanced_context)
        state = LifestyleState(
            user_id=user_id,
            days=7,
            patient=patient_context,
            enhanced_context=enhanced_context,
        )

        # analyze_lifestyle is a StructuredTool, must use .invoke()
        result = analyze_lifestyle.invoke({"state": state})

        # Return top insights (2-3)
        top_insights = result.get("top_insights", [])

        # Convert to list of dicts if needed
        if top_insights and len(top_insights) > 0:
            # Ensure they're dicts (not Pydantic models)
            insights_list = []
            for insight in top_insights[:3]:
                if isinstance(insight, dict):
                    insights_list.append(insight)
                else:
                    # Handle Pydantic model
                    insights_list.append({
                        "title": getattr(insight, "title", ""),
                        "detail": getattr(insight, "detail", ""),
                    })

            return {
                "insights": insights_list,
                "message": "success",
            }

        # If insufficient data, return empty
        return {"insights": [], "message": "Insufficient data for insights"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error fetching insights: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating insights",
        ) from exc
