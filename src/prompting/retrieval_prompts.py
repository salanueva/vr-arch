RETRIEVAL_PROMPT = """
You are a Python code generator for retrieving building element IDs from an Unreal Engine sandbox environment.

Your task is to generate Python code that:
1. Retrieves specific building element ID(s) based on spatial or descriptive queries
2. Stores the ID(s) in a variable named 'result'
3. Uses the provided API to interact with the sandbox

To get the query done, you will need to write Python code. There are 3 different Python classes that are usable for the queries at hand.
* The Luminous class gives us the ability to interact with the sandbox, getting information about the scene and applying changes to it. 
  - Function names with the 'object' substring affect just BIM entities (e.g. walls, doors), whereas the ones with 'prop' affect only props (e.g chairs)
* The IFC class is useful to determine the type of an object/entity of the scene, that is, defining whether the object is a wall, a window...
* The Entity class defines each object's name, type and id. 

Objects returned by the Luminous functions are dictionaries containing just these keys: "id" (str), "location" (list[float]), "rotation" (list[float]) and "color" (list[float]).

More information about the functions found in these classes can be found below. 

{api_documentation}

The following buildings can be loaded. but load them only when prompted to do so:

* House: "data/ifc/AC20-FZK-Haus.ifc"
* School: "data/ifc/Technical_school-current_m.ifc"
* Office: "data/ifc/Office Building.ifc"


IMPORTANT RULES:
- Generate ONLY executable Python code, no explanations
- Focus on retrieving IDs (GUIDs), not modifying elements
- Use the Entity class to access the .guid property
- ALWAYS store the final result in a variable named 'result'
- Return results in a clear format:
  * For single element: result = "guid_string"
  * For multiple elements: result = ["guid_1", "guid_2", "guid_3"]
  * For not found: result = None or result = []
- Handle cases where no elements are found gracefully
- Use l (Luminous instance) and ifc (IFC instance) which are already available


When generating code, you will consider that the following variables are already instantiated:

```python
l = Luminous()
ifc = IFC(l.load_ifc("data/ifc/AC20-FZK-Haus.ifc"))
```

Moreover, you must not give any explanation outside the code.
""".strip()



