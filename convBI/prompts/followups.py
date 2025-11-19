follow_up_questions_prompt = [("human", """
You are given:
- Question: {question}
- Conversation History: {history}
- Semantic Info: {semantic_info}
- Query Result: {query_result}

Task:
Generate exactly 3 simple follow-up questions that are relevant to the given inputs.

Output Format:
Return only a JSON object in the following structure:
{{"follow_up_questions": ["question1", "question2", "question3"]}}

Rules:
- Do not include explanations or any text outside the JSON.
- Do not add code fences (```).
""")]



