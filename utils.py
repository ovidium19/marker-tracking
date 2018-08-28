import bpy
import bgl
import blf
from math import sqrt, pow
import time

def time_it(f):
    '''
    A Decorator function used to time your other functions.
    Simply put @time_it on top of any function and you will get a print statement on the console with how long it took to execute the function.

    :param f: Function to be timed
    :return: Result of function f, with a print statement that specifies how long it took to execute

    '''
    def ex(*args,**kwargs):
        t = time.time()
        res = f(*args,**kwargs)
        print("Function {} took {:.4f} seconds".format(f.__name__,time.time()-t))
        return res
    return ex

def dist(p1,p2):
    '''

    :param p1: (x,y) point coords
    :param p2: (x,y) point coords
    :return: Distance between p1 and p2 in 2D (float)
    '''

    return sqrt(pow(p1[0]-p2[0],2) + pow(p1[1]-p2[1],2))

def normalized_to_space(loc,size):
    '''

    :param loc: point location normalized
    :param size: image size
    :return: point lcoation in Blender Space
    '''
    #converts to Blender space location
    return (loc[0] / size[0], (size[1]-loc[1])/size[1])

def space_to_normalized(loc,size):
    #inverse of normalized_to_space
    return (loc[0]*size[0],size[1]-size[1]*loc[1])

# http://blenderscripting.blogspot.ch/2011/07/bgl-drawing-with-opengl-onto-blender-25.html
class GlDrawOnScreen():
    '''
        This class is used to draw stuff on the screen while performing Modal Operators.
        Not gonna go deep into commenting this class, you can use the link above to see more information on the stuff used here.
    '''
    black = (0.0, 0.0, 0.0, 0.7)
    white = (1.0, 1.0, 1.0, 0.5)
    progress_colour = (0.2, 0.7, 0.2, 0.7)

    def String(self, text, x, y, size, colour):
        ''' my_string : the text we want to print
            pos_x, pos_y : coordinates in integer values
            size : font height.
            colour : used for definining the colour'''
        dpi, font_id = 72, 0   # dirty fast assignment
        bgl.glColor4f(*colour)
        blf.position(font_id, x, y, 0)
        blf.size(font_id, size, dpi)
        blf.draw(font_id, text)

    def _end(self):
        bgl.glEnd()
        bgl.glPopAttrib()
        bgl.glLineWidth(1)
        bgl.glDisable(bgl.GL_BLEND)
        bgl.glColor4f(0.0, 0.0, 0.0, 1.0)

    def _start_line(self, colour, width=2, style=bgl.GL_LINE_STIPPLE):
        bgl.glPushAttrib(bgl.GL_ENABLE_BIT)
        bgl.glLineStipple(1, 0x9999)
        bgl.glEnable(style)
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glColor4f(*colour)
        bgl.glLineWidth(width)
        bgl.glBegin(bgl.GL_LINE_STRIP)

    def Rectangle(self, x0, y0, x1, y1, colour, width=2, style=bgl.GL_LINE):
        self._start_line(colour, width, style)
        bgl.glVertex2i(x0, y0)
        bgl.glVertex2i(x1, y0)
        bgl.glVertex2i(x1, y1)
        bgl.glVertex2i(x0, y1)
        bgl.glVertex2i(x0, y0)
        self._end()

    def Polygon(self, pts, colour):
        bgl.glPushAttrib(bgl.GL_ENABLE_BIT)
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glColor4f(*colour)
        bgl.glBegin(bgl.GL_POLYGON)
        for pt in pts:
            x, y = pt
            bgl.glVertex2f(x, y)
        self._end()

    def ProgressBar(self, x, y, width, height, start, percent):
        x1, y1 = x + width, y + height
        # progress from current point to either start or end
        xs = x + (x1 - x) * float(start)
        if percent > 0:
            # going forward
            xi = xs + (x1 - xs) * float(percent)
        else:
            # going backward
            xi = xs - (x - xs) * float(percent)
        self.Polygon([(xs, y), (xs, y1), (xi, y1), (xi, y)], self.progress_colour)
        self.Rectangle(x, y, x1, y1, self.white, width=1)

def draw_callback(self, context):
    #This function gets called by Modal Operators after the modal operator finishes a step.
    self.gl.ProgressBar(10, 40, 200, 16, 0, self.progress)
    self.gl.String(str(int(100 * abs(self.progress))) + "% ESC to Stop", 14, 44, 10, self.gl.white)
    self.gl.String("Processing frame {}".format(context.scene.frame_current), 20,70,15,(0.94,1.0,0.42,1))

def get_vars_from_context(context):
    #returns some important properties from the Blender context
    scene = context.scene
    props = context.window_manager.op_props
    space = context.space_data
    clip = space.clip if isinstance(space,bpy.types.SpaceClipEditor) else None
    tracks = clip.tracking.tracks if clip else None
    current_frame = scene.frame_current
    clip_end = scene.frame_end
    clip_start = scene.frame_start

    return scene, props, space, clip, tracks, current_frame, clip_end, clip_start


class ScenarioManager():
    '''
    This is a context manager that can be used with Blender. It makes initializing context and managing resources easier.

    Usage: with ScenarioManager(context,scene_name,area_type) as sc:

    Sets the scene and area as soon as the 'with' block is executed. You can load resources using the ScenarioManager methods.

        1. get_node_group(group_name,type,delete_at_end=True) - Gets a node group by its name. If it doesn't exist, a node_group with that name and type
            is created. If delete_at_end is True, the node_group gets deleted at the end of the 'with' block.

        Same process for all the other get methods.
    '''
    def __init__(self, context, scene_name, area_type=None):
        self.context = context
        self.default_scene = context.scene if scene_name else None
        self.default_area_type = self.context.area.type
        self.scene_name = scene_name
        self.area_type = area_type if area_type else self.default_area_type
        self.scenes = bpy.data.scenes
        self.node_groups = bpy.data.node_groups
        self.removals = {}

    def __enter__(self):
        #setting scene
        if self.scene_name in self.scenes.keys():
            self.context.screen.scene = self.get_scene(self.scene_name,False)
        else:
            self.context.screen.scene = self.get_scene(self.scene_name,True)
        self.context.area.type = self.area_type
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.context.screen.scene = self.default_scene
        self.context.area.type = self.default_area_type

        for key in self.removals.keys():

            id = getattr(bpy.data,key)
            for elem in self.removals[key]:
                id.remove(elem,True)


    def get_node_group(self,group_name,type,delete_at_end=False):
        if group_name in bpy.data.node_groups.keys():
            tree = bpy.data.node_groups[group_name]
        else:
            tree = bpy.data.node_groups.new(group_name,type)
        if delete_at_end:
            self.remove_at_end("node_groups", tree)
        return tree

    def get_scene(self,scene_name,delete_at_end=False):
        if scene_name in bpy.data.scenes:
            res = bpy.data.scenes[scene_name]
        else:
            res  = bpy.data.scenes.new(scene_name)
        if delete_at_end:
            self.remove_at_end("scenes", res)
        return res

    def get_image(self,path,delete_at_end=False):
        found = None
        for img in bpy.data.images:
            if img.filepath == path:
                found = img
                break
        else:
            found = bpy.data.images.load(path,False)
        if delete_at_end:
            self.remove_at_end("images",found)
        return found


    def remove_at_end(self,type,item):
        self.removals[type] = self.removals.get(type,[]) + [item]
