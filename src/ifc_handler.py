import json
import neo4j
import ifcopenshell
from langchain_neo4j import Neo4jGraph
from neo4j_graphrag.schema import get_schema
import logging
from neo4j import GraphDatabase
from tqdm import tqdm

from src.ifc2graph.custom_graph import CustomGraph
from src.ifc2graph.custom_neo4j import CustomNeo4j


class IFCGraphHandler():

    def __init__(self, uri: str, username: str, password: str, database: str, ifc_path: str = None):

        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self.ifc_path = ifc_path
        
        self.driver = GraphDatabase.driver(self.uri, auth=(self.username, password), database=self.database)

        self.topologic_graph = None
        self.neo_4j_graph = None

        if ifc_path is not None:
            self.reset_graph(ifc_path)
        
        self.graph_schema = get_schema(driver=self.driver)
            
    def reset_graph(self, path: str):
        
        logging.info("Processing IFC file...")
        self.topologic_graph = CustomGraph.ByIFCPath(path, transferDictionaries=True)
        logging.info("IFC data loaded.")

        logging.info("Resetting Neo4j session...")
        self._reset_neo4j_session()
        self.neo_4j_graph = CustomNeo4j.ByGraph(
            neo4jGraph=self.driver, 
            graph=self.topologic_graph,
            vertexLabelKey="IFC_type",
            edgeLabelKey="IFC_type",
            bidirectional=True,
            silent=True
        )
        logging.info("Neo4j graph loaded.")

        self.graph_schema = get_schema(driver=self.driver)

        # Save schema
        filename = self.ifc_path.split("/")[-1].split(".")[0] if self.ifc_path is not None else self.database
        with open(f"data/schema/{filename}.schema", "w") as f:
                f.write(self.graph_schema) 
        
        logging.info("Graph schema computed.")

    
    def save_graph_schema(self, path: str, structured: bool = False):
        
        self.langchain_graph.refresh_schema()
        schema = self.langchain_graph.get_schema
        structured_schema = self.langchain_graph.get_structured_schema
        
        if structured:
            with open(path, "w") as f:
                json.dump(structured_schema, f)
        else:
            with open(path, "w") as f:
                f.write(schema) 
    
    def execute_cypher_query(self, cypher_query: str) -> str:

        try:
            records, summary, _ = self.driver.execute_query(cypher_query, database_=self.database)
        except neo4j.exceptions.CypherSyntaxError:
            return "'No information retrieved.'"
        
        return str(records)

    def _wrap_graph(self) -> Neo4jGraph:
        return Neo4jGraph(
            url=self.uri, username=self.username, password=self.password, database=self.database, refresh_schema=True #, enhanced_schema=True
        )

    def _reset_neo4j_session(self):
        with self.driver.session() as session:
            # Clear existing data (optional)
            session.run("MATCH (n) DETACH DELETE n")


# Example usage
def main():

    # Neo4j connection details
    uri = "neo4j://localhost:7687"
    username = "neo4j"
    password = "123456zazpi"
    
    databases = ["Technical_school-current_m"] # ["AC20-FZK-Haus", "Technical_school-current_m"]

    for database in databases: 
        ifc_graph = IFCGraphHandler(uri, username, password, "neo4j")
    
        query = """MATCH (n:IfcBuildingStorey)
RETURN n
LIMIT 5""".strip()
        ifc_graph.execute_cypher_query(query)


if __name__ == "__main__":
    main()