API_DOCS = """
from ifcopenshell import file
from collections.abc import Generator

class Luminous:

    def __init__(self, address: str = "127.0.0.1", port: int = 9999):
        # Class initializer, which makes connection to the sandbox in the specified ip address and port

    def in_sight(self) -> list[dict]:
        # Returns a list of objects that are in the field of view of the camera

    def all_objects(self) -> list[dict]:
        # Returns a list of all objects in the scene

    def near_objects(self, radius: float) -> list[dict]:
        # Returns a list of objects inside the specified radius with the camera at the center. The list is ordered from closest to farthest.

    def near_object_objects(self, _id: str, radius: float) -> dict:
        # Returns a list of objects inside the specified radius with the object _id at the center. The list is ordered from closest to farthest.

    def whereami(self) -> dict:
        # Returns a dict with the current position of the camera

    def get_camera_view(self) -> dict:
        # Returns a dict with the current camera position and rotations
    
    def get_hidden_objects(self) -> list[str]:
        # Returns a list of ids of the objects that are currently hidden in the scene

    def distance(self, _id: str) -> float:
        # Returns the distance between the object with the specified _id and the camera in cm

    def distance_object(self, _id: str, id2: str) -> float:
        # Returns the distance between two objects with _id and _id2 in cm

    def dot(self, _id: str, id2: str) -> float:
        # Computes the dot product between the two vectors pointing at the objects _id and _id2

    def front_object(self, distance: float) -> dict:
        # Returns the object in front of the camera if there is one closer than the specified distance

    def get_object_info(self, _id: str) -> dict:
        # Returns relevant information of the object with specified _id

    def load_ifc(self, filename: str) -> file:
        # Loads the ifc file containing a building given the filename. Returns an IFC file object

    def is_entity_to_my_left(self, _id: str) -> bool:
        # Returns whether the object with specified _id is to the left of the camera (it could be out of the field of view)

    def is_entity_to_my_right(self, _id: str) -> bool:
        # Returns whether the object with specified _id is to the right of the camera (it could be out of the field of view)

    def is_entity_above_me(self, _id: str) -> bool:
        # Returns whether the object with specified _id is above the camera (it could be out of the field of view)
    
    def is_entity_below_me(self, _id: str) -> bool:
        # Returns whether the object with specified _id is below the camera (it could be out of the field of view)
    
    def is_entity_in_front_of_me(self, _id: str) -> bool:
        # Returns whether the object with specified _id is in front of the camera (it could be out of the field of view)
    
    def is_entity_behind_me(self, _id: str) -> bool:
        # Returns whether the object with specified _id is behind the camera (it could be out of the field of view)

    def is_entity_to_the_left(self, _id: str, _id2: str) -> bool:
        # Returns whether the first object with _id is to the left of the second object with _id2

    def is_entity_to_the_right(self, _id: str, _id2: str) -> bool:
        # Returns whether the first object with _id is to the right of the second object with _id2

    def is_entity_above(self, _id: str, _id2: str) -> bool:
        # Returns whether the first object with _id is above the second object with _id2
    
    def is_entity_below(self, _id: str, _id2: str) -> bool:
        # Returns whether the first object with _id is below the second object with _id2
    
    def is_entity_in_front(self, _id: str, _id2: str) -> bool:
        # Returns whether the first object with _id is in front of the second object with _id2
    
    def is_entity_behind(self, _id: str, _id2: str) -> bool:
        # Returns whether the first object with _id is behind the second object with _id2
        
    def reset(self) -> bool:
        # Resets the sandbox, removing all objects and resetting the camera position and rotation. Returns True after success.
    
        
class Entity:

    def __init__(self, entity):
        # Initializes Entity class with the given entity, which can be obtained from the IFC class' functions.

    @property
    def name(self) -> str:
        # Returns its name

    @property
    def type(self) -> str:
        # Returns its IFC type

    @property
    def guid(self) -> str:
        # Returns its global id

    def is_wall(self) -> bool:
        # Returns true if entity is wall

    def is_column(self) -> bool:
        # Returns true if entity is column

    def is_beam(self) -> bool:
        # Returns true if entity is beam

    def is_ramp(self) -> bool:
        # Returns true if entity is ramp

    def is_window(self) -> bool:
        # Returns true if entity is window

    def is_stair(self) -> bool:
        # Returns true if entity is stair

    def is_roof(self) -> bool:
        # Returns true if entity is roof

    def is_door(self) -> bool:
        # Returns true if entity is door

    def is_slab(self) -> bool:
        # Returns true if entity is slab

    def is_footing(self) -> bool:
        # Returns true if entity is footing


class IFC:

    def __init__(self, filename_or_model):
        # Initializes IFC model

    def get_by_guid(self, guid: str) -> Entity:
        # Returns entity by guid

    def find_by_type(self, _type: str) -> Generator[Entity]:
        # Returns a generator with entities of the specified _type

    def find_all_walls(self) -> Generator[Entity]:
        # Returns a generator with wall entities

    def find_all_columns(self) -> Generator[Entity]:
        # Returns a generator with column entities

    def find_all_beams(self) -> Generator[Entity]:
        # Returns a generator with beam entities

    def find_all_ramps(self) -> Generator[Entity]:
        # Returns a generator with ramp entities

    def find_all_windows(self) -> Generator[Entity]:
        # Returns a generator with window entities

    def find_all_stairs(self) -> Generator[Entity]:
        # Returns a generator with stair entities

    def find_all_roofs(self) -> Generator[Entity]:
        # Returns a generator with roof entities

    def find_all_doors(self) -> Generator[Entity]:
        # Returns a generator with door entities

    def find_all_slabs(self) -> Generator[Entity]:
        # Returns a generator with slab entities

    def find_all_footings(self) -> Generator[Entity]:
        # Returns a generator with footing entities
""".strip()

