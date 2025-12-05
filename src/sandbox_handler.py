from abc import ABC
import logging

from src.luminous.luminous import Luminous
from src.luminous.luminous_ifc import IFC, Entity



class SandboxHandler(ABC):

    def __init__(self):
                
        self.sandbox = Luminous() 
        self.ifc = None

    @classmethod
    def from_ifc(cls, ifc_filename: str) -> "SandboxHandler":
        sandbox = cls()
        sandbox.reset_ifc(ifc_filename)
        return sandbox
    

    def reset_ifc(self, ifc_filename: str) -> None:
        self.sandbox.reset()
        self.ifc = IFC(self.sandbox.load_ifc(ifc_filename))
        

    def __call__(self, code: str, return_result: bool = False) -> str:
        """
        Execute code in the sandbox environment.
        
        Args:
            code: Python code to execute
            return_result: If True, returns the value of 'result' variable from executed code.
                          If False, returns success/error message (default behavior)
        
        Returns:
            String containing either the result value or a success/error message
        """
        variables = {"l": self.sandbox, "ifc": self.ifc, "IFC": IFC, "Entity": Entity, "result": None }
        logging.debug("Attempting to execute code...")
        try:
            exec(code, variables)
            self.ifc = variables["ifc"] # if not none print id
            if return_result:
                result_value = variables.get("result", None)
                if result_value is not None:
                    logging.debug(f"Code executed successfully! Result: {result_value}")
                    return str(result_value)
                else:
                    logging.warning("Code executed but no 'result' variable was set")
                    return "No result was returned from the code execution."
        except Exception as e:
            logging.error("Error executing code: %s", e)
            return "There was an error when trying to fulfill the query."
        logging.debug("Code executed successfully!")
        return "The query was successfully followed."