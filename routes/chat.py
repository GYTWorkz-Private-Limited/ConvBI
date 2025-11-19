"""
Chat streaming endpoint
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import uuid

from .models import ConversationRequest
from convBI.conversationalBI import TextToSQLWorkflow

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/stream/chat")
async def stream_chat_endpoint(request: ConversationRequest):
    """Streaming chat endpoint for conversational BI using Server-Sent Events (SSE)."""
    try:
        # Use provided thread_id or generate a new one for the user
        # If thread_id is provided, it maintains conversation history
        # If not provided, create a new conversation thread
        thread_id = request.thread_id or f"{request.user_id}_{uuid.uuid4().hex[:8]}"
        
        # Initialize workflow
        workflow = TextToSQLWorkflow()

        async def event_stream() -> AsyncGenerator[str, None]:
            # Dynamic table discovery using Qdrant
            for chunk in workflow.run_stream_workflow(
                question=request.question,
                thread_id=thread_id,
                collection_name=request.collection_name or "semantics"
            ):
                yield chunk

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Thread-ID": thread_id,
                "X-User-ID": request.user_id,
            },
        )
    except Exception as e:
        # Log the full error for debugging
        import traceback
        print(f"Error in stream chat endpoint: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")

        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}",
        )

