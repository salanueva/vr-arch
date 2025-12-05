from abc import ABC, abstractmethod
from openai import OpenAI
import os
import re
from peft import PeftModel, PeftConfig
import torch

from google import genai
from google.genai import types

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)
from src.prompting.sandbox_prompts import SANDBOX_PROMPT, SANDBOX_VERBALIZATION_PROMPT
from src.prompting.cypher_prompts import CYPHER_VERBALIZATION_PROMPT
from src.prompting.router_prompts import ROUTER_PROMPT
from src.prompting.retrieval_prompts import RETRIEVAL_PROMPT, CHAT_RETRIEVAL_EXAMPLES

import re

class HelperLLM(ABC):

    def __init__(self, model_name: str, instruction_templates: dict[str] = None, enable_thinking: bool = False):
        
        self.model_name = model_name
        
        self.model_generate_parameters = {
            "best_of": 1, 
            "top_p": 1, 
            "top_k": 1, 
            "use_beam_search": True,
            "temperature": 0.0, 
            "max_new_tokens": 4096
            # "do_sample": True,
            # "pad_token_id": self.tokenizer.eos_token_id,
        }

        if "Qwen3" in model_name:
            self.model_generate_parameters["enable_thinking"] = enable_thinking

        self.is_google = False
 
        if instruction_templates is not None:
            self.instructions = instruction_templates
        else:
            self.instructions = {
                "cypher_verbalization": CYPHER_VERBALIZATION_PROMPT,
                "sandbox_verbalization": SANDBOX_VERBALIZATION_PROMPT,
                "sandbox_api": SANDBOX_PROMPT,
                "retrieval_api": RETRIEVAL_PROMPT,
                "query_classification": ROUTER_PROMPT
            }
 

    @abstractmethod
    def __call__(self, input_data: dict[str, str], instruction_type: str) -> str:
        return


    def _preprocess_input_chat(self, input_data: dict[str, str], instruction_type: str) -> list[dict]:
        if instruction_type == "sandbox_api":
            content = self.instructions[instruction_type].format(
                api_documentation=input_data['api_documentation'],
            )
            chat = [
                {
                    "role": "user",
                    "content": content,
                },
                {
                    "role": "assistant",
                    "content": "Alright, from now on I will answer just by writing Python code."
                }
            ] + input_data['api_examples'] + [
                {
                    "role": "user",
                    "content": input_data["query"]
                }
            ]
        elif instruction_type == "sandbox_verbalization":
            content = self.instructions[instruction_type].format(
                query=input_data['query'], outcome=input_data['outcome'] # python_code=input_data['python_code'],
            )
            chat = [
                {
                    "role": "user", 
                    "content": content 
                }  
            ]
        elif instruction_type == "cypher_verbalization":
            content = self.instructions[instruction_type].format(
                query=input_data['query'], metadata=input_data['metadata']
            )
            chat = [
                {
                    "role": "user", 
                    "content": content 
                }  
            ]
        elif instruction_type == "query_classification":
            content = self.instructions[instruction_type].format(
                query=input_data["query"]
            )
            chat = [
                {
                    "role": "user",
                    "content": content
                }
            ]
        elif instruction_type == "retrieval_api":
            content = self.instructions[instruction_type].format(
                api_documentation=input_data['api_documentation'],
            )
            chat = [
                {
                    "role": "user",
                    "content": content,
                },
                {
                    "role": "assistant",
                    "content": "Alright, from now on I will answer just by writing Python code to retrieve IDs."
                }
            ] + CHAT_RETRIEVAL_EXAMPLES + [
                {
                    "role": "user",
                    "content": input_data["query"]
                }
            ]

        elif instruction_type == "react_reasoning":
            chat = [
                # {
                #     "role": "system",
                #     "content": self.instructions[instruction_type]
                # },
                {
                    "role": "user",
                    "content": input_data["prompt"]
                }
            ]
        return chat


    def _postprocess_output_python(self, output_python: str) -> str:
        # Remove any explanation. E.g.  a = 2...\n\n**Explanation:**\n\n -> a = 2...
        # Remove python indicator. E.g.```python\na = 2...``` --> a = 2...
        # Note: Possible to have both:
        #   E.g. ```cypher\a = 2...```\n\n**Explanation:**\n\n --> a = 2...
        partition_by = "**Explanation:**"
        output_python, _, _ = output_python.partition(partition_by)
        output_python = output_python.strip("`\n")
        output_python = output_python.lstrip("python\n")
        output_python = output_python.strip("`\n ")
        output_python = output_python.replace("\t", "    ")
        return output_python


class HelperLLMViaAPI(HelperLLM):
    """
    This variant calls an endpoint containing the model. The endpoint is defined by calling `vllm serve [model_name]`.
    """

    def __init__(self, model_name: str, instruction_templates: dict[str, str] = None, openai_api_base_url: str = "http://localhost:8000/v1", openai_api_key: str = "EMPTY", enable_thinking: bool = False):

        super().__init__(model_name, instruction_templates)

        self.openai_api_key = openai_api_key
        self.open_api_base = openai_api_base_url
        self.model_generate_parameters["do_sample"] = True

        self.client = OpenAI(api_key=openai_api_key, base_url=openai_api_base_url)

    def __call__(self, input_data: dict[str, str], instruction_type: str) -> str:

        stop_sequences = None
        if instruction_type == "react_reasoning":
            stop_sequences = ["Observation:", "\nObservation:", "Observation :", "\nObservation :"]  # Stop before generating observations
    
        try:
            chat_response = self.client.chat.completions.create(
                model=self.model_name,
                messages=self._preprocess_input_chat(input_data, instruction_type),
                temperature=self.model_generate_parameters['temperature'],
                top_p=self.model_generate_parameters['top_p'],
                stop=stop_sequences,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}} # TODO: Make it relative
            )
        except Exception as e:
            return f"Error during API call: {e}"

        if instruction_type == "sandbox_api" or instruction_type == "retrieval_api":
            return self._postprocess_output_python(chat_response.choices[0].message.content)
        else:
            return chat_response.choices[0].message.content
                
        

class HelperLLMLocal(HelperLLM):
    """
    This variant runs the model locally on the machine.
    """

    def __init__(self, model_name: str, instruction_templates: dict[str, str] = None):

        super().__init__(model_name, instruction_templates)

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.bfloat16
        )

        self.model_generate_parameters["do_sample"] = True

    
    def __call__(self, input_data: dict[str, str], instruction_type: str) -> str:

        new_message = self._preprocess_input_chat(input_data=input_data, instruction_type=instruction_type)
        prompt = self.tokenizer.apply_chat_template(new_message, add_generation_prompt=True, tokenize=False)
        inputs = self.tokenizer(prompt, return_tensors="pt", padding=True)

        inputs.to(self.model.device)
        self.model.eval()

        with torch.no_grad():
            tokens = self.model.generate(**inputs, **self.model_generate_parameters)
            tokens = tokens[:, inputs.input_ids.shape[1]:]
            outputs = self.tokenizer.batch_decode(tokens, skip_special_tokens=True)
            if instruction_type == "sandbox_api"  or instruction_type == "retrieval_api":
                outputs = [self._postprocess_output_python(output) if not isinstance(output, str) else output for output in outputs]
        return outputs
