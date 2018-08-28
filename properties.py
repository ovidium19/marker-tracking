import bpy
from bpy.props import FloatVectorProperty
####################################
# Properties
class TrackingProperties(bpy.types.PropertyGroup):
    #not used
    f_limit = bpy.props.IntProperty(
                    name="Frame limit",
                    description="Frame limit modal",
                    default = 5,
                    min=0,
                    max=100
    )
    #not used
    sz = bpy.props.IntProperty(
        name="size_step",
        description="Step size to increase",
        default=10,
        min=1,
        max=25
    )
    #not used
    timer_time = bpy.props.FloatProperty(
        name="Timer",
        description="How much time in between updates",
        default=0.5,
        min=0.1,
        max=2
    )
    #holds the path to the current frame being processed
    dir = bpy.props.StringProperty(
        name="filepath",
        description="Where temp file is",
        default=""
    )
    #If your markers move very little from frame to frame, specify a low value here.
    #Measured in pixels
    max_dist = bpy.props.FloatProperty(
        name="max_dist",
        description="Maximum distance between two frames that a marker can move(in pixels). If this is set too high, markers can override each other, set appropriately",
        default=40
    )
    #Ignore a certain part of the image on the Y axis. Good for avoiding watermarks
    ignore_height = bpy.props.FloatProperty(
        name="ignore_height",
        description="Y axis height to ignore when choosing markers..good to use if you have a date watermark on the footage",
        default = 0
    )
    #This should pretty much never be changed. Slows down the process if increased.
    time_step = bpy.props.FloatProperty(
        name="time_step",
        description="How much time in between frames. The bigger, the more frames you see in between updates",
        default=0.1
    )
    #On what layer to add empties.
    layer_empties = bpy.props.IntProperty(
        name="Layer",
        description="Layer to place empties on",
        default=1,
        min=1,
        max=20
    )

class ColorProperty(bpy.types.PropertyGroup):
    #Color to be marked
    color = FloatVectorProperty(name="color",
                                subtype="COLOR_GAMMA",
                                default=[1.0, 1.0, 1.0, 1.0],
                                size=4,
                                min=0.0,
                                max=1.0)
    #How many grouped pixels should form a cluster to be marked. If increased, you will find less markers. If decreased, you will find more markers.
    thresh = bpy.props.IntProperty(
        name="threshold for marker",
        description="Minimum nr of pixels that form a coloured cluster",
        default=25,
        min=1,
        max=50
    )
    #Pattern Size of the new markers.
    pattern_size = bpy.props.FloatProperty(
        name="Pattern box size",
        default= 11,
        min=3,
        max = 20
    )

    #Search size of the new markers.
    search_size = bpy.props.FloatProperty(
        name="Search box size",
        default = 61,
        min = 20,
        max = 80
    )
####################################

def register():
    bpy.utils.register_class(TrackingProperties)
    bpy.utils.register_class(ColorProperty)
    bpy.types.MovieClip.track_color = bpy.props.PointerProperty(type=ColorProperty)
    bpy.types.WindowManager.op_props = bpy.props.PointerProperty(type=TrackingProperties)
    #Path where the converted image sequence will be saved.
    bpy.types.MovieClip.convert_path = bpy.props.StringProperty(
        name="Convert_Path",
        description="Where to save image sequence",
        default="",
        subtype="FILE_PATH"
    )

    bpy.types.MovieClip.current_path = bpy.props.StringProperty(
        default="",
        subtype="FILE_PATH"
    )

def unregister():
    del bpy.types.MovieClip.track_color
    del bpy.types.WindowManager.op_props
    del bpy.types.MovieClip.convert_path
    del bpy.types.MovieClip.current_path
    bpy.utils.unregister_class(ColorProperty)
    bpy.utils.unregister_class(TrackingProperties)
