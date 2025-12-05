import argparse
import asyncio
import json
import logging
import time
import yaml

from src.cypher_llm import CypherQueryGeneratorViaAPI
from src.helper_llm import HelperLLM, HelperLLMViaAPI
from src.ifc_handler import IFCGraphHandler
from src.sandbox_handler import SandboxHandler
from src.react_agent import ReActAgent
from src.prompting.sandbox_prompts import API_DOCS, CHAT_API_EXAMPLES
from src.voice_layer import record_audio, asr_from_file


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, default="config.yaml", help="Path to the configuration file")
    args = parser.parse_args()
    return args

def load_all_handlers(config: dict[str, dict[str, object]]) -> tuple[CypherQueryGeneratorViaAPI, HelperLLM, IFCGraphHandler, SandboxHandler]:
    """Load all handlers for both query and modification modes."""
    
    ### Create object that handles IFC data (for query mode)
    uri = config['neo4j']['apiUri']
    username = config['neo4j']['username']
    password = config['neo4j']['password']
    database = config['neo4j']['database']
    
    if config['neo4j']['resetGraph']:
        graph_handler = IFCGraphHandler(uri, username, password, database, ifc_path=config['sandbox']['ifcPath'])
    else:
        graph_handler = IFCGraphHandler(uri, username, password, database)
    logging.info("IFC Graph Handler created")
    
    ### Create object that generates cypher queries (for query mode)
    cypher_model = config['cypherLLM']['model']
    openai_api_cypher_url = config['cypherLLM']['apiUrl']
    openai_api_key = config['cypherLLM']['apiKey']
    cypher_llm = CypherQueryGeneratorViaAPI(
        model_name=cypher_model,
        openai_api_base_url=openai_api_cypher_url, 
        openai_api_key=openai_api_key
    )
    logging.info("Cypher Query client created")
    
    ### Create object that communicates with sandbox (for modification mode)
    sandbox_handler = SandboxHandler.from_ifc(config['sandbox']['ifcPath'])
    logging.info("Sandbox Handler created")

    ### Create object that handles LLM for secondary tasks (both modes)
    model_name = config['helperLLM']['model']
    openai_api_helper_url = config['helperLLM']['apiUrl']
    openai_api_key = config['helperLLM']['apiKey']
    helper_llm = HelperLLMViaAPI(
        model_name=model_name,
        openai_api_base_url=openai_api_helper_url, 
        openai_api_key=openai_api_key
    )
    logging.info("Helper LLM client created")

    return cypher_llm, helper_llm, graph_handler, sandbox_handler


def process_query(input_text: str, graph_handler: IFCGraphHandler, cypher_llm: CypherQueryGeneratorViaAPI, helper_llm: HelperLLM) -> tuple[str, str]:
    """Process information retrieval queries using Neo4j graph."""
    
    start_time = time.time()

    print(f"[QUERY MODE] INPUT: {input_text}")
    cypher_query = cypher_llm(question=input_text, schema=graph_handler.graph_schema)
    cypher_query_time = time.time()

    cypher_output = graph_handler.execute_cypher_query(cypher_query=cypher_query)
    cypher_exec_time = time.time()

    print(f"CYPHER QUERY: {cypher_query.strip()}")
    if cypher_output == "'No information retrieved.'":
        print(" - This query gave an error while executing it.")

    final_output = cypher_output
    print(f"OUTPUT: {final_output}")

    print(f"TIMES: C. query {cypher_query_time-start_time:.2f}s - C. exec {cypher_exec_time-cypher_query_time:.2f}s")

    return final_output, cypher_query


def process_modification(input_text: str, helper_llm: HelperLLM, sandbox_handler: SandboxHandler) -> tuple[str, str]:
    """Process building modification requests using Unreal Engine sandbox."""
    
    start_time = time.time()

    print(f"[MODIFY MODE] INPUT: {input_text}")
    input_data = {
        "query": input_text,
        "api_documentation": API_DOCS,
        "api_examples": CHAT_API_EXAMPLES
    }

    python_code = helper_llm(input_data=input_data, instruction_type="sandbox_api")
    python_code_time = time.time()

    python_outcome = sandbox_handler(code=python_code)
    python_exec_time = time.time()

    logging.info(f"PYTHON CODE:\n{python_code.strip()}")

    final_output = python_outcome
    print(f"OUTPUT: {final_output}")

    print(f"TIMES: P. code {python_code_time-start_time:.2f}s - P. exec {python_exec_time-python_code_time:.2f}s")

    return final_output, python_code

