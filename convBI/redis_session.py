"""
Redis Session Service for Conversation Management
Handles conversation history storage and retrieval using Redis
"""

import redis
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage


class RedisSessionService:
    """Simple Redis service for conversation session management"""

    def __init__(self):
        """Initialize Redis connection"""
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            password=os.getenv('REDIS_PASSWORD', ''),
            db=int(os.getenv('REDIS_DB', 0)),
            decode_responses=True
        )

    def add_message(self, thread_id: str, role: str, content: str, sql_query: str = None):
        """Add message to conversation history"""
        key = f"conversation:{thread_id}"
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        if sql_query:
            message["sql_query"] = sql_query

        # Add to Redis list
        self.redis_client.lpush(key, json.dumps(message))
        # Set expiry to 24 hours (86400 seconds)
        self.redis_client.expire(key, 86400)

    def get_conversation_history(self, thread_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get conversation history for thread (limited to recent messages)"""
        key = f"conversation:{thread_id}"
        try:
            # Get only the most recent messages (limit)
            messages = self.redis_client.lrange(key, 0, limit - 1)
            return [json.loads(msg) for msg in reversed(messages)]
        except Exception as e:
            return []

    def clear_conversation(self, thread_id: str):
        """Clear conversation history"""
        key = f"conversation:{thread_id}"
        self.redis_client.delete(key)

    def get_conversation_count(self, thread_id: str) -> int:
        """Get number of messages in conversation"""
        key = f"conversation:{thread_id}"
        return self.redis_client.llen(key)

    def get_recent_messages_count(self, thread_id: str, limit: int = 10) -> int:
        """Get count of recent messages being sent to workflow"""
        key = f"conversation:{thread_id}"
        try:
            messages = self.redis_client.lrange(key, 0, limit - 1)
            return len(messages)
        except Exception as e:
            return 0


def convert_redis_to_langchain_messages(redis_history: List[Dict[str, Any]]) -> List[BaseMessage]:
    """
    Convert Redis message format to LangChain message format
    
    Args:
        redis_history: List of message dictionaries from Redis
        
    Returns:
        List of LangChain BaseMessage objects
    """
    langchain_messages = []
    for msg in redis_history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        
        if role == "user":
            langchain_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            langchain_messages.append(AIMessage(content=content))
    
    return langchain_messages


def convert_langchain_to_redis_format(messages: List[BaseMessage]) -> List[Dict[str, Any]]:
    """
    Convert LangChain messages to Redis message format
    
    Args:
        messages: List of LangChain BaseMessage objects
        
    Returns:
        List of message dictionaries for Redis
    """
    redis_messages = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            redis_messages.append({
                "role": "user",
                "content": msg.content,
                "timestamp": datetime.now().isoformat()
            })
        elif isinstance(msg, AIMessage):
            redis_messages.append({
                "role": "assistant",
                "content": msg.content,
                "timestamp": datetime.now().isoformat()
            })
    
    return redis_messages

