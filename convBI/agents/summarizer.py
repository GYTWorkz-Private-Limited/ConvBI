from langchain_core.prompts import ChatPromptTemplate

def run(state, llm, prompt, get_callback_config):
    
    chat_prompt = ChatPromptTemplate.from_messages(prompt)
    prez_conv = state["history"][-1:] if state["history"] else []
    chain = chat_prompt | llm
    result = chain.invoke({
        "question": state["question"],
        "history": prez_conv,
        "query_result": state.get("query_result", "")
    }, config=get_callback_config("summarizer"))

    state["final_answer"] = result.content.strip()
    state["history"] = []
    return state

