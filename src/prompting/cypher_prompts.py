CYPHER_GENERATION_INSTRUCTION = """
Generate Cypher statement to query a graph database.
Use only the provided relationship types and properties in the schema.
Schema: {schema}

If the question refers to specific objects by ID, always use the property IFC_global_id for matching (e.g., WHERE n.IFC_global_id = '<ID>' or WHERE n.IFC_global_id IN [<IDs>]).
When the question asks for the name or properties of an object:
- Use n.IFC_name to return its name and n.IFC_type to return its type.
- For bbox dimensions (height, width, depth, or volume), parse the bbox_dimensions JSON property and access the specific dimension with the pattern apoc.convert.fromJsonMap(n.bbox_dimensions).bbox_<dimension> where <dimension> is one of: bbox_height, bbox_width, bbox_depth, or bbox_volume (e.g., apoc.convert.fromJsonMap(n.bbox_dimensions).bbox_height AS height).

When answering, provide ONLY the Cypher query without any explanation or markdown formatting.
""".strip()


CYPHER_VERBALIZATION_PROMPT = """
Answer the query with the related metadata.
Query: {query}
Metadata: {metadata}
Answer: 
""".strip()

CHAT_CYPHER_EXAMPLES = [
    {
        "role": "user",
        "content": "Question: Which walls have doors in them?\nCypher output:",
    },
    {
        "role": "assistant",
        "content": """MATCH (w:IfcWallStandardCase)-[:IfcRelVoidsElement]->(:IfcOpeningElement)<-[:IfcRelFillsElement]-(d:IfcDoor)
RETURN DISTINCT w""".strip()
    },
#     {
#         "role": "user",
#         "content": "Question: List all stair elements in the scene.\nCypher output:",
#     },
#     {
#         "role": "assistant",
#         "content": """MATCH (s:IfcStair)
# RETURN s""".strip()
#     },
    {
        "role": "user",
        "content": "Question: How many doors are in the building?\nCypher output:",
    },
    {
        "role": "assistant",
        "content": """MATCH (d:IfcDoor)
RETURN count(d) AS numberOfDoors""".strip()
    },
#     {
#         "role": "user",
#         "content": "Question: How many windows are there per floor?\nCypher output:",
#     },
#     {
#         "role": "assistant",
#         "content": """MATCH (w:IfcWindow)-[:IfcRelContainedInSpatialStructure]->(f:IfcBuildingStorey)
# RETURN f.IFC_name AS floor, count(w) AS windowCount""".strip()
#     },
    {
        "role": "user",
        "content": "Question: Show the floor that contains the most doors.\nCypher output:",
    },
    {
        "role": "assistant",
        "content": """MATCH (d:IfcDoor)-[:IfcRelContainedInSpatialStructure]->(s:IfcBuildingStorey)
RETURN s.IFC_name AS storey, count(d) AS doorCount
ORDER BY doorCount DESC
LIMIT 1""".strip()
    },
#     {
#         "role": "user",
#         "content": "Question: What is the width of the object with ID 2MNBtRpLQeZk7sYHdP3xAa?.\nCypher output:",
#     },
#     {
#         "role": "assistant",
#         "content": """MATCH (n)
# WHERE n.IFC_global_id = '2MNBtRpLQeZk7sYHdP3xAa'
# RETURN apoc.convert.fromJsonMap(n.bbox_dimensions).bbox_width AS width""".strip()
#     },
    {
        "role": "user",
        "content": "Question: Return all walls, doors and windows grouped by floors and aggregated by type.\nCypher output:",
    },
    {
        "role": "assistant",
        "content": """MATCH (e)-[:IfcRelContainedInSpatialStructure]->(s:IfcBuildingStorey)
WHERE e:IfcWallStandardCase OR e:IfcDoor OR e:IfcWindow
RETURN s.IFC_name AS storey, labels(e)[0] AS elementType, count(e) AS count
ORDER BY storey, elementType""".strip()
    },
    {
        "role": "user",
        "content": "Question: What is the height of the object with ID 1TAGlQkKXEnQ4lBJfHnOcM?.\nCypher output:",
    },
    {
        "role": "assistant",
        "content": """MATCH (n)
WHERE n.IFC_global_id = '1TAGlQkKXEnQ4lBJfHnOcM'
RETURN apoc.convert.fromJsonMap(n.bbox_dimensions).bbox_height AS height""".strip()
    },
    {
        "role": "user",
        "content": "Question: What are the names of the wall with ID 3QPLxDzTWeHm9cJFkR4sVu and the two windows with IDs 1TAGlQkKXEnQ4lBJfHnOcM and 5ZRBmNtHYpVk2aLWcD8qTe?\nCypher output:",
    },
    {
        "role": "assistant",
        "content": """MATCH (n)
WHERE n.IFC_global_id IN ['3QPLxDzTWeHm9cJFkR4sVu', '1TAGlQkKXEnQ4lBJfHnOcM', '5ZRBmNtHYpVk2aLWcD8qTe']
RETURN n.IFC_global_id AS id, n.IFC_name AS name""".strip()
    },
    # { #EDO BESTE MODU BATEN
        # "role": "assistant",
        # "content": """MATCH (n)
# WHERE n.IFC_global_id = '0KMpiAlnb52RgQuM1CwVfd'
# WITH n, n.bbox_dimensions AS json
# RETURN toFloat(split(split(json, '"bbox_height": ')[1], ',')[0]) AS height""".strip()
#     },

]