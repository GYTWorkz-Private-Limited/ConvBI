import json
from langchain_core.prompts import ChatPromptTemplate

def run(state, llm, prompt):
    chat_prompt = ChatPromptTemplate.from_messages(prompt)
    chain = chat_prompt | llm
    result = chain.invoke({
        "question": state["question"],
        "history": state.get("history", []),
        "semantic_info": state.get("semantic_info", {}),
        "query_result": state.get("query_result", "")
    })
    state["follow_up_questions"] = json.loads(result.content.strip())
    return state

