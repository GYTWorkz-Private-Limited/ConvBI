from dotenv import load_dotenv
load_dotenv()

import os 
from langgraph.graph import StateGraph,START,END 
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict,Any,Optional,List
from datetime import datetime
import asyncio
from convBI.prompts import (
    intent_prompt,
    greeting_prompt,
    text_to_sql_prompt,
    summarizer_prompt,
    visualization_prompt,
    help_prompt,
    follow_up_questions_prompt,
    debugger_prompt,
)

import psycopg

from convBI.agents.intent import run as run_intent
from convBI.agents.populate_qdrant_data import run as run_populate_qdrant
from convBI.agents.text_to_sql import run as run_text_to_sql
from convBI.agents.execute_sql import run as run_execute_sql
from convBI.agents.clarification import run as run_clarification
from convBI.agents.summarizer import run as run_summarizer
from convBI.agents.visualization import run as run_visualization
from convBI.agents.followups import run as run_followups
from convBI.redis_session import (
    RedisSessionService,
    convert_redis_to_langchain_messages
)
from convBI.config.models import WorkflowState, StreamResponse

try:
    from langfuse.langchain import CallbackHandler
    if os.getenv('LANGFUSE_PUBLIC_KEY') and os.getenv('LANGFUSE_SECRET_KEY'):
        langfuse_handler = CallbackHandler()
    else:
        langfuse_handler = None
except ImportError:
    langfuse_handler = None

def get_callback_config(tag: str):
    if langfuse_handler:
        return {
            "callbacks": [langfuse_handler],
            "metadata": {"langfuse_tags": [tag, "text_to_sql_workflow"]}
        }
    else:
        return {}




