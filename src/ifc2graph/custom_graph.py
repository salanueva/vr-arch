import os

from datetime import datetime
import warnings
import math

import topologicpy
from topologicpy.Graph import Graph

# from src.ifc2graph.custom_topology import CustomTopology
from src.ifc2graph.bbox_helper import compute_dimensions, empty_dimensions



class CustomGraph(Graph):
    """
    CustomGraph is a subclass of the Graph class from the topologicpy library.
    It is used to create a graph object that can be used to store and manipulate IFC data.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    
    @staticmethod
    def ByIFCFile(file,
                  includeTypes: list = [],
                  excludeTypes: list = [],
                  includeRels: list = [],
                  excludeRels: list = [],
                  transferDictionaries: bool = False,
                  useInternalVertex: bool = False,
                  storeBREP: bool = False,
                  removeCoplanarFaces: bool = False,
                  xMin: float = -0.5, yMin: float = -0.5, zMin: float = -0.5,
                  xMax: float = 0.5, yMax: float = 0.5, zMax: float = 0.5,
                  tolerance: float = 0.0001):
        """
        Create a Graph from an IFC file. This code is partially based on code from Bruno Postle.

        Parameters
        ----------
        file : file
            The input IFC file
        includeTypes : list , optional
            A list of IFC object types to include in the graph. The default is [] which means all object types are included.
        excludeTypes : list , optional
            A list of IFC object types to exclude from the graph. The default is [] which mean no object type is excluded.
        includeRels : list , optional
            A list of IFC relationship types to include in the graph. The default is [] which means all relationship types are included.
        excludeRels : list , optional
            A list of IFC relationship types to exclude from the graph. The default is [] which mean no relationship type is excluded.
        transferDictionaries : bool , optional
            If set to True, the dictionaries from the IFC file will be transferred to the topology. Otherwise, they won't. The default is False.
        useInternalVertex : bool , optional
            If set to True, use an internal vertex to represent the subtopology. Otherwise, use its centroid. The default is False.
        storeBREP : bool , optional
            If set to True, store the BRep of the subtopology in its representative vertex. The default is False.
        removeCoplanarFaces : bool , optional
            If set to True, coplanar faces are removed. Otherwise they are not. The default is False.
        xMin : float, optional
            The desired minimum value to assign for a vertex's X coordinate. The default is -0.5.
        yMin : float, optional
            The desired minimum value to assign for a vertex's Y coordinate. The default is -0.5.
        zMin : float, optional
            The desired minimum value to assign for a vertex's Z coordinate. The default is -0.5.
        xMax : float, optional
            The desired maximum value to assign for a vertex's X coordinate. The default is 0.5.
        yMax : float, optional
            The desired maximum value to assign for a vertex's Y coordinate. The default is 0.5.
        zMax : float, optional
            The desired maximum value to assign for a vertex's Z coordinate. The default is 0.5.
        tolerance : float , optional
            The desired tolerance. The default is 0.0001.
        
        Returns
        -------
        topologic_core.Graph
            The created graph.
        
        """
        from topologicpy.Vertex import Vertex
        from topologicpy.Edge import Edge
        from topologicpy.Graph import Graph
        from topologicpy.Topology import Topology
        from topologicpy.Dictionary import Dictionary
        try:
            import ifcopenshell
            import ifcopenshell.util.placement
            import ifcopenshell.util.element
            import ifcopenshell.util.shape
            import ifcopenshell.geom
        except:
            print("Graph.ByIFCFile - Warning: Installing required ifcopenshell library.")
            try:
                os.system("pip install ifcopenshell")
            except:
                os.system("pip install ifcopenshell --user")
            try:
                import ifcopenshell
                import ifcopenshell.util.placement
                import ifcopenshell.util.element
                import ifcopenshell.util.shape
                import ifcopenshell.geom
                print("Graph.ByIFCFile - Warning: ifcopenshell library installed correctly.")
            except:
                warnings.warn("Graph.ByIFCFile - Error: Could not import ifcopenshell. Please try to install ifcopenshell manually. Returning None.")
                return None
        
        import random

        def vertexAtKeyValue(vertices, key, value):
            for v in vertices:
                d = Topology.Dictionary(v)
                d_value = Dictionary.ValueAtKey(d, key)
                if value == d_value:
                    return v
            return None

        def IFCObjects(ifc_file, include=[], exclude=[]):
            include = [s.lower() for s in include]
            exclude = [s.lower() for s in exclude]
            all_objects = ifc_file.by_type('IfcProduct')
            return_objects = []
            for obj in all_objects:
                is_a = obj.is_a().lower()
                if is_a in exclude:
                    continue
                if is_a in include or len(include) == 0:
                    return_objects.append(obj)
            return return_objects

        def IFCObjectTypes(ifc_file):
            products = IFCObjects(ifc_file)
            obj_types = []
            for product in products:
                obj_types.append(product.is_a())  
            obj_types = list(set(obj_types))
            obj_types.sort()
            return obj_types

        def IFCRelationshipTypes(ifc_file):
            rel_types = [ifc_rel.is_a() for ifc_rel in ifc_file.by_type("IfcRelationship")]
            rel_types = list(set(rel_types))
            rel_types.sort()
            return rel_types

        def IFCRelationships(ifc_file, include=[], exclude=[]):
            include = [s.lower() for s in include]
            exclude = [s.lower() for s in exclude]
            rel_types = [ifc_rel.is_a() for ifc_rel in ifc_file.by_type("IfcRelationship")]
            rel_types = list(set(rel_types))
            relationships = []
            for ifc_rel in ifc_file.by_type("IfcRelationship"):
                rel_type = ifc_rel.is_a().lower()
                if rel_type in exclude:
                    continue
                if rel_type in include or len(include) == 0:
                    relationships.append(ifc_rel)
            return relationships

        def get_psets(entity):
            # Initialize the PSET dictionary for this entity
            psets = {}
            
            # Check if the entity has a GlobalId
            if not hasattr(entity, 'GlobalId'):
                raise ValueError("The provided entity does not have a GlobalId.")
            
            # Get the property sets related to this entity
            for definition in entity.IsDefinedBy:
                if definition.is_a('IfcRelDefinesByProperties'):
                    property_set = definition.RelatingPropertyDefinition
                    
                    # Check if it is a property set
                    if not property_set == None:
                        if property_set.is_a('IfcPropertySet'):
                            pset_name = "IFC_"+property_set.Name
                            
                            # Dictionary to hold individual properties
                            properties = {}
                            
                            # Iterate over the properties in the PSET
                            for prop in property_set.HasProperties:
                                if prop.is_a('IfcPropertySingleValue'):
                                    # Get the property name and value
                                    prop_name = "IFC_"+prop.Name
                                    prop_value = prop.NominalValue.wrappedValue if prop.NominalValue else None
                                    properties[prop_name] = prop_value
                            
                            # Add this PSET to the dictionary for this entity
                            psets[pset_name] = properties
            return psets
        
        def get_color_transparency_material(entity):
            import random

            # Set default Material Name and ID
            material_list = []
            # Set default transparency based on entity type or material
            default_transparency = 0.0
            
            # Check if the entity is an opening or made of glass
            is_a = entity.is_a().lower()
            if "opening" in is_a or "window" in is_a or "door" in is_a or "space" in is_a:
                default_transparency = 0.7
            elif "space" in is_a:
                default_transparency = 0.8
            
            # Check if the entity has constituent materials (e.g., glass)
            else:
                # Check for associated materials (ConstituentMaterial or direct material assignment)
                materials_checked = False
                if hasattr(entity, 'HasAssociations'):
                    for rel in entity.HasAssociations:
                        if rel.is_a('IfcRelAssociatesMaterial'):
                            material = rel.RelatingMaterial
                            if material.is_a('IfcMaterial') and 'glass' in material.Name.lower():
                                default_transparency = 0.5
                                materials_checked = True
                            elif material.is_a('IfcMaterialLayerSetUsage'):
                                material_layers = material.ForLayerSet.MaterialLayers
                                for layer in material_layers:
                                    material_list.append(layer.Material.Name)
                                    if 'glass' in layer.Material.Name.lower():
                                        default_transparency = 0.5
                                        materials_checked = True
                                        
                # Check for ConstituentMaterial if available
                if hasattr(entity, 'HasAssociations') and not materials_checked:
                    for rel in entity.HasAssociations:
                        if rel.is_a('IfcRelAssociatesMaterial'):
                            material = rel.RelatingMaterial
                            if material.is_a('IfcMaterialConstituentSet'):
                                for constituent in material.MaterialConstituents:
                                    material_list.append(constituent.Material.Name)
                                    if 'glass' in constituent.Material.Name.lower():
                                        default_transparency = 0.5
                                        materials_checked = True

                # Check if the entity has ShapeAspects with associated materials or styles
                if hasattr(entity, 'HasShapeAspects') and not materials_checked:
                    for shape_aspect in entity.HasShapeAspects:
                        if hasattr(shape_aspect, 'StyledByItem') and shape_aspect.StyledByItem:
                            for styled_item in shape_aspect.StyledByItem:
                                for style in styled_item.Styles:
                                    if style.is_a('IfcSurfaceStyle'):
                                        for surface_style in style.Styles:
                                            if surface_style.is_a('IfcSurfaceStyleRendering'):
                                                transparency = getattr(surface_style, 'Transparency', default_transparency)
                                                if transparency > 0:
                                                    default_transparency = transparency

            # Try to get the actual color and transparency if defined
            if hasattr(entity, 'Representation') and entity.Representation:
                for rep in entity.Representation.Representations:
                    for item in rep.Items:
                        if hasattr(item, 'StyledByItem') and item.StyledByItem:
                            for styled_item in item.StyledByItem:
                                if hasattr(styled_item, 'Styles'):
                                    for style in styled_item.Styles:
                                        if style.is_a('IfcSurfaceStyle'):
                                            for surface_style in style.Styles:
                                                if surface_style.is_a('IfcSurfaceStyleRendering'):
                                                    color = surface_style.SurfaceColour
                                                    transparency = getattr(surface_style, 'Transparency', default_transparency)
                                                    return (color.Red*255, color.Green*255, color.Blue*255), transparency, material_list
            
            # If no color is defined, return a consistent random color based on the entity type
            if "wall" in is_a:
                color = (175, 175, 175)
            elif "slab" in is_a:
                color = (200, 200, 200)
            elif "space" in is_a:
                color = (250, 250, 250)
            else:
                random.seed(hash(is_a))
                color = (random.random(), random.random(), random.random())
            
            return color, default_transparency, material_list

        def vertexByIFCObject(ifc_object, object_types, restrict=False, prev_vertices=None, ndo_info=None):
            settings = ifcopenshell.geom.settings()
            settings.set(settings.USE_WORLD_COORDS,True)
            try:
                shape = ifcopenshell.geom.create_shape(settings, ifc_object)
            except:
                shape = None
            if shape or restrict == False: #Only add vertices of entities that have 3D geometries.
                obj_id = ifc_object.id()
                psets = ifcopenshell.util.element.get_psets(ifc_object)
                obj_type = ifc_object.is_a()
                obj_type_id = object_types.index(obj_type)
                name = "Untitled"
                LongName = "Untitled"
                try:
                    name = ifc_object.Name
                except:
                    name = "Untitled"
                try:
                    LongName = ifc_object.LongName
                except:
                    LongName = name

                if name == None:
                    name = "Untitled"
                if LongName == None:
                    LongName = "Untitled"
                label = str(obj_id)+" "+LongName+" ("+obj_type+" "+str(obj_type_id)+")"
                
                random.seed(datetime.now().timestamp())
                is_ndo = False
                if label not in ndo_info["ndo"]:
                    grouped_verts = ifcopenshell.util.shape.get_vertices(shape.geometry)
                    vertices = [Vertex.ByCoordinates(list(coords)) for coords in grouped_verts]
                    centroid = Vertex.Centroid(vertices)
                    bbox_info = compute_dimensions(vertices)
                else:
                    row, column, depth = -1, -1, -1
                    idx = ndo_info['ndo'].index(label)
                    aux_up, aux_prev = 0, 0
                    for i in range(ndo_info['ndo_count_first_row'], 0, -1):
                        aux_prev = aux_up
                        aux_up += i
                        if idx < aux_up:
                            row = ndo_info['ndo_count_first_row'] - i
                            column = idx - aux_prev
                            depth = row + column
                            break
                    x = ndo_info['xMin'] + (row * ndo_info['ndo_distance'])
                    y = ndo_info['yMin'] + (column * ndo_info['ndo_distance'])
                    z = ndo_info['zMin'] + (depth * ndo_info['ndo_distance'])
                    # print(row, column, depth, " - ", x, y, z, "NDO centroid coordinates")
                    centroid = Vertex.ByCoordinates(x, y, z)
                    bbox_info = {}
                    is_ndo = True
                
                # Avoid overlapping vertices
                centroid_offset = [0.0, 0.0, 0.0]
                new_centroid = Vertex.ByCoordinates(centroid.X(), centroid.Y(), centroid.Z())
                found_vert = False
                value = ndo_info['ndo_distance']
                for vert in prev_vertices:
                    while Vertex.Distance(vert, new_centroid, mantissa=6) < value - 1e-6:
                        # print(vert, new_centroid, "is too close. Adding random offset.")
                        # If the vertex already exists, add random offset to the centroid
                        centroid_offset = [centroid_offset[0] + random.uniform(value, value), centroid_offset[1] + random.uniform(-value, value), centroid_offset[2] + random.uniform(-value, value)]
                        # print(centroid_offset)
                        new_centroid = Vertex.ByCoordinates(centroid.X() + centroid_offset[0], centroid.Y() + centroid_offset[1], centroid.Z() + centroid_offset[2])
                        # print(centroid.X(), centroid.Y(), centroid.Z())
                        # print(new_centroid.X(), new_centroid.Y(), new_centroid.Z())
                    if Vertex.Distance(centroid, new_centroid, mantissa=6) > value:
                        found_vert = True
                        break

                if found_vert:
                    centroid = Vertex.ByCoordinates(new_centroid.X(), new_centroid.Y(), new_centroid.Z())
                
                # Store relevant information
                if transferDictionaries == True:
                    color, transparency, material_list = get_color_transparency_material(ifc_object)
                    if color == None:
                        color = "white"
                    if transparency == None:
                        transparency = 0
                    # if "GlobalId" not in ifc_object:
                        # print("Graph.ByIFCFile - Warning: The IFC object", ifc_object, "of type", ifc_object.is_a(), "does not have a GlobalId. Using 0 instead.")
                    entity_dict = {
                        # "name":getattr(ifc_object, 'Name', label) if getattr(ifc_object, 'Name', label) is not None else label, # "TOPOLOGIC_name": getattr(ifc_object, 'Name', "Untitled"),
                        # "color": color, # "TOPOLOGIC_color": color,
                        # "opacity": 1.0 - transparency, # "TOPOLOGIC_opacity": 1.0 - transparency,
                        "is_non_dimensional": str(bool(is_ndo)),
                        "bbox_dimensions": bbox_info,
                        "IFC_name": getattr(ifc_object, 'Name', label) if getattr(ifc_object, 'Name', label) is not None else label, # "TOPOLOGIC_name": getattr(ifc_object, 'Name', "Untitled")
                        "IFC_global_id": getattr(ifc_object, 'GlobalId', 0),
                        "IFC_type": ifc_object.is_a(),
                        "IFC_material_list": material_list,
                        "TOPOLOGIC_id": str(UUID(centroid, ifc_global_id_str=getattr(ifc_object, 'GlobalId', 0))),
                        "TOPOLOGIC_name": getattr(ifc_object, 'Name', "Untitled"),
                        "TOPOLOGIC_color": color,
                        "TOPOLOGIC_type": Topology.TypeAsString(centroid),
                        "TOPOLOGIC_opacity": 1.0 - transparency,
                        "CUSTOM_offset": centroid_offset,
                    }
                    # if bbox_info == {}:
                    #    del entity_dict["CUSTOM_dimensions"]
                    # if sum(centroid_offset) <= 1e-6:
                    #     del entity_dict["CUSTOM_offset"]
                    topology_dict = Dictionary.ByPythonDictionary(entity_dict)
                    # Get PSETs dictionary
                    pset_python_dict = get_psets(ifc_object)
                    pset_dict = Dictionary.ByPythonDictionary(pset_python_dict)
                    topology_dict = Dictionary.ByMergedDictionaries([topology_dict, pset_dict])
                    if storeBREP == True or useInternalVertex == True:
                        shape_topology = None
                        if hasattr(ifc_object, "Representation") and ifc_object.Representation:
                            for rep in ifc_object.Representation.Representations:
                                if rep.is_a("IfcShapeRepresentation"):
                                    try:
                                        # Generate the geometry for this entity
                                        shape = ifcopenshell.geom.create_shape(settings, ifc_object)
                                        # Get grouped vertices and grouped faces     
                                        grouped_verts = shape.geometry.verts
                                        verts = [ [grouped_verts[i], grouped_verts[i + 1], grouped_verts[i + 2]] for i in range(0, len(grouped_verts), 3)]
                                        grouped_edges = shape.geometry.edges
                                        edges = [[grouped_edges[i], grouped_edges[i + 1]] for i in range(0, len(grouped_edges), 2)]
                                        grouped_faces = shape.geometry.faces
                                        faces = [ [grouped_faces[i], grouped_faces[i + 1], grouped_faces[i + 2]] for i in range(0, len(grouped_faces), 3)]
                                        shape_topology = Topology.ByGeometry(verts, edges, faces, silent=True)
                                        if not shape_topology == None:
                                            if removeCoplanarFaces == True:
                                                shape_topology = Topology.RemoveCoplanarFaces(shape_topology, epsilon=0.0001)
                                    except:
                                        pass
                        # print(f"# IFC Object: {ifc_object.GlobalId} - {ifc_object.Name} - {ifc_object.is_a()}")
                        if not shape_topology == None and storeBREP:
                            topology_dict = Dictionary.SetValuesAtKeys(topology_dict, ["brep", "brepType", "brepTypeString"], [Topology.BREPString(shape_topology), Topology.Type(shape_topology), Topology.TypeAsString(shape_topology)])
                        if not shape_topology == None and useInternalVertex == True:
                            centroid = Topology.InternalVertex(shape_topology)
                    centroid = Topology.SetDictionary(centroid, topology_dict)
                return centroid
            return None

        def edgesByIFCRelationships(ifc_relationships, ifc_types, vertices):
            tuples = []
            edges = []

            for ifc_rel in ifc_relationships:
                source = None
                destinations = []
                if ifc_rel.is_a("IfcRelConnectsPorts"):
                    source = ifc_rel.RelatingPort
                    destinations = ifc_rel.RelatedPorts
                elif ifc_rel.is_a("IfcRelConnectsPortToElement"):
                    source = ifc_rel.RelatingPort
                    destinations = [ifc_rel.RelatedElement]
                elif ifc_rel.is_a("IfcRelAggregates"):
                    source = ifc_rel.RelatingObject
                    destinations = ifc_rel.RelatedObjects
                elif ifc_rel.is_a("IfcRelNests"):
                    source = ifc_rel.RelatingObject
                    destinations = ifc_rel.RelatedObjects
                elif ifc_rel.is_a("IfcRelAssignsToGroup"):
                    source = ifc_rel.RelatingGroup
                    destinations = ifc_rel.RelatedObjects
                elif ifc_rel.is_a("IfcRelConnectsPathElements"):
                    source = ifc_rel.RelatingElement
                    destinations = [ifc_rel.RelatedElement]
                elif ifc_rel.is_a("IfcRelConnectsStructuralMember"):
                    source = ifc_rel.RelatingStructuralMember
                    destinations = [ifc_rel.RelatedStructuralConnection]
                elif ifc_rel.is_a("IfcRelContainedInSpatialStructure"):
                    source = ifc_rel.RelatingStructure
                    destinations = ifc_rel.RelatedElements
                elif ifc_rel.is_a("IfcRelFillsElement"):
                    source = ifc_rel.RelatingOpeningElement
                    destinations = [ifc_rel.RelatedBuildingElement]
                elif ifc_rel.is_a("IfcRelSpaceBoundary"):
                    source = ifc_rel.RelatingSpace
                    destinations = [ifc_rel.RelatedBuildingElement]
                elif ifc_rel.is_a("IfcRelVoidsElement"):
                    source = ifc_rel.RelatingBuildingElement
                    destinations = [ifc_rel.RelatedOpeningElement]
                elif ifc_rel.is_a("IfcRelDefinesByProperties") or ifc_rel.is_a("IfcRelAssociatesMaterial") or ifc_rel.is_a("IfcRelDefinesByType"):
                    source = None
                    destinations = None
                else:
                    print("Graph.ByIFCFile - Warning: The relationship", ifc_rel, "is not supported. Skipping.")
                if source:
                    sv = vertexAtKeyValue(vertices, key="IFC_global_id", value=getattr(source, 'GlobalId', 0))
                    if sv:
                        si = Vertex.Index(sv, vertices, tolerance=tolerance)
                        if not si == None:
                            for destination in destinations:
                                if destination == None:
                                    continue
                                ev = vertexAtKeyValue(vertices, key="IFC_global_id", value=getattr(destination, 'GlobalId', 0),)
                                if ev:
                                    ei = Vertex.Index(ev, vertices, tolerance=tolerance)
                                    if not ei == None:
                                        if not([si,ei] in tuples or [ei,si] in tuples):
                                            tuples.append([si,ei])
                                            e = Edge.ByVertices([sv,ev])
                                            d = Dictionary.ByKeysValues(["IFC_global_id", "IFC_name", "IFC_type"], [ifc_rel.id(), ifc_rel.Name, ifc_rel.is_a()])
                                            e = Topology.SetDictionary(e, d)
                                            edges.append(e)
            return edges
        
        def compute_bbox_for_non_dimensional_objects(ifc_objects, ifc_types):

            settings = ifcopenshell.geom.settings()
            settings.set(settings.USE_WORLD_COORDS,True)

            centroids = []
            non_dimensional_objects = []
            for ifc_object in ifc_objects:
                try:
                    shape = ifcopenshell.geom.create_shape(settings, ifc_object)
                    grouped_verts = ifcopenshell.util.shape.get_vertices(shape.geometry)
                    vertices = [Vertex.ByCoordinates(list(coords)) for coords in grouped_verts]
                    centroids.append(Vertex.Centroid(vertices))
                except Exception as e:
                    obj_id = ifc_object.id()
                    psets = ifcopenshell.util.element.get_psets(ifc_object)
                    obj_type = ifc_object.is_a()
                    obj_type_id = ifc_types.index(obj_type)
                    name = "Untitled"
                    LongName = "Untitled"
                    try:
                        name = ifc_object.Name
                    except:
                        name = "Untitled"
                    try:
                        LongName = ifc_object.LongName
                    except:
                        LongName = name

                    if name == None:
                        name = "Untitled"
                    if LongName == None:
                        LongName = "Untitled"
                    label = str(obj_id)+" "+LongName+" ("+obj_type+" "+str(obj_type_id)+")"
                    
                    non_dimensional_objects.append(label)

            # print(len(centroids), "dimensional objects found.")
            # print(len(non_dimensional_objects), "non-dimensional objects found.")
            # print("NDOs: ", non_dimensional_objects)
            # non_dimensional_object_count
            ndo_count = len(non_dimensional_objects)
            inter_ndo_distance = 0.2
            if ndo_count == 0:
                return {
                    "xMin": xMin,
                    "xMax": xMax,
                    "yMin": yMin,
                    "yMax": yMax,
                    "zMin": zMin,
                    "zMax": zMax,
                    "ndo": non_dimensional_objects,
                    "ndo_count": ndo_count,
                    "ndo_count_first_row": 0,
                    "ndo_distance": inter_ndo_distance
                }
            
            x_coords = [c.X() for c in centroids]
            y_coords = [c.Y() for c in centroids]
            z_coords = [c.Z() for c in centroids]

            # Second grade equation to compute the bounding box for non-dimensional objects
            a, b, c = 1, 1, -ndo_count*2
            # print(a, b, c)
            discriminant = b**2 - 4*a*c
            sqrt_discriminant = math.sqrt(discriminant)
            ndo_count_first_row = math.ceil((-b + sqrt_discriminant) / (2*a))

            ndo_x_max, ndo_y_max, ndo_z_max = min(x_coords) - 0.5, min(y_coords) - 0.5, min(z_coords) - 0.5
            ndo_x_min, ndo_y_min, ndo_z_min = ndo_x_max - ((ndo_count_first_row - 1) * inter_ndo_distance), ndo_y_max - ((ndo_count_first_row - 1) * inter_ndo_distance), ndo_z_max - ((ndo_count_first_row - 1) * inter_ndo_distance)

            return {
                "xMin": ndo_x_min,
                "xMax": ndo_x_max,
                "yMin": ndo_y_min,
                "yMax": ndo_y_max,
                "zMin": ndo_z_min,
                "zMax": ndo_z_max,
                "ndo": non_dimensional_objects,
                "ndo_count": ndo_count,
                "ndo_count_first_row": ndo_count_first_row,
                "ndo_distance": inter_ndo_distance
            }
        
        ifc_types = IFCObjectTypes(file)
        ifc_objects = IFCObjects(file, include=includeTypes, exclude=excludeTypes)

        ndo_info = compute_bbox_for_non_dimensional_objects(ifc_objects, ifc_types)  # This is just to ensure the dimensions are computed, but not used here.

        vertices = []
        # print("BEFORE")
        for ifc_object in ifc_objects:
            v = vertexByIFCObject(ifc_object, ifc_types, prev_vertices=vertices, ndo_info=ndo_info)
            elem = topologicpy.Dictionary.Dictionary.PythonDictionary(Topology.Dictionary(v))
            # if elem['IFC_type'] == "IfcOpeningElement":
            # print(f"{elem['IFC_type'].ljust(24, ' ')}{elem['TOPOLOGIC_id'].ljust(32, ' ')} {v.X():2.6f},{v.Y():2.6f},{v.Z():2.6f}")
            # print(elem['IFC_type'], Topology.Geometry(v, mantissa=6)['vertices'][0])
            if v:
                vertices.append(v)
        # print("AFTER")
        # print(len(vertices), "vertices created from", len(ifc_objects), "IFC objects.")
        # for v in vertices:
        #    print(Topology.Geometry(v, mantissa=6))
        if len(vertices) > 0:
            ifc_relationships = IFCRelationships(file, include=includeRels, exclude=excludeRels)
            edges = edgesByIFCRelationships(ifc_relationships, ifc_types, vertices)
            g = Graph.ByVerticesEdges(vertices, edges)
        else:
            g = None
        return g

    @staticmethod
    def ByIFCPath(path,
                  includeTypes=[],
                  excludeTypes=[],
                  includeRels=[],
                  excludeRels=[],
                  transferDictionaries=False,
                  useInternalVertex=False,
                  storeBREP=False,
                  removeCoplanarFaces=False,
                  xMin=-0.5, yMin=-0.5, zMin=-0.5, xMax=0.5, yMax=0.5, zMax=0.5):
        """
        Create a Graph from an IFC path. This code is partially based on code from Bruno Postle.

        Parameters
        ----------
        path : str
            The input IFC file path.
        includeTypes : list , optional
            A list of IFC object types to include in the graph. The default is [] which means all object types are included.
        excludeTypes : list , optional
            A list of IFC object types to exclude from the graph. The default is [] which mean no object type is excluded.
        includeRels : list , optional
            A list of IFC relationship types to include in the graph. The default is [] which means all relationship types are included.
        excludeRels : list , optional
            A list of IFC relationship types to exclude from the graph. The default is [] which mean no relationship type is excluded.
        transferDictionaries : bool , optional
            If set to True, the dictionaries from the IFC file will be transferred to the topology. Otherwise, they won't. The default is False.
        useInternalVertex : bool , optional
            If set to True, use an internal vertex to represent the subtopology. Otherwise, use its centroid. The default is False.
        storeBREP : bool , optional
            If set to True, store the BRep of the subtopology in its representative vertex. The default is False.
        removeCoplanarFaces : bool , optional
            If set to True, coplanar faces are removed. Otherwise they are not. The default is False.
        xMin : float, optional
            The desired minimum value to assign for a vertex's X coordinate. The default is -0.5.
        yMin : float, optional
            The desired minimum value to assign for a vertex's Y coordinate. The default is -0.5.
        zMin : float, optional
            The desired minimum value to assign for a vertex's Z coordinate. The default is -0.5.
        xMax : float, optional
            The desired maximum value to assign for a vertex's X coordinate. The default is 0.5.
        yMax : float, optional
            The desired maximum value to assign for a vertex's Y coordinate. The default is 0.5.
        zMax : float, optional
            The desired maximum value to assign for a vertex's Z coordinate. The default is 0.5.
        
        Returns
        -------
        topologic_core.Graph
            The created graph.
        
        """
        try:
            import ifcopenshell
            import ifcopenshell.util.placement
            import ifcopenshell.util.element
            import ifcopenshell.util.shape
            import ifcopenshell.geom
        except:
            print("Graph.ByIFCPath - Warning: Installing required ifcopenshell library.")
            try:
                os.system("pip install ifcopenshell")
            except:
                os.system("pip install ifcopenshell --user")
            try:
                import ifcopenshell
                import ifcopenshell.util.placement
                import ifcopenshell.util.element
                import ifcopenshell.util.shape
                import ifcopenshell.geom
                print("Graph.ByIFCPath - Warning: ifcopenshell library installed correctly.")
            except:
                warnings.warn("Graph.ByIFCPath - Error: Could not import ifcopenshell. Please try to install ifcopenshell manually. Returning None.")
                return None
        if not path:
            print("Graph.ByIFCPath - Error: the input path is not a valid path. Returning None.")
            return None
        ifc_file = ifcopenshell.open(path)
        if not ifc_file:
            print("Graph.ByIFCPath - Error: Could not open the IFC file. Returning None.")
            return None
        return CustomGraph.ByIFCFile(ifc_file,
                               includeTypes=includeTypes,
                               excludeTypes=excludeTypes,
                               includeRels=includeRels,
                               excludeRels=excludeRels,
                               transferDictionaries=transferDictionaries,
                               useInternalVertex=useInternalVertex,
                               storeBREP=storeBREP,
                               removeCoplanarFaces=removeCoplanarFaces,
                               xMin=xMin, yMin=yMin, zMin=zMin, xMax=xMax, yMax=yMax, zMax=zMax)



def UUID(topology, namespace="topologicpy", ifc_global_id_str=""):
    """
    Generate a UUID v5 based on the provided content and a fixed namespace.
    
    Parameters
    ----------
    topology : topologic_core.Topology
        The input topology
    namespace : str , optional
        The base namescape to use for generating the UUID

    Returns
    -------
    UUID
        The uuid of the input topology.

    """
    import uuid
    from topologicpy.Topology import Topology
    from topologicpy.Dictionary import Dictionary

    predefined_namespace_dns = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
    namespace_uuid = uuid.uuid5(predefined_namespace_dns, namespace)
    cellComplexes = Topology.CellComplexes(topology)
    cells = Topology.Cells(topology)
    shells = Topology.Shells(topology)
    faces = Topology.Faces(topology)
    wires = Topology.Wires(topology)
    edges = Topology.Edges(topology)
    vertices = Topology.Vertices(topology)
    apertures = Topology.Apertures(topology, subTopologyType="all")
    subTopologies = cellComplexes+cells+shells+faces+wires+edges+vertices+apertures
    dictionaries = [Dictionary.PythonDictionary(Topology.Dictionary(topology))]
    dictionaries += [Dictionary.PythonDictionary(Topology.Dictionary(s)) for s in subTopologies]
    dict_str = str(dictionaries)
    top_geom = Topology.Geometry(topology, mantissa=6)
    verts_str = str(top_geom['vertices'])
    edges_str = str(top_geom['edges'])
    faces_str = str(top_geom['faces'])
    geo_str = verts_str+edges_str+faces_str
    final_str = geo_str+dict_str+ifc_global_id_str
    uuid_str = uuid.uuid5(namespace_uuid, final_str)
    return str(uuid_str)