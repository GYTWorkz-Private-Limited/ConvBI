import json
from langchain_core.prompts import ChatPromptTemplate

def run(state, llm, prompt, get_callback_config):
    try:
        chat_prompt = ChatPromptTemplate.from_messages(prompt)
        chain = chat_prompt | llm
        prez_conv = state["history"][-1:] if state["history"] else []
        
        # Clean the result content - remove markdown code blocks if present
        result = chain.invoke({
            "question": state["question"],
            "query_result": state.get("query_result", ""),
            "history": prez_conv,
            "sql_query": state.get("sql_query", ""),
        }, config=get_callback_config("visualization"))
        
        content = result.content.strip()
        
        # Remove markdown code blocks if present
        if content.startswith("```"):
            # Remove ```json or ``` at start and end
            lines = content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines).strip()
        
        # Parse JSON
        viz_data = json.loads(content)
        
        # Store as dict/object (not string)
        state["visualization_data"] = viz_data if viz_data else {}
        
    except json.JSONDecodeError as e:
        # Return empty dict on error
        state["visualization_data"] = {}
    except Exception as e:
        state["visualization_data"] = {}
    
    return state

