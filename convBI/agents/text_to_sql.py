from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage

def run(state, llm, prompt, get_callback_config):
    
    chat_prompt = ChatPromptTemplate.from_messages(prompt)
    prev_conv = state["history"][-6:] if state["history"] else []
    chain = chat_prompt | llm
 
    result = chain.invoke({
        "semantic_info": state.get("semantic_info", {}),
        "question": state["question"],
        "selected_tables": state.get("selected_tables", []),
        "history": prev_conv
    }, config=get_callback_config("text_to_sql"))

    state["sql_query"] = result.content.strip()
    #print("Semantic Info:", state.get("semantic_info", {}))

    state["history"] = [
        HumanMessage(content=state["question"]),
        AIMessage(content=state["sql_query"])
    ]
    
    return state

