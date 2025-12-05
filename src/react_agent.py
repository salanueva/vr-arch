import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class ToolResult:
    """Stores the result of a tool execution"""
    tool_name: str
    input: str
    output: str
    success: bool
    
@dataclass 
class AgentStep:
    """Stores one reasoning-action step"""
    thought: str
    action: str
    action_input: str
    observation: str
    code: Optional[str] = None


class ReActAgent:
    """
    ReAct agent that reasons about which tools to use and chains them together.
    Supports iterative reasoning and acting until task is complete.
    """
    
    def __init__(self, helper_llm, max_iterations: int = 5):
        """
        Args:
            helper_llm: HelperLLM instance for reasoning
            max_iterations: Maximum number of reasoning-action iterations
        """
        self.helper_llm = helper_llm
        self.max_iterations = max_iterations
        self.available_tools = {
            "query_building": {
                "name_for_model": "query_building",
                "name_for_human": "Graph Querying API",
                "description_for_model": "Graph Querying API is used to retrieve information from the building database using natural language queries. Returns raw data from the Neo4j database. Input should be a question about building elements, their properties, or relationships. It is also possible to query about a specific ID retrieved from the sandbox.",
                "examples": "'How many doors are there?', 'How many windows are there per floor?', 'Get the height of the door with ID xyz'"
            },
            "retrieve_building": {
                "name_for_model": "retrieve_building",
                "name_for_human": "Building Retrieval API",
                "description_for_model": "The Building Retrieval API is used to retrieve specific building element ID(s) from the sandbox environment based on spatial or descriptive queries. Use this when you need to identify elements before querying their properties.",
                "examples": "'Get the ID of the window in front of me', 'Find the name of the left door', 'Get the height of the stairs in sight'"
            },
            "modify_building": {
                "name_for_model": "modify_building",
                "name_for_human": "Building Modification API",
                "description_for_model": "The Building Modification API is used to modify building elements in the environment. Input should be a modification request. Can also be used to get spatial information like 'what is in front of me' or 'the one on the left'.",
                "examples": "'Change the window color to red', 'Hide all stairs', 'Rotate the visible door 90 degrees counter clockwise', 'Move to the other side of the window and look back at it'"
            },
            "finish": {
                "name_for_model": "finish",
                "name_for_human": "Finish Tool",
                "description_for_model": "The Finish Tool is used when you have enough information to answer the user's question. Input should be the final answer to provide to the user.",
                "examples": "'The building has 24 windows.', 'The door in front of you is named Innentuer-3.', 'I have hidden all the stairs in the building.'"
            }
        }
        # Few-shot examples
        self.examples = [
            {
                "query": "How many windows are in the building?",
                "steps": [
                    {
                        "thought": "This is a straightforward information retrieval query about counting windows.",
                        "action": "query_building",
                        "action_input": "How many windows are in the building?",
                        "observation": "[<Record windowCount=24>]"
                    },
                    {
                        "thought": "I have the answer the user needs.",
                        "action": "finish",
                        "action_input": "There are 24 windows in the building.",
                        "observation": "Task completed"
                    }
                ]
            },
            {
                "query": "Hide the left door",
                "steps": [
                    {
                        "thought": "This is a direct modification request that doesn't require querying first.",
                        "action": "modify_building",
                        "action_input": "Hide the left door",
                        "observation": "The query was successfully followed."
                    },
                    {
                        "thought": "The modification is complete. I can now conclude the task.",
                        "action": "finish",
                        "action_input": "I've hidden all the stairs in the building.",
                        "observation": "Task completed"
                    }
                ]
            },
            {
                "query": "What is the height of the door in front of me?",
                "steps": [
                    {
                        "thought": "To answer this, I first need to identify which door is in front of the user using the retrieve_building tool.",
                        "action": "retrieve_building",
                        "action_input": "Get the ID of the door in front of me",
                        "observation": "1TAGlQkKXEnQ4lBJfHnOcM"
                    },
                    {
                        "thought": "Now I have the door ID. I need to query the database to get the name property of this specific door.",
                        "action": "query_building",
                        "action_input": "What is the height of the door with ID 1TAGlQkKXEnQ4lBJfHnOcM?",
                        "observation": "height = 14.0"
                    },
                    {
                        "thought": "I now have all the information needed to answer the user's question.",
                        "action": "finish",
                        "action_input": "The height of the door is 14.0 units.",
                        "observation": "Task completed"
                    }
                ]
            },
        ]
        
    def _format_examples(self) -> str:
        """Format few-shot examples for the prompt"""
        examples_text = ""
        
        for i, example in enumerate(self.examples, 1):
            examples_text += f"\n{'='*50}\nExample {i}:\n{'='*50}\n"
            examples_text += f"User Question: {example['query']}\n\n"
            
            for step_num, step in enumerate(example['steps'], 1):
                examples_text += f"Thought: {step['thought']}\n"
                examples_text += f"Action: {step['action']}\n"
                examples_text += f"Action Input: {step['action_input']}\n"
                examples_text += f"Observation: {step['observation']}\n\n"
        
        return examples_text


        
        
        
        # Few-shot examples
        self.examples = [
            {
                "query": "How many windows are in the building?",
                "steps": [
                    {
                        "thought": "This is a straightforward information retrieval query about counting windows.",
                        "action": "query_building",
                        "action_input": "How many windows are in the building?",
                        "observation": "There are 24 windows in the building."
                    },
                    {
                        "thought": "I have the answer the user needs.",
                        "action": "finish",
                        "action_input": "There are 24 windows in the building.",
                        "observation": "Task completed"
                    }
                ]
            },
            {
                "query": "What is the name of the door in front of me?",
                "steps": [
                    {
                        "thought": "To answer this, I first need to identify which door is in front of the user, then query its properties.",
                        "action": "modify_building",
                        "action_input": "Get the ID of the door in front of me",
                        "observation": "The door in front of you has ID: door_12345"
                    },
                    {
                        "thought": "Now I have the door ID. I need to query the database to get the name property of this specific door.",
                        "action": "query_building",
                        "action_input": "What is the name of the door with ID door_12345?",
                        "observation": "The door with ID door_12345 has the name 'Innentuer-3'."
                    },
                    {
                        "thought": "I now have all the information needed to answer the user's question.",
                        "action": "finish",
                        "action_input": "The door in front of you is named 'Innentuer-3'.",
                        "observation": "Task completed"
                    }
                ]
            },
            {
                "query": "Hide all the stairs",
                "steps": [
                    {
                        "thought": "This is a direct modification request that doesn't require querying first.",
                        "action": "modify_building",
                        "action_input": "Hide all the stairs",
                        "observation": "Successfully hidden all stair elements in the building."
                    },
                    {
                        "thought": "The modification is complete. I can now conclude the task.",
                        "action": "finish",
                        "action_input": "I've hidden all the stairs in the building.",
                        "observation": "Task completed"
                    }
                ]
            }
        ]
        
    def _format_examples(self) -> str:
        """Format few-shot examples for the prompt"""
        examples_text = ""
        
        for i, example in enumerate(self.examples, 1):
            examples_text += f"\n{'='*50}\nExample {i}:\n{'='*50}\n"
            examples_text += f"User Question: {example['query']}\n\n"
            
            for step_num, step in enumerate(example['steps'], 1):
                examples_text += f"Thought: {step['thought']}\n"
                examples_text += f"Action: {step['action']}\n"
                examples_text += f"Action Input: {step['action_input']}\n"
                examples_text += f"Observation: {step['observation']}\n\n"
        
        return examples_text


        
    def _create_react_prompt(self, query: str, history: List[AgentStep]) -> str:
        """Create the ReAct prompt with reasoning format and few-shot examples"""
        
        TOOL_DESC = """{name_for_model}: Call this tool to interact with the {name_for_human} API.\nWhat is the {name_for_human} API useful for?\n{description_for_model}\nExamples: {examples}"""
        tools_name_text = ", ".join(list(map(lambda t: t["name_for_model"], self.available_tools.values())))
        tools_text = "\n\n".join([
            TOOL_DESC.format(**tool) 
            for tool in self.available_tools.values()
        ])
        
        # Format few-shot examples
        examples_text = self._format_examples()
        
        # Format conversation history
        history_text = ""
        if history:
            history_text = f"\n{'='*50}\nCurrent Task Progress:\n{'='*50}\n"
            history_text += f"User Question: {query}\n\n"
            for i, step in enumerate(history, 1):
                history_text += f"Thought: {step.thought}\n"
                history_text += f"Action: {step.action}\n"
                history_text += f"Action Input: {step.action_input}\n"
                history_text += f"Observation: {step.observation}\n\n"

        
