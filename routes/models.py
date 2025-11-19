"""
Request models for API endpoints
"""

from pydantic import BaseModel
from typing import Optional


class ConversationRequest(BaseModel):
    question: str
    user_id: Optional[str] = "default_user"
    collection_name: Optional[str] = "semantics"
    thread_id: Optional[str] = None  # Allow client to pass thread_id for conversation continuity

