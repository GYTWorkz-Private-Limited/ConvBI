summarizer_prompt = [
    ("human", """
Summarize the query result based on the user's question and conversation context.

User question: {question}
Query result: {query_result}
Previous conversation: {history}

Guidelines:
- Be clear, concise, and context-aware
- Highlight key numbers, trends, and comparisons if implied by the conversation
- Avoid domain-specific jargon

Respond with only the summary. No explanation needed.""")
]


