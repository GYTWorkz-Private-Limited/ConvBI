from typing import Annotated, Dict, Any, Optional, List
from typing_extensions import TypedDict
from pydantic import BaseModel
from langgraph.graph.message import add_messages


class WorkflowState(TypedDict, total=False):
    history: Annotated[list, add_messages]
    question: str
    intent: str
    selected_tables: List[str]
    semantic_info: Dict[str, Any]
    sql_query: str
    query_result: str
    error_message: str
    needs_clarification: bool
    visualization_data: Dict[str, Any]
    final_answer: str
    follow_up_questions: Dict[str, Any]

    collection_name: str
    thread_id: str  # Added for Redis session management

    retry_count: int
    has_sql_error: bool
    error_history: List[str]


class StreamResponse(BaseModel):
    type: str
    data: dict
    timestamp: str
    thread_id: Optional[str] = None
    node: Optional[str] = None