class TextToSQLWorkflow:
    def __init__(self):
        self.llm=AzureChatOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
            openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"]
        )
        # Initialize Redis session service for conversation history
        self.redis_session = RedisSessionService()
            
    
    def _build_workflow(self)->StateGraph[WorkflowState]:
        graph_builder=StateGraph(WorkflowState)
        graph_builder.add_node("intent_classification",self._intent_classification_agent)
        graph_builder.add_node("greeting",self._greeting_agent)
        graph_builder.add_node("help_agent", self._help_agent)
        graph_builder.add_node("populate_qdrant_data", self._populate_qdrant_data_agent)
        graph_builder.add_node("text_to_sql",self._text_to_sql_agent)
        graph_builder.add_node("execute_sql_query", self._execute_sql_query)
        graph_builder.add_node("clarification_agent", self._clarification_agent)
        
        graph_builder.add_node("summarizer", self._summarizer_agent)
        graph_builder.add_node("noanswer", self._noanswer_agent)
        graph_builder.add_node("visualization",self._visualization_agent)
        graph_builder.add_node("follow_up_questions",self._follow_up_questions_agent)


        

        graph_builder.add_edge(START,"intent_classification")
        graph_builder.add_conditional_edges(
            "intent_classification",
            self._route_by_intent,  # Use a routing function
            {
                "general": "greeting",
                "help": "help_agent",
                "system_query": "populate_qdrant_data"
                
            }
        )

        graph_builder.add_edge("populate_qdrant_data", "text_to_sql") 
        graph_builder.add_edge("text_to_sql","execute_sql_query")
        graph_builder.add_conditional_edges(
            "execute_sql_query",
            self._route_after_execute,
            {"success":"summarizer","retry":"clarification_agent","no_answer":"noanswer"}
        )
        graph_builder.add_conditional_edges(
            "clarification_agent",
            self._route_after_debugger,
            {"retry_execute":"execute_sql_query", "end":END}
        )
        graph_builder.add_edge("summarizer", "visualization")
        graph_builder.add_edge("visualization","follow_up_questions")
        graph_builder.add_edge("noanswer",END)
        graph_builder.add_edge("follow_up_questions",END)
        graph_builder.add_edge("greeting",END)  
        graph_builder.add_edge("help_agent", END)
        
        return graph_builder

    def _route_after_execute(self, state: WorkflowState) -> str:
        # Success path
        if not state.get("has_sql_error"):
            return "success"
        # If there is an error, decide whether to retry via debugger or clarify
        retry_count = state.get("retry_count", 0)
        if retry_count < 3:
            return "retry"
        return "no_answer"

    def _route_after_debugger(self, state: WorkflowState) -> str:
        # After debugger produces a new query, if under limit, go execute again; else end
        retry_count = state.get("retry_count", 0)
        if retry_count < 3:
            return "retry_execute"
        return "end"

    def _clarification_agent(self, state: WorkflowState) -> WorkflowState:
        return run_clarification(state, self.llm, debugger_prompt, get_callback_config)

    def _route_by_intent(self, state: WorkflowState) -> str:
        """Route based on the classified intent"""
        intent = state.get("intent", "").strip().lower()

        if intent == "general":
            return "general"
        elif intent == "help":
            return "help"
        elif intent == "system_query":
            return "system_query"
        else:
            # Default fallback
            return "system_query"

    def _intent_classification_agent(self,state:WorkflowState)->WorkflowState:
        return run_intent(state, self.llm, intent_prompt, get_callback_config)
    
    def _greeting_agent(self,state:WorkflowState)->WorkflowState:
        prompt=ChatPromptTemplate.from_messages(greeting_prompt)
        chain=prompt|self.llm 
        
        result=chain.invoke({
            "question":state["question"]
        }, 
        config=get_callback_config("greeting")
        )
        state["final_answer"]=result.content.strip()

        return state
    
    def _help_agent(self, state: WorkflowState) -> WorkflowState:
        """Agent to handle help/assistance questions"""
        help_message=help_prompt
        state["final_answer"]=help_message
        return state

    def _populate_qdrant_data_agent(self, state: WorkflowState) -> WorkflowState:
        return run_populate_qdrant(state)

    
    
    def _text_to_sql_agent(self,state:WorkflowState)->WorkflowState:
        result_state = run_text_to_sql(state, self.llm, text_to_sql_prompt, get_callback_config)
        # Save SQL query to Redis if we have a thread_id in the state
        thread_id = state.get("thread_id")
        if thread_id and result_state.get("sql_query"):
            self.redis_session.add_message(
                thread_id=thread_id,
                role="assistant",
                content=result_state.get("sql_query", ""),
                sql_query=result_state.get("sql_query", "")
            )
        return result_state
    
    def _execute_sql_query(self, state: WorkflowState) -> WorkflowState:
        return run_execute_sql(state, self._get_db_connection)
    def _get_db_connection(self):
        try:
            from urllib.parse import quote_plus
            q_user = os.getenv('QUERY_DB_USER')
            q_pass = os.getenv('QUERY_DB_PASSWORD', '')
            q_host = os.getenv('QUERY_DB_HOST')
            q_port = os.getenv('QUERY_DB_PORT')
            q_name = os.getenv('QUERY_DB_NAME')
            encoded_q_pass = quote_plus(q_pass or '')
            DATABASE_URL = f"postgresql://{q_user}:{encoded_q_pass}@{q_host}:{q_port}/{q_name}?sslmode=require"
            connection = psycopg.connect(DATABASE_URL)
            return connection
        except psycopg.Error:
            return None  
    
    def _summarizer_agent(self, state: WorkflowState) -> WorkflowState:
        result_state = run_summarizer(state, self.llm, summarizer_prompt, get_callback_config)
        # Save final answer to Redis if we have a thread_id
        thread_id = state.get("thread_id")
        if thread_id and result_state.get("final_answer"):
            self.redis_session.add_message(
                thread_id=thread_id,
                role="assistant",
                content=result_state.get("final_answer", "")
            )
        return result_state

    def _noanswer_agent(self, state: WorkflowState) -> WorkflowState:

        state["final_answer"] = "I'm sorry, I don't have an answer for that question."
        
        return state
    
    def _visualization_agent(self, state: WorkflowState) -> WorkflowState:
        return run_visualization(state, self.llm, visualization_prompt, get_callback_config)

    def _follow_up_questions_agent(self, state: WorkflowState) -> WorkflowState:
        return run_followups(state, self.llm, follow_up_questions_prompt)


    def run_stream_workflow(self, question: str, thread_id: str, collection_name: str = "semantics"):
        # Load conversation history from Redis
        redis_history = self.redis_session.get_conversation_history(thread_id, limit=10)
        langchain_history = convert_redis_to_langchain_messages(redis_history)
        
        # Save user question to Redis
        self.redis_session.add_message(thread_id=thread_id, role="user", content=question)
        
        input_state = WorkflowState(
            history=langchain_history,
            question=question,
            intent="",
            selected_tables=[],
            semantic_info="",
            sql_query="", 
            query_result="", 
            needs_clarification="", 
            visualization_data={},
            final_answer="",
            error_message="",
            collection_name=collection_name,
            retry_count=0,
            has_sql_error=False,
            error_history=[],
            thread_id=thread_id  # Store thread_id in state for agents to access
        )
        
        try:
            workflow = self._build_workflow()
            graph = workflow.compile()  # No checkpointer needed

            config = {"configurable": {"thread_id": thread_id}}
            # User-facing status messages for each node
            user_friendly_messages = {
                "intent_classification": "Understanding what you need...",
                "greeting": "Saying hello 👋...",
                "help_agent": "Gathering helpful information...",
                "populate_qdrant_data": "Finding the most relevant information for you...",
                "text_to_sql": "Figuring out the best way to answer your question...",
                "execute_sql_query": "Processing your request...",
                "clarification_agent": "Making sure I understood you correctly...",
                "summarizer": "Summarizing the key points...",
                "visualization": "Creating a visual overview...",
                "follow_up_questions": "Thinking of helpful next steps...",
                "noanswer": "Sorry, I couldn't find a clear answer this time."
            }
            
            # Track the latest state during streaming
            latest_state = input_state.copy()
            
            for chunk in graph.stream(
                input=input_state,
                config=config,
                stream_mode="updates",
            ):
                for node_name, update in chunk.items():
                    # Update our tracked state with the latest values
                    if isinstance(update, dict):
                        latest_state.update(update)
                    
                    update_response = StreamResponse(
                        type="node_update",
                        data={
                            "node": node_name,
                            "message": user_friendly_messages.get(node_name, "Working on it...")
                        },
                        node=node_name,
                        thread_id=thread_id,
                        timestamp=datetime.now().isoformat(),
                    )
                    yield f"data: {update_response.model_dump_json()}\n\n"

            # Extract final values from the tracked state
            final_answer = latest_state.get("final_answer", "")
            visualization_data = latest_state.get("visualization_data", {})
            sql_query = latest_state.get("sql_query", "")
            follow_up_questions = latest_state.get("follow_up_questions", {})

            completion_response = StreamResponse(
                type="final_answer",
                data={"final_answer": final_answer,"visualization_data":visualization_data,"sql_query":sql_query,"follow_up_questions":follow_up_questions},
                thread_id=thread_id,
                timestamp=datetime.now().isoformat(),
            )
            yield f"data: {completion_response.model_dump_json()}\n\n"
            
        except Exception as e:
            import traceback
            print(f"Error in streaming workflow: {e}")
            print(traceback.format_exc())
            # Send error response
            error_response = StreamResponse(
                type="error",
                data={"error": str(e)},
                thread_id=thread_id,
                timestamp=datetime.now().isoformat(),
            )
            yield f"data: {error_response.model_dump_json()}\n\n"

