"""Chat streaming endpoints."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.core.chat_graph import _route_and_process
from app.core.system_prompt_builder import build_system_prompt
from app.dependencies import extract_user_id, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


class ChatMessage(BaseModel):
    """Single chat message from the user or assistant."""

    role: str  # "user", "assistant", or "system"
    content: str


class ChatRequest(BaseModel):
    """Request body for the chat_stream endpoint."""

    messages: list[ChatMessage]


async def _langchain_event_stream(
    chat_request: ChatRequest,
    user: Any,
) -> AsyncIterator[str]:
    """Bridge LangChain routing into a Server-Sent Events (SSE) stream.

    This implementation:
    1. Extracts user_id from authenticated user
    2. Routes the message to appropriate agent (fetches context ONCE)
    3. Builds system prompt with patient context
    4. Streams LLM response tokens
    """
    import os

    # Get OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise RuntimeError("OPENAI_API_KEY not found in environment variables.")

    # Extract user_id
    user_id = extract_user_id(user)
    logger.info("=== User ID successfully extracted: %s ===", user_id)

    # Convert incoming messages to dict format
    messages = [m.model_dump() for m in chat_request.messages]

    # Convert to LangChain format
    lc_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            lc_messages.append(SystemMessage(content=content))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=content))
        else:
            lc_messages.append(HumanMessage(content=content))

    # Get agent output (runs synchronously)
    # This fetches enhanced context ONCE and shares it
    logger.info("Starting agent routing for user_id: %s", user_id)
    patient_context_str = ""
    enhanced_context = None

    try:
        # Use a longer lookback (e.g. 30 days) for chatbot context summary
        agent_output = _route_and_process({"messages": messages, "user_id": user_id, "days": 30})
        agent_text = agent_output.get("output", "")
        enhanced_context = agent_output.get("enhanced_context")
        rag_context = agent_output.get("rag_context", "")  # Extract RAG context for system prompt
        target_agent = agent_output.get("target_agent", "unmatched")
        rag_sources = agent_output.get("rag_sources", [])
        logger.info("Agent output received: %s", agent_text[:200] if agent_text else "None")
        logger.info("RAG context extracted: %s characters", len(rag_context) if rag_context else 0)
        logger.info("Target agent: %s", target_agent)

        yield "data: " + json.dumps(
            {"type": "status", "value": {"stage": "routing", "agent": target_agent}}
        ) + "\n\n"
        if rag_sources:
            yield "data: " + json.dumps(
                {
                    "type": "status",
                    "value": {
                        "stage": "rag",
                        "sources": rag_sources[:6],
                        "rag_chars": len(rag_context) if rag_context else 0,
                    },
                }
            ) + "\n\n"

        # Use enhanced context for system prompt if available (avoids redundant Supabase call)
        if enhanced_context:
            # Prefer the longer-horizon summary if it was computed
            if getattr(enhanced_context, "historical_summary", None):
                patient_context_str = enhanced_context.historical_summary or ""
            else:
                patient_context_str = enhanced_context.get_summary_string()
        else:
            # Fallback to basic patient context (only if enhanced_context not available)
            from app.core.chat_graph import _extract_patient_context

            try:
                patient = _extract_patient_context(user_id)
                context_parts = []
                if patient.full_name and patient.full_name != "there":
                    context_parts.append(f"Name: {patient.full_name}")
                if patient.age:
                    context_parts.append(f"Age: {patient.age}")
                if patient.sex:
                    context_parts.append(f"Sex: {patient.sex}")
                if patient.ethnicity and patient.ethnicity != "Unknown":
                    context_parts.append(f"Ethnicity: {patient.ethnicity}")
                if patient.height:
                    context_parts.append(f"Height: {patient.height} cm")
                if patient.activity_level:
                    context_parts.append(f"Activity Level: {patient.activity_level}")
                if patient.location:
                    context_parts.append(f"Location: {patient.location}")
                if patient.conditions:
                    context_parts.append(f"Medical Conditions: {', '.join(patient.conditions)}")
                if patient.medications:
                    context_parts.append(f"Medications: {', '.join(patient.medications)}")

                if context_parts:
                    patient_context_str = "\n".join(context_parts)
                    logger.info("Patient context for system prompt: %s", patient_context_str)
            except Exception as exc:
                logger.error("Error fetching patient context for system prompt: %s", exc, exc_info=True)

        # Extract user message for system prompt builder
        user_message = ""
        if messages:
            last_msg = messages[-1]
            user_message = last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg)

        # Build system prompt using shared utility (with RAG context from agent)
        system_prompt = build_system_prompt(
            patient_context_str=patient_context_str or "",
            enhanced_context=enhanced_context,
            user_message=user_message,
            agent_text=agent_text,
            rag_context=rag_context,  # Pass RAG context to system prompt
        )
        
        # Log RAG context presence for debugging
        if rag_context:
            logger.info("RAG context included in system prompt: %d characters", len(rag_context))
            # Extract source names for verification
            sources = re.findall(r'Source:\s*([^\n|]+)', rag_context)
            unique_sources = list(set([s.strip() for s in sources if s.strip()]))
            logger.info("Source names in RAG context: %s", unique_sources[:5])  # Log first 5
        else:
            logger.info("No RAG context to include in system prompt")
        
        lc_messages.insert(0, SystemMessage(content=system_prompt))
    except Exception as exc:
        logger.error("Error in agent routing: %s", exc, exc_info=True)
        # Fallback system prompt with patient context
        user_message = ""
        if messages:
            last_msg = messages[-1]
            user_message = last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg)

        fallback_prompt = build_system_prompt(
            patient_context_str=patient_context_str or "",
            enhanced_context=None,
            user_message=user_message,
            agent_text=None,
            rag_context="",  # No RAG context in fallback
        )
        lc_messages.insert(0, SystemMessage(content=fallback_prompt))

    # Initialize LLM for streaming
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        streaming=True,
        api_key=openai_api_key,
    )

    # Stream directly from LLM
    async for chunk in llm.astream(lc_messages):
        # chunk is an AIMessage chunk with content
        if hasattr(chunk, "content"):
            content = chunk.content
            if isinstance(content, str) and content:
                yield "data: " + json.dumps({"type": "tokens", "value": content}) + "\n\n"
        elif isinstance(chunk, str):
            yield "data: " + json.dumps({"type": "tokens", "value": chunk}) + "\n\n"

    # Signal completion to the client
    yield "data: " + json.dumps({"type": "done"}) + "\n\n"


@router.post(
    "/chat_stream",
    summary="Stream AI chat responses",
    description=(
        "Streams AI assistant tokens and tool status events using Server-Sent Events (SSE). "
        "Consumes a LangChain routing system under the hood."
    ),
)
async def chat_stream_endpoint(
    chat_request: ChatRequest,
    user: Any = Depends(get_current_user),
) -> StreamingResponse:
    """FastAPI endpoint that returns a StreamingResponse for chat events."""

    async def event_generator() -> AsyncIterator[str]:
        try:
            async for chunk in _langchain_event_stream(chat_request, user):
                yield chunk
        except Exception as exc:
            logger.error("Error in chat stream: %s", exc, exc_info=True)
            yield "data: " + json.dumps({"type": "error", "value": str(exc)}) + "\n\n"
            yield "data: " + json.dumps({"type": "done"}) + "\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