#         prompt = f"""You are an intelligent agent that helps users interact with building information models (BIM).
# You can reason step-by-step and use tools to answer questions or make modifications to buildings.

# Available Tools:
# {tools_description}

# You must use this exact format for your responses:

# Thought: [Think about what you need to do next]
# Action: [Choose one tool from: {', '.join(self.available_tools.keys())}]
# Action Input: [The input for the chosen tool]

# After each action, you will receive an Observation with the result. Then continue with another Thought/Action/Action Input, or use the 'finish' tool if you have the final answer.

# IMPORTANT RULES:
# 1. Always start with a Thought about what information you need
# 2. If you need to identify a specific element (like "door in front of me"), use modify_building tool first to get its ID
# 3. If you need to query properties of a specific element, use query_building tool with the ID
# 4. Chain tools when necessary - use output from one tool as input to another
# 5. When you have the final answer, use the 'finish' tool with your complete answer as the Action Input
# 6. Be concise in your thoughts and actions
# 7. Always follow the exact format: Thought, Action, Action Input

# Here are some examples of how to solve tasks:
# {examples_text}"""
        
        prompt = f"""You are an intelligent agent that helps users interact with building information models (BIM).
Answer the following questions as best you can. You have access to the following tools:

{tools_text}

Important rules:
1. If you need to identify a specific element (like "door in front of me"), use modify_building tool first to get its ID.
2. If you need to query properties of a specific element, use query_building tool with the ID (IFC_global_id in the schema).
3. Chain tools when necessary - use output from one tool as input to another.
4. Be concise.

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tools_name_text}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can be repeated zero or more times)
Thought: I now know the final answer
Action: finish
Action Input: the final answer to the original input question

Here are some example of how to solve tasks using these tools (DO NOT take the examples' information into account, they are only for reference):
{examples_text}

The examples have finished. Now, Begin!
        """

        if history:
            prompt += f"{history_text}\n"
        else:
            prompt += f"\n\nQuestion: {query}\nThought:"
        
        #print(prompt[-800:], "=========================================================================END PROMPT")
        return prompt
    
    def _parse_action(self, llm_output: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Parse the LLM output to extract Thought, Action, and Action Input"""
        
        # Extract Thought
        thought_match = re.search(r'Thought:\s*(.+?)(?=\nAction:|$)', llm_output, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else None
        
        # Extract Action
        action_match = re.search(r'Action:\s*(.+?)(?=\n|$)', llm_output)
        action = action_match.group(1).strip() if action_match else None
        
        # Extract Action Input
        action_input_match = re.search(r'Action Input:\s*(.+?)(?=\n\n|$)', llm_output, re.DOTALL)
        action_input = action_input_match.group(1).strip() if action_input_match else None
        
        return thought, action, action_input
    
    def run(self, query: str, tool_executors: Dict[str, callable]) -> tuple[str, List[AgentStep]]:
        """
        Run the ReAct agent loop
        
        Args:
            query: User's input query
            tool_executors: Dictionary mapping tool names to their executor functions
                           Example: {'query_building': query_func, 'modify_building': modify_func}
        
        Returns:
            final_answer: The final answer to the user's query
            steps: List of all reasoning and action steps taken
        """
        
        history: List[AgentStep] = []
        
        for iteration in range(self.max_iterations):
            # Generate reasoning and action
            prompt = self._create_react_prompt(query, history)
            
            input_data = {
                "query": query,
                "prompt": prompt
            }
            
            llm_output = self.helper_llm(
                input_data=input_data, 
                instruction_type="react_reasoning"
            )
            
            # Parse the output
            thought, action, action_input = self._parse_action(llm_output)
            
            if not action or not action_input:
                # If parsing fails, return what we have
                return f"I encountered an issue processing your request. Here's what I was thinking: {thought}", history
            
            # Check if we're done
            if action.lower() == "finish":
                        
                step = AgentStep(
                    thought=thought or "",
                    action=action,
                    action_input=action_input,
                    observation="Task completed"
                )
                history.append(step) 
                return action_input, history
            
            # Execute the action
            observation, extra_body = self._execute_tool(action, action_input, tool_executors)
            
            # Store the step
            step = AgentStep(
                thought=thought or "",
                action=action,
                action_input=action_input,
                observation=observation,
                code=extra_body
            )
            history.append(step)
            
            # Check if we hit max iterations
            if iteration == self.max_iterations - 1:
                return "I've reached the maximum number of steps. Here's what I found: " + observation, history
        
        return "Task completed", history
    
    def _execute_tool(self, tool_name: str, tool_input: str, tool_executors: Dict[str, callable]) -> str:
        """Execute a tool and return its observation"""
        
        tool_name_lower = tool_name.lower().strip()
        
        if tool_name_lower not in tool_executors:
            return f"Error: Tool '{tool_name}' not found. Available tools: {list(tool_executors.keys())}"
        
        try:
            result = tool_executors[tool_name_lower](tool_input)
            return result
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"
    
    def format_trajectory(self, steps: List[AgentStep]) -> str:
        """Format the agent's trajectory for display or logging"""
        
        trajectory = "Agent Trajectory:\n" + "="*50 + "\n"
        
        for i, step in enumerate(steps, 1):
            trajectory += f"\n--- Step {i} ---\n"
            trajectory += f"Thought: {step.thought}\n"
            trajectory += f"Action: {step.action}\n"
            trajectory += f"Action Input: {step.action_input}\n"
            trajectory += f"Observation: {step.observation}\n"
        
        return trajectory