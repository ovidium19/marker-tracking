#Main file of the addon. This file links all the other modules together and tells blender to register all the panels and operators described.

bl_info = {
    #This info shows up in the Addon Preferences tab in Blender
    "name": "Marker Tracker",
    "author": "Ovidiu Mitroi",
    "version": (1,0,0),
    "blender": (2, 79, 0),
    "location": "View3D > Tools",
    "description": "Tools for animating a 3D model with triangulation",
    "warning": "Depended on numpy and scipy",
    "wiki_url": "",
    "category": "Motion Tracking"
}

if "bpy" in locals():
    #If you are in Blender and have made a change to this addon and want to upload the change, you can simply
    #refresh the addon by hitting F8 and the changes will be uploaded.
    #This is achieved by reloading the packages
    #Any change to this file (__init__.py) will not be uploaded, in that case you have to reinstall the addon.
    import importlib

    empties_to_bones = importlib.reload(empties_to_bones)
    properties = importlib.reload(properties)
    sequence_converter = importlib.reload(sequence_converter)
    marker_tracker = importlib.reload(marker_tracker)
    Triangulate = importlib.reload(Triangulate)
    print("Reloaded")

else:
    #This executes when the addon is first activated

    from . import empties_to_bones
    from . import properties
    from . import sequence_converter
    from . import marker_tracker
    from . import Triangulate

    print("Imported")

#import all the modules from other modules that have to be registered with Blender
import bpy
from bpy.props import *
from .empties_to_bones import (
    CLIP_PT_EmptiesPoseBones,
    VIEW_3D_OT_PoseBones
)
from .sequence_converter import (
    CLIP_OT_ToSequence,
    ConvertModalOperator,
    ConvertPanel
)
from .Triangulate import (
    VIEW_3D_PT_triangulate,
    MESH_OT_triangulate
)
from .marker_tracker import (
    CLIP_OT_moveMarkers,
    CLIP_OT_colortrack,
    CLIP_OT_assignMarkersOnColor,
    TrackMarkersModalOperator,
    TrackPanel,
    CLIP_PT_color
)

classes = (
    CLIP_PT_EmptiesPoseBones,
    VIEW_3D_OT_PoseBones,
    CLIP_OT_ToSequence,
    ConvertModalOperator,
    ConvertPanel,
    MESH_OT_triangulate,
    VIEW_3D_PT_triangulate,
    CLIP_OT_moveMarkers,
    CLIP_OT_colortrack,
    CLIP_OT_assignMarkersOnColor,
    TrackMarkersModalOperator,
    TrackPanel,
    CLIP_PT_color
)

def register():
    #Register all properties and classes imported within this function
    properties.register()
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    properties.unregister()
    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__=='__main__':
    register()