from langchain_core.prompts import ChatPromptTemplate

def run(state, llm, prompt, get_callback_config):
    

    chat_prompt = ChatPromptTemplate.from_messages(prompt)
    prev_conv = state["history"][-6:] if state["history"] else []
    chain = chat_prompt | llm

    result = chain.invoke({
        "question": state["question"],
        "history": prev_conv,
    }, config=get_callback_config("intent_classification"))

    state["intent"] = result.content.strip().lower()
    
    return state

