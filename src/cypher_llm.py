from abc import ABC, abstractmethod
from openai import OpenAI
from peft import PeftModel, PeftConfig
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)


from src.prompting.cypher_prompts import CHAT_CYPHER_EXAMPLES, CYPHER_GENERATION_INSTRUCTION



class CypherQueryGenerator(ABC):

    def __init__(self, model_name: str, instruction_template: str = None):
        
        self.model_name = model_name
        
        self.model_generate_parameters = {
            "top_p": 0.9,
            "temperature": 0.2, 
            "max_new_tokens": 512,
            "do_sample": True,
            # "pad_token_id": self.tokenizer.eos_token_id,
        }
 
        if instruction_template is not None:
            self.instruction = instruction_template
        else:
            self.instruction = CYPHER_GENERATION_INSTRUCTION
 

    @abstractmethod
    def __call__(self, question: str, schema: str) -> str:
        return

    def _preprocess_input_chat(self, question: str, schema: str) -> list[dict]:
        chat = [
            {
                "role": "user",
                "content": CYPHER_GENERATION_INSTRUCTION,
            },
            {
                "role": "assistant",
                "content": "Alright, from now on I will answer by writing only Cypher queries."
            }
        ] + CHAT_CYPHER_EXAMPLES + [
            {
                "role": "user",
                "content": f"Question: {question}\nCypher output:"
            }
        ]
        
        return chat

    def _postprocess_output_cypher(self, output_cypher: str) -> str:
        # Remove any explanation. E.g.  MATCH...\n\n**Explanation:**\n\n -> MATCH...
        # Remove cypher indicator. E.g.```cypher\nMATCH...```` --> MATCH...
        # Note: Possible to have both:
        #   E.g. ```cypher\nMATCH...````\n\n**Explanation:**\n\n --> MATCH...
        partition_by = "**Explanation:**"
        output_cypher, _, _ = output_cypher.partition(partition_by)
        output_cypher = output_cypher.strip("`\n")
        output_cypher = output_cypher.lstrip("cypher\n")
        output_cypher = output_cypher.strip("`\n ")
        return output_cypher



class CypherQueryGeneratorViaAPI(CypherQueryGenerator):
    """
    This variant calls an endpoint containing the model. The endpoint is defined by calling `vllm serve [model_name]`.
    """

    def __init__(self, model_name: str, instruction_template: str = None, openai_api_base_url: str = "http://localhost:8000/v1", openai_api_key: str = "EMPTY"):

        super().__init__(model_name, instruction_template)

        self.openai_api_key = openai_api_key
        self.open_api_base = openai_api_base_url

        self.client = OpenAI(api_key=openai_api_key, base_url=openai_api_base_url)

    def __call__(self, question: str, schema: str) -> str:

        chat_response = self.client.chat.completions.create(
            model=self.model_name,
            messages=self._preprocess_input_chat(question, schema),
            max_tokens=self.model_generate_parameters['max_new_tokens'],
            temperature=self.model_generate_parameters['temperature'],
            top_p=self.model_generate_parameters['top_p'],
        )

        return chat_response.choices[0].message.content
        

        

class CypherQueryGeneratorLocal(CypherQueryGenerator):
    """
    This variant runs the model locally on the machine.
    """

    def __init__(self, model_name: str, instruction_template: str = None):

        super().__init__(model_name, instruction_template)

        #bnb_config = BitsAndBytesConfig(
        #    load_in_4bit=True,
        #    bnb_4bit_use_double_quant=True, # True for double quantization
        #    bnb_4bit_quant_type="nf4",
        #    bnb_4bit_compute_dtype=torch.bfloat16,
        #)

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            # quantization_config=bnb_config,
            torch_dtype=torch.bfloat16,
            attn_implementation="eager",
            # low_cpu_mem_usage=True,
        )

        device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")

        self.model = self.model.to(device)

        self.model.eval()

        self.model_generate_parameters['pad_token_id'] = self.tokenizer.eos_token_id
    
    def __call__(self, question: str, schema: str) -> str:

        new_message = [self._preprocess_input_chat(question=question, schema=schema)]
        prompt = self.tokenizer.apply_chat_template(new_message, add_generation_prompt=True, tokenize=False)
        inputs = self.tokenizer(prompt, return_tensors="pt", padding=True)

        inputs.to(self.model.device)

        with torch.no_grad():
            tokens = self.model.generate(**inputs, **self.model_generate_parameters)
            tokens = tokens[:, inputs.input_ids.shape[1]:]
            raw_outputs = self.tokenizer.batch_decode(tokens, skip_special_tokens=True)
            outputs = [self._postprocess_output_cypher(output) if not isinstance(output, str) else output for output in raw_outputs]
        
        return outputs[0]


if __name__ == "__main__":

    model_name = "neo4j/text2cypher-gemma-2-9b-it-finetuned-2024v1"

    question = "What are the movies of Tom Hanks?"
    schema = "(:Actor)-[:ActedIn]->(:Movie)" # Check the NOTE below on creating your own schemas

    cypher_generator = CypherQueryGenerator(model_name)
    outputs = cypher_generator([question], schema)
    print(outputs)
    # > ["MATCH (a:Actor {Name: 'Tom Hanks'})-[:ActedIn]->(m:Movie) RETURN m"]