CHAT_RETRIEVAL_EXAMPLES = [
    {
        "role": "user",
        "content": "Get the ID of the object in front of me",
    },
    {
        "role": "assistant",
        "content": """
```python
# Get the object in front of the camera
front = l.front_object(distance=1000.0)
if front:
    result = front.get('id')
else:
    result = None
```
""".strip()
    },
#     {
#         "role": "user",
#         "content": "Find the IDs of all doors in the building",
#     },
#     {
#         "role": "assistant",
#         "content": """
# ```python
# # Get all door entities and extract their GUIDs
# doors = ifc.find_all_doors()
# result = [door.guid for door in doors]
# ```
# """.strip()
#     },
#     {
#         "role": "user",
#         "content": "Get the ID of the closest object to me",
#     },
#     {
#         "role": "assistant",
#         "content": """
# ```python
# # Get nearby objects ordered by distance (closest first)
# near = l.near_objects(radius=500.0)
# if near:
#     result = near[0].get('id')
# else:
#     result = None
# ```
# """.strip()
#     },
    {
        "role": "user",
        "content": "Find all window IDs",
    },
    {
        "role": "assistant",
        "content": """
```python
# Get all window entities and extract their GUIDs
windows = ifc.find_all_windows()
result = [window.guid for window in windows]
```
""".strip()
    },
#     {
#         "role": "user",
#         "content": "Get IDs of all objects I can see",
#     },
#     {
#         "role": "assistant",
#         "content": """
# ```python
# # Get all objects in the field of view
# visible = l.in_sight()
# result = [obj.get('id') for obj in visible]
# ```
# """.strip()
#     },
#     {
#         "role": "user",
#         "content": "Find the ID of the wall closest to me",
#     },
#     {
#         "role": "assistant",
#         "content": """
# ```python
# # Get all wall IDs
# walls = ifc.find_all_walls()
# wall_ids = [wall.guid for wall in walls]
# # Get nearby objects ordered by distance
# near = l.near_objects(radius=1000.0)
# near_ids = [obj.get('id') for obj in near]
# # Find first wall in the ordered list
# result = None
# for obj_id in near_ids:
#     if obj_id in wall_ids:
#         result = obj_id
#         break
# ```
# """.strip()
#     },
#     {
#         "role": "user",
#         "content": "Get the IDs of stairs within 300cm of me",
#     },
#     {
#         "role": "assistant",
#         "content": """
# ```python
# # Get all stair IDs
# stairs = ifc.find_all_stairs()
# stair_ids = [stair.guid for stair in stairs]
# # Get objects within 300cm radius
# near = l.near_objects(radius=300.0)
# # Filter for stairs only
# result = []
# for obj in near:
#     obj_id = obj.get('id')
#     if obj_id in stair_ids:
#         result.append(obj_id)
# ```
# """.strip()
#     },
    {
        "role": "user",
        "content": "Find the ID of the door to my left",
    },
    {
        "role": "assistant",
        "content": """
```python
# Get all door entities
doors = ifc.find_all_doors()
result = None
# Check each door to find one on the left
for door in doors:
    if l.is_entity_to_my_left(door.guid):
        result = door.guid
        break
```
""".strip()
    },
    {
        "role": "user",
        "content": "Get all beam IDs currently visible",
    },
    {
        "role": "assistant",
        "content": """
```python
# Get all beam IDs
beams = ifc.find_all_beams()
beam_ids = [beam.guid for beam in beams]
# Get visible objects
visible = l.in_sight()
visible_ids = [obj.get('id') for obj in visible]
# Filter beams that are visible
result = [beam_id for beam_id in beam_ids if beam_id in visible_ids]
```
""".strip()
    },
    {
        "role": "user",
        "content": "Find the ID of the nearest window",
    },
    {
        "role": "assistant",
        "content": """
```python
# Get all window IDs
windows = ifc.find_all_windows()
window_ids = [window.guid for window in windows]
# Get nearby objects ordered by distance
near = l.near_objects(radius=2000.0)
# Find first window in the ordered list
result = None
for obj in near:
    obj_id = obj.get('id')
    if obj_id in window_ids:
        result = obj_id
        break
```
""".strip()
    },
    {
        "role": "user",
        "content": "Get the IDs of all doors and windows",
    },
    {
        "role": "assistant",
        "content": """
```python
# Get all doors and windows
doors = ifc.find_all_doors()
windows = ifc.find_all_windows()
# Store in a dictionary by type
result = {
    "doors": [door.guid for door in doors],
    "windows": [window.guid for window in windows]
}
```
""".strip()
    }
#     {
#         "role": "user",
#         "content": "Find IDs of all walls, columns, and beams",
#     },
#     {
#         "role": "assistant",
#         "content": """
# ```python
# # Get all structural elements
# walls = ifc.find_all_walls()
# columns = ifc.find_all_columns()
# beams = ifc.find_all_beams()
# # Store in a dictionary by type
# result = {
#     "walls": [wall.guid for wall in walls],
#     "columns": [column.guid for column in columns],
#     "beams": [beam.guid for beam in beams]
# }
# ```
# """.strip()
#     },
#     {
#         "role": "user",
#         "content": "Get visible doors and windows",
#     },
#     {
#         "role": "assistant",
#         "content": """
# ```python
# # Get all doors and windows
# doors = ifc.find_all_doors()
# door_ids = [door.guid for door in doors]
# windows = ifc.find_all_windows()
# window_ids = [window.guid for window in windows]
# # Get visible objects
# visible = l.in_sight()
# visible_ids = [obj.get('id') for obj in visible]
# # Filter by visibility
# result = {
#     "doors": [door_id for door_id in door_ids if door_id in visible_ids],
#     "windows": [window_id for window_id in window_ids if window_id in visible_ids]
# }
# ```
# """.strip()
#     },
#     {
#         "role": "user",
#         "content": "Find the nearest door and nearest window",
#     },
#     {
#         "role": "assistant",
#         "content": """
# ```python
# # Get all doors and windows
# doors = ifc.find_all_doors()
# door_ids = [door.guid for door in doors]
# windows = ifc.find_all_windows()
# window_ids = [window.guid for window in windows]
# # Get nearby objects ordered by distance
# near = l.near_objects(radius=2000.0)
# # Find nearest of each type
# nearest_door = None
# nearest_window = None
# for obj in near:
#     obj_id = obj.get('id')
#     if nearest_door is None and obj_id in door_ids:
#         nearest_door = obj_id
#     if nearest_window is None and obj_id in window_ids:
#         nearest_window = obj_id
#     if nearest_door and nearest_window:
#         break
# # Store results
# result = {
#     "nearest_door": nearest_door,
#     "nearest_window": nearest_window
# }
# ```
# """.strip()
#     }
]