ROUTER_PROMPT = """
Classify the user query into one of the two categories: "query" or "modify".

Definitions:
- "query": The user is requesting **information** (e.g., how many elements, list all elements, etc.)
- "modify": The user wants to **change** something in the model (e.g., move, hide, color, resize, etc.)

Examples:
1. Query: "How many windows are there?" → query  
2. Query: "List all the doors in the building " → query  
3. Query: "Change the stairs color to red" → modify  
4. Query: "Hide the walls" → modify  

Now classify the following input:
Query: {query}
Classification (only one word: "query" or "modify"):
""".strip()