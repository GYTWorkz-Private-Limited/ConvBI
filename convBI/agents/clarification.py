from langchain_core.prompts import ChatPromptTemplate

def run(state, llm, prompt, get_callback_config):
    state["retry_count"] = state.get("retry_count", 0) + 1

    chat_prompt = ChatPromptTemplate.from_messages(prompt)
    chain = chat_prompt | llm
    result = chain.invoke({
        "question": state["question"],
        "sql_query": state.get("sql_query", ""),
        "error_message": state.get("error_message", ""),
        "semantic_info": state.get("semantic_info", {}),
        "previous_errors": state.get("error_history", [])
    }, config=get_callback_config("debugger"))

    state["sql_query"] = result.content.strip()
    state["has_sql_error"] = False
    return state

