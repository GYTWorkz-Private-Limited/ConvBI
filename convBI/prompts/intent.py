intent_prompt = [("human", """Classify the user's intent based on their question and full conversation history. 
Current question: {question}
Conversation history: {history} 
Categories: 
- general: General greetings, pleasantries, casual conversation (hi, hello, bye, thanks, good morning, etc.)
- help: Questions about system capabilities, assistance, features, what the system can do (what can you help with, how can you assist me, tell me about yourself, what are your capabilities, how do I use this system, etc.) 
- system_query: Questions about data, database queries, analytics, trends, reports, or any data-related inquiries

IMPORTANT: 
Use the conversation history to understand context. 
For example: 
- If previous questions were about data and current question is a follow-up (e.g., "What about X?"), classify as system_query 
- If this is a follow-up question referencing previous data queries, classify as system_query 
- If user asks about system features or capabilities, classify as help 

Respond with only the category name (general, help, or system_query)""") ]


