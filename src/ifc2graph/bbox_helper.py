from compas.geometry import oriented_bounding_box_numpy, length_vector, subtract_vectors
import numpy as np
from topologicpy.Vertex import Vertex


def boundingBox(vertices, mantissa=6):
    
    x = []
    y = []
    z = []
    
    for aVertex in vertices:
        x.append(Vertex.X(aVertex, mantissa=mantissa))
        y.append(Vertex.Y(aVertex, mantissa=mantissa))
        z.append(Vertex.Z(aVertex, mantissa=mantissa))
    
    return ([min(x), min(y), min(z), max(x), max(y), max(z)])

def width_height_depth(bbox):
    """
    Returns the width, depth and height of a bounding box.
    """
    a = bbox[3] - bbox[0]
    b = bbox[4] - bbox[1]
    height = bbox[5] - bbox[2]

    if a >= b:
        width = round(a, 4)
        depth = round(b, 4)
        dim_order = "wdh"
    else:
        width = round(b, 4)
        depth = round(a, 4)
        dim_order = "dwh"
    height = round(height, 4)
                
    return {
        "bbox_width": width,
        "bbox_height": height, 
        "bbox_depth": depth,
        "bbox_volume": round(width * height * depth, 4)
    }, dim_order

def orientedBoundingBox(vertices, mantissa=6):
    
    x = []
    y = []
    z = []
    
    for aVertex in vertices:
        x.append(Vertex.X(aVertex, mantissa=mantissa))
        y.append(Vertex.Y(aVertex, mantissa=mantissa))
        z.append(Vertex.Z(aVertex, mantissa=mantissa))
    
    points = np.array([x, y, z]).T

    return oriented_bounding_box_numpy(points=points)



def oriented_width_height_depth(oriented_bbox, dim_order="whd"):
    """
    Returns the width, height and depth of a bounding box.
    """
    a_vec = subtract_vectors(oriented_bbox[1], oriented_bbox[0])
    b_vec = subtract_vectors(oriented_bbox[3], oriented_bbox[0])
    height = length_vector(subtract_vectors(oriented_bbox[4], oriented_bbox[0])) # this is height

    distances = [
        length_vector(a_vec),
        length_vector(b_vec),
        # length_vector(c_vec)
    ]
    distances.sort(reverse=True)
    """
    if dim_order == "whd":
        width, height, depth = distances
    elif dim_order == "wdh":
        width, depth, height = distances
    elif dim_order == "hwd":
        height, width, depth = distances
    elif dim_order == "hdw":
        height, depth, width = distances
    elif dim_order == "dwh":
        depth, width, height = distances
    elif dim_order == "dhw":
        depth, height, width = distances
    """
    if dim_order == "wdh":
        width, depth = distances
    elif dim_order == "dwh":
        depth, width = distances
    
    width = round(width, 4)
    height = round(height, 4)
    depth = round(depth, 4)
            
    return {
        "oriented_bbox_width": width,
        "oriented_bbox_height": height, 
        "oriented_bbox_depth": depth,
        "oriented_bbox_volume": round(width * height * depth, 4)
    }

def empty_dimensions():
    """
    Returns an empty dictionary with dimensions.
    """
    return {
        "bbox_width": 0,
        "bbox_height": 0,
        "bbox_depth": 0,
        "bbox_volume": 0,
        "oriented_bbox_width": 0,
        "oriented_bbox_height": 0, 
        "oriented_bbox_depth": 0,
        "oriented_bbox_volume": 0
    }


def compute_dimensions(vertices, mantissa=6):
    """
    Computes the dimensions of a bounding box and an oriented bounding box.
    """
    bbox = boundingBox(vertices, mantissa=mantissa)
    oriented_bbox = orientedBoundingBox(vertices, mantissa=mantissa)
    
    bbox_dimensions, dim_order = width_height_depth(bbox)
    oriented_bbox_dimensions = oriented_width_height_depth(oriented_bbox, dim_order=dim_order)
    
    return {
        # "bbox": bbox,
        # "oriented_bbox": oriented_bbox,
        **bbox_dimensions,
        # **oriented_bbox_dimensions # Commented out to avoid duplicate values
    }