def process_with_react_agent(input_text: str, agent: ReActAgent, graph_handler: IFCGraphHandler, cypher_llm: CypherQueryGeneratorViaAPI, helper_llm: HelperLLM, sandbox_handler: SandboxHandler, verbose: bool = False, return_additionally: list[str] | None = None) -> str:
    """Process query using ReAct agent that can chain multiple tools."""

    # Define tool executor functions that the agent can call
    def query_building_tool(query_input: str) -> tuple[str, str]:
        """Tool for querying building information"""
        try:
            sandbox_handler.sandbox.text_to_speech("Using the query tool")
            result, cypher_query = process_query(query_input, graph_handler, cypher_llm, helper_llm)
            return result, cypher_query
        except Exception as e:
            return f"Error querying building: {str(e)}", ""
    
    def retrieve_building_tool(retrieve_input: str) -> tuple[str, str]:
        """Tool for retrieving building element IDs"""
        try:
            sandbox_handler.sandbox.text_to_speech("Using the retrieve tool")
            start_time = time.time()
            print(f"[RETRIEVE MODE] INPUT: {retrieve_input}")
            
            input_data = {
                "query": retrieve_input,
                "api_documentation": API_DOCS
            }
            
            python_code = helper_llm(input_data=input_data, instruction_type="retrieval_api")
            python_code_time = time.time()
            
            python_outcome = sandbox_handler(code=python_code, return_result=True)
            python_exec_time = time.time()
            
            logging.info(f"RETRIEVAL CODE:\n{python_code.strip()}")
            logging.info(f"RETRIEVAL RESULT: {python_outcome}")
            
            print(f"TIMES: P. code {python_code_time-start_time:.2f}s - P. exec {python_exec_time-python_code_time:.2f}s")
            
            return python_outcome, python_code
        except Exception as e:
            return f"Error retrieving building elements: {str(e)}", ""

    def modify_building_tool(modify_input: str) -> tuple[str, str]:
        """Tool for modifying building elements"""
        try:
            sandbox_handler.sandbox.text_to_speech("Using the modification tool")
            result, python_code = process_modification(modify_input, helper_llm, sandbox_handler)
            return result, python_code
        except Exception as e:
            return f"Error modifying building: {str(e)}", ""
    
    # Map tool names to executor functions
    tool_executors = {
        "query_building": query_building_tool,
        "retrieve_building": retrieve_building_tool,
        "modify_building": modify_building_tool,
    }
    
    # Run the agent
    final_answer, steps = agent.run(input_text, tool_executors)
    
    # Display trajectory if verbose mode
    if verbose and steps:
        print("\n" + "="*60)
        print(agent.format_trajectory(steps))
        print("="*60 + "\n")

    sandbox_handler.sandbox.text_to_speech(final_answer)
    
    if return_additionally == None:
        return final_answer
    else:
        steps_of_interest = []
        for step in steps:
            if step.action in return_additionally:
                steps_of_interest.append(step)
        return final_answer, steps_of_interest

def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO)
    
    with open(args.config, "r") as f:
        config = yaml.safe_load(f)

    # Load all handlers for both modes
    cypher_llm, helper_llm, graph_handler, sandbox_handler = load_all_handlers(config)
    
    # Initialize ReAct agent with config settings
    max_iterations = config['agent']['max_iterations']
    verbose = config['agent']['verbose']
    agent = ReActAgent(helper_llm, max_iterations=max_iterations)

    print("**Unified BIM Assistant**")
    print("- Query examples: 'How many windows are there?', 'List all doors in the building'")
    print("- Modify examples: 'Change the left doors color to red', 'Hide all the visible stairs'")
    print("- Retrieval examples: 'What is the name of the door in front of me?'")
    print("- Press Enter (empty input) to record voice, 'q' to quit")
    print("-" * 60)
    
    if verbose:
        print("- Verbose mode: ON (showing reasoning steps)")

    while True:
        input_text = input("Type input query: ").strip()
        start_time = time.time()
        
        if input_text.lower() == "q":
            break
        elif input_text == "":  # Record audio if empty string
            logging.info("Starting to record for 5 seconds...")
            audio_file = record_audio(seconds=5)
            logging.info("Recording stopped.")
            start_time = time.time()  # Don't include recording time
            
            with open(audio_file, "rb") as f:
                response = asyncio.get_event_loop().run_until_complete(
                    asr_from_file(f)
                )
            json_data = json.loads(response.body)
            
            if json_data['status'] == 'success':
                input_text = json_data['transcript']
                logging.info(f"Input text: {input_text}")
                # sandbox_handler.sandbox.text_to_speech(f"You said: {input_text}")
            else:
                logging.error("STT failed, please retry your query.")
                sandbox_handler.sandbox.text_to_speech("Speech recognition failed, please try again")
                continue
        
        try:
            result = process_with_react_agent(
                input_text, 
                agent,
                graph_handler,
                cypher_llm,
                helper_llm,
                sandbox_handler,
                verbose=verbose
            )
            
            print(f"\nAssistant: {result}\n")
            
        except Exception as e:
            error_msg = f"An error occurred: {str(e)}"
            print(f"\nError: {error_msg}\n")
            sandbox_handler.sandbox.text_to_speech(error_msg)

        end_time = time.time()
        logging.info(f"Total execution time: {end_time-start_time:.2f}s")
        print("-" * 60)


if __name__ == "__main__":
    main()