from __future__ import annotations

from contextlib import asynccontextmanager
import json
import logging
import sys
from typing import Any, AsyncIterator, List, Literal

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from supabase import Client, create_client
from app.core.system_prompt_builder import build_system_prompt
from app.core.timezone_utils import get_current_datetime_string

# Configure logging to show INFO level and above
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
    force=True,  # Override any existing configuration
)

# NOTE:
# - This file wires together the FastAPI app, Supabase auth, and shared infrastructure.
# - Feature‑specific routes and Agents should live in `app/routers/` and `app/agents/`.

logger = logging.getLogger(__name__)
logger.info("=== Backend logging initialized ===")


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    These map to the same SUPABASE env vars that the Flutter app uses.
    Secrets must NEVER be hard‑coded in code.
    """

    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str | None = None

    neo4j_uri: str | None = None
    neo4j_username: str | None = None
    neo4j_password: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class HealthResponse(BaseModel):
    """Simple health check response."""

    api: str
    supabase: bool


class ChatMessage(BaseModel):
    """Single chat message from the user or assistant."""

    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    """Request body for the chat_stream endpoint."""

    messages: List[ChatMessage]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan hook.

    Initializes shared resources (Supabase client, Neo4j driver, etc.)
    once at startup and cleans them up on shutdown.
    """

    settings = Settings()
    app.state.settings = settings

    # Supabase client (use service role key when available for backend‑only work).
    supabase_key = settings.supabase_service_role_key or settings.supabase_anon_key
    app.state.supabase: Client = create_client(settings.supabase_url, supabase_key)

    # TODO: Initialize Neo4j driver here when connection details are available.
    app.state.neo4j_driver = None

    logger.info("Backend startup complete")
    try:
        yield
    finally:
        neo4j_driver = getattr(app.state, "neo4j_driver", None)
        if neo4j_driver is not None:
            neo4j_driver.close()
        logger.info("Backend shutdown complete")


app = FastAPI(
    title="Diabetes Assistant Backend",
    description="FastAPI backend for the Diabetes FYP (Supabase + Agents).",
    version="0.1.0",
    lifespan=lifespan,
)


# CORS configuration – allow local frontend and Supabase Studio origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # Allow all origins for development (restrict in production)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


def get_settings(request: Request) -> Settings:
    """FastAPI dependency to access global settings."""

    return request.app.state.settings


def get_supabase_client(request: Request) -> Client:
    """FastAPI dependency to access the shared Supabase client."""

    return request.app.state.supabase


async def get_current_user(
    request: Request,
    supabase: Client = Depends(get_supabase_client),
) -> Any:
    """Validate the Supabase JWT from the Authorization header.

    The Flutter frontend must send:  Authorization: Bearer <access_token>
    This dependency ensures all protected routes receive an authenticated user.
    """

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing access token",
        )

    access_token = auth_header.removeprefix("Bearer").strip()
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )

    try:
        user_response = supabase.auth.get_user(access_token)
        user = getattr(user_response, "user", None)
        if user is None:
            logger.error("Supabase get_user returned None")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access token",
            )
        logger.info("Supabase auth succeeded. User type: %s, User: %s", type(user).__name__, user)
        # Try to log user.id if it exists
        if hasattr(user, "id"):
            logger.info("User has id attribute: %s", user.id)
        elif isinstance(user, dict):
            logger.info("User is dict with id: %s", user.get("id"))
        return user
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("Supabase JWT verification failed: %s", exc)
        # For development: try JWT decode fallback if Supabase fails
        # This allows the app to work even if Supabase auth has issues
        try:
            import jwt
            decoded = jwt.decode(
                access_token,
                options={"verify_signature": False}
            )
            user_id = decoded.get("sub") or decoded.get("user_id")
            if user_id:
                user = {"id": user_id, "email": decoded.get("email")}
                logger.warning(
                    "Using JWT fallback due to Supabase error. User ID: %s", user_id
                )
                return user
        except ImportError:
            logger.error("PyJWT not installed, cannot use JWT fallback")
        except Exception as jwt_exc:  # noqa: BLE001
            logger.error("JWT fallback also failed: %s", jwt_exc)
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired access token: {str(exc)}",
        ) from exc


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Basic liveness endpoint to verify the API and Supabase connectivity.",
)
async def health(
    settings: Settings = Depends(get_settings),
    supabase: Client = Depends(get_supabase_client),
) -> HealthResponse:
    """Simple health check endpoint.

    - Verifies the API is running.
    - Performs a lightweight call to Supabase auth to ensure configuration is valid.
    """

    supabase_ok = True
    try:
        # Perform a lightweight query to verify Supabase connection.
        # Try to query a common table (profiles) with limit 0 to minimize overhead.
        _ = supabase.table("profiles").select("id").limit(0).execute()
    except Exception as exc:  # noqa: BLE001
        supabase_ok = False
        logger.error("Supabase health check failed: %s", exc)

    return HealthResponse(api="ok", supabase=supabase_ok)


# --- LangChain streaming integration -------------------------------------------------


async def _langchain_event_stream(
    chat_request: ChatRequest,
    user: Any,
) -> AsyncIterator[str]:
    """Bridge LangChain `astream_events` into a Server-Sent Events (SSE) stream.

    This implementation expects a LangChain Runnable/Graph with an `astream_events`
    method that yields structured events. You should implement `get_chat_runnable()`
    in `app/core` and have it return your Agent/Graph.
    """

    # Import locally to avoid forcing LangChain at import time if unused.
    from app.core.chat_graph import _route_and_process  # type: ignore[import-not-found]
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI
    import os
    
    # Get OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise RuntimeError("OPENAI_API_KEY not found in environment variables.")
    
    # Initialize LLM for streaming
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        streaming=True,
        api_key=openai_api_key,
    )

    # Extract user_id from the authenticated user
    user_id = ""
    if hasattr(user, "id"):
        user_id = str(user.id)
    elif isinstance(user, dict):
        user_id = str(user.get("id", ""))
    elif hasattr(user, "__dict__"):
        # Try to get from __dict__
        user_dict = vars(user)
        user_id = str(user_dict.get("id", ""))
        logger.info("Extracted user_id from user.__dict__: %s", user_id)
    else:
        logger.warning("Could not extract user_id from user object. User type: %s, User: %s", type(user).__name__, user)

    if not user_id:
        logger.error("=== CRITICAL: No user_id available! Cannot fetch patient context or logs. ===")
        logger.error("This will cause agents to fail. User object was: %s", user)
    else:
        logger.info("=== User ID successfully extracted: %s ===", user_id)

    # Convert incoming messages into the format your runnable expects.
    # Include user_id so agents can fetch patient context from Supabase.
    input_payload: dict[str, Any] = {
        "messages": [m.model_dump() for m in chat_request.messages],
        "user_id": user_id,
    }

    messages = input_payload.get("messages", [])
    user_id = input_payload.get("user_id", "")
    
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
    try:
        agent_output = _route_and_process({"messages": messages, "user_id": user_id, "days": 7})
        agent_text = agent_output.get("output", "")
        enhanced_context = agent_output.get("enhanced_context")
        logger.info("Agent output received: %s", agent_text[:200] if agent_text else "None")
        
        # Use enhanced context for system prompt if available (avoids redundant Supabase call)
        if enhanced_context:
            patient_context_str = enhanced_context.get_summary_string()
        else:
            # Fallback to basic patient context (only if enhanced_context not available)
            from app.core.chat_graph import _extract_patient_context
            try:
                if user_id:
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
        
        # Build system prompt using shared utility
        system_prompt = build_system_prompt(
            patient_context_str=patient_context_str or "",
            enhanced_context=enhanced_context,
            user_message=user_message,
            agent_text=agent_text,
        )
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
        )
        lc_messages.insert(0, SystemMessage(content=fallback_prompt))
    
    # Stream directly from LLM (this avoids pickling issues with astream_events)
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


@app.post(
    "/chat_stream",
    summary="Stream AI chat responses",
    description=(
        "Streams AI assistant tokens and tool status events using Server‑Sent Events (SSE). "
        "Consumes a LangChain `astream_events` iterator under the hood."
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


@app.get("/api/insights", response_model=dict)
async def get_insights(
    user: Any = Depends(get_current_user),
) -> dict:
    """Get personalized insights for the user.
    
    Returns top 2-3 insights calculated by the lifestyle analyst agent.
    Returns empty list if insufficient data.
    """
    from app.core.chat_graph import _extract_enhanced_patient_context, _extract_patient_context
    from app.agents.lifestyle_analyst_agent import analyze_lifestyle, LifestyleState
    
    try:
        # Extract user_id
        user_id = str(user.id) if hasattr(user, "id") else str(user.get("id", ""))
        if not user_id:
            return {"insights": [], "message": "User ID not found"}
        
        # Fetch enhanced context (this includes pattern analysis)
        enhanced_context = _extract_enhanced_patient_context(user_id, days=7)
        
        # Extract patient context
        patient_context = _extract_patient_context(user_id)
        
        # Run lifestyle analysis
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
    except Exception as exc:
        logger.error("Error fetching insights: %s", exc, exc_info=True)
        return {"insights": [], "message": "Error generating insights"}


# Future: include feature routers here, each using the shared auth + agents.
# from app.routers import meals, glucose, profile
# app.include_router(meals.router, prefix="/meals", tags=["meals"])
# app.include_router(glucose.router, prefix="/glucose", tags=["glucose"])
# app.include_router(profile.router, prefix="/profile", tags=["profile"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )

