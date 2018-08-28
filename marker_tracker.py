#These operators will not work without numpy and scipy, so it is important you have these installed before continuing.

import importlib
np = importlib.util.find_spec("numpy")
if np is not None:
    import numpy as np
else:
    raise ImportError("Need numpy")
sp = importlib.util.find_spec("scipy")
if sp is not None:
    from scipy.ndimage.measurements import find_objects, label
    from scipy.ndimage import imread
else:
    raise ImportError("Need scipy")

import bpy
from .utils import (
    time_it,
    ScenarioManager,
    get_vars_from_context,
    normalized_to_space,
    space_to_normalized,
    dist,
    GlDrawOnScreen,
    draw_callback
)

from pprint import pprint as pp
import time


@time_it
def getPoints(img, color, thresh,context):
    '''

    :param img: Image to work on, as BlenderData
    :param color: Color to search for
    :param thresh: Minimum amount of connected pixels that form a cluster
    :param context: Blender Context
    :return: List of 2D Point locations where makers should be placed.
    '''

    with ScenarioManager(context,"getPointsFromImageScene","NODE_EDITOR") as sc:
        scene, props, space, clip, tracks, current_frame, clip_end, clip_start = get_vars_from_context(context)

        #we will use a CompositorNodeTree to filter the image to black and white, where white pixels will be pixels that
        #originally had the color specified in the parameters.
        tree_node =  sc.get_node_group("TestTree","CompositorNodeTree")
        height = props.ignore_height

        dir = props.dir

        #prepare scene for Compositing
        scene.use_nodes = True
        space.tree_type = "CompositorNodeTree"
        context.space_data.node_tree = tree_node
        tree_node = context.space_data.edit_tree

        #delete all objects in this scene
        for key in context.scene.objects.keys():
            bpy.data.objects.remove(bpy.data.objects[key], True)

        #make sure there is a camera available in this scene for rendering
        bpy.ops.object.camera_add()
        bpy.context.scene.camera = bpy.context.active_object
        cameraKey = bpy.context.active_object.name

        # create input node and input the image
        input_node = tree_node.nodes.new(type="CompositorNodeImage")
        input_node.image = img
        # create color node
        color_node = tree_node.nodes.new(type="CompositorNodeChromaMatte")
        color_node.gain = 1
        color_node.tolerance = 0.69
        color_node.threshold = 0.52
        color_node.inputs[1].default_value = color

        # create invert node
        invert_node = tree_node.nodes.new(type="CompositorNodeInvert")

        # add file output node
        output_node = tree_node.nodes.new(type="CompositorNodeOutputFile")  # file output

        # construct filepath for the file
        # working directory
        w_dir = dir[:dir.rfind("\\")+1]
        #filename
        output_node.file_slots[0].path = "audi"
        f_name = output_node.file_slots[0].path + "0001"



        # full path
        output_fpath = w_dir + f_name + ".png"
        output_node.base_path = w_dir

        # create links
        links = tree_node.links
        links.new(input_node.outputs[0], color_node.inputs[0])
        links.new(color_node.outputs[1], invert_node.inputs[1])
        links.new(invert_node.outputs[0], output_node.inputs[0])
        # render scene and save resulting file
        bpy.ops.render.render()

        #we will now read the output image using scipy.ndimage, a library to work with images.
        try:
            sc_img = imread(output_fpath,True)
        except FileNotFoundError as e:
            print(e)
            return []

        #this converts the image to 1's and 0's
        img = np.where(sc_img > 0 ,1, 0)

        #specifies what pattern to look for in the image and labels each pattern found with a number.
        #See scipy.ndimage.measurements.label and find_objects for more information on how this works.
        labelled_array, num_features = label(img, np.ones((3,3),dtype=np.uint8))
        #Finds all the labels in the image
        slices = find_objects(labelled_array)

        points_from_slices = []
        for i,sl in enumerate(slices):
            ct = np.count_nonzero(labelled_array[sl])

            #print("Slice {} has {} values".format(i,ct))
            #If the current slice has more non-zero pixels than the treshold specified, then this is a cluster.
            if ct>thresh:
                #Get the average x coordinate and the average y coord of the slice and append to the result.
                cordx = (sl[1].start + sl[1].stop) / 2
                cordy = (sl[0].start + sl[0].stop) / 2
                if cordy > height:
                    points_from_slices.append((cordx,cordy))



        bpy.data.objects.remove(bpy.data.objects[cameraKey], True)


    return points_from_slices

@time_it
def get_frame_image(context):
    '''
    This function simply gets the current frame in image format.

    If the current clip is an image sequence, then we simply compute the path to the current frame and set the dir attribute to that.

    If it is a movie, we first convert the frame to an image useing a CompositorNodeTree and rendering that, then we set the dir attribute to the
    filepath.

    The temporary image in this case is saved as safedelete.png in the folder of the current blend file.

    :param context: Current Blender Context
    :return: Nothing, but sets the context.window_manager.op_props.dir attribute to the path of the render result.
    '''
    an = context.edit_movieclip

    scene = context.scene

    if an.source == 'MOVIE':
        with ScenarioManager(context, scene.name, "NODE_EDITOR") as sc:
            # create image from movie current frame using compositor nodes
            # img=bpy.data.images.load(an.filepath,True)

            #create the Node Tree
            context.space_data.tree_type = "CompositorNodeTree"
            context.scene.use_nodes = True
            tree_name = str(time.time()).partition(".")[0]
            ng = sc.get_node_group(tree_name, "CompositorNodeTree")

            default_tree = context.space_data.node_tree
            context.space_data.node_tree = ng

            tree = context.space_data.edit_tree

            for node in tree.nodes:
                tree.nodes.remove(node)
            input_node = tree.nodes.new(type="CompositorNodeMovieClip")
            input_node.clip = an

            output_node = tree.nodes.new(type="CompositorNodeComposite")
            links = tree.links
            links.new(input_node.outputs[0], output_node.inputs[0])

            #Render the Node Tree
            save_dir = bpy.data.filepath[:bpy.data.filepath.rfind("\\")] + "\\temp\\" + "safedelete.png"
            dir = bpy.data.scenes[scene.name].render.filepath
            bpy.data.scenes[scene.name].render.filepath = save_dir
            bpy.data.scenes[scene.name].render.resolution_x = an.size[0]
            bpy.data.scenes[scene.name].render.resolution_y = an.size[1]
            bpy.data.scenes[scene.name].render.resolution_percentage = 100
            bpy.ops.render.render(write_still=True)
            bpy.data.scenes[scene.name].render.filepath = dir

            context.window_manager.op_props.dir = save_dir

            context.space_data.node_tree = default_tree
    else:
        #If it's an image sequence, simply use the current frame, instead of rendering a temporary image.
        print("Its an image sequence at frame {}".format(scene.frame_current))
        img_path = str(scene.frame_current).zfill(5)
        base = an.filepath[:an.filepath.find('0')]
        format = an.filepath[an.filepath.rfind('.'):]
        real_path =  base + img_path + format
        context.window_manager.op_props.dir = real_path

def set_marker_search_area(marker,sz,img=(0,0)):
    #Sets the search size of a marker to sz
    w,h = img
    a = - sz / 2 / w
    b = - sz / 2 / h
    marker.search_min = (a,b)
    marker.search_max = (-a,-b)

@time_it
def assignMarkers(img, points, context):
    scene, props, space, clip, tracks, current_frame, clip_end, clip_start = get_vars_from_context(context)

    #new_size = (-pattern_size,+pattern_size,-pattern_size,-pattern_size,pattern_size,)
    #These 3 constants will help with precise adjustment of the marker pattern size
    ratio_x = clip.track_color.pattern_size / clip.size[0]
    ratio_y = clip.track_color.pattern_size / clip.size[1]
    signs = [(-1, -1), (1, -1), (1, 1), (-1, 1)]

    for i in points:
        #add the points to the scene as markers. Have to convert the point location to Blender space coordinates.
        bpy.ops.clip.add_marker(location=normalized_to_space(i,img.size))

    #Sets pattern size and search size of added markers.
    for track in tracks:
        track.markers[0].frame = scene.frame_current
        for i,corner in enumerate(track.markers[0].pattern_corners):
            corner[0] = ratio_x * signs[i][0]
            corner[1] = ratio_y * signs[i][1]
        set_marker_search_area(track.markers[0],clip.track_color.search_size,clip.size)

    return

def moveMarkers(tracks,points,frame,size,d):

    '''

    :param tracks: Blender Tracks on source clip
    :param points: Points in the new frame
    :param frame: Frame number
    :param size: Image size
    :param d: Maximum distance a marker can move
    :return: Nothing, but it assigns each existing marker to a new position or records the marker as lost.
    '''
    #keep track of lost markers
    lost = {}
    for t in tracks:
        #find the last recorded marker for this track
        marked = False
        ct = 1
        mrk = None
        while mrk == None:
            if (frame-ct<0):
                print("Something is wrong here")
                break
            mrk = t.markers.find_frame(frame-ct)
            ct+=1
        #if the last recorder marker is disabled, add this track to the lost tracks
        if mrk.mute:
            lost[t.name] = (t,mrk)
            continue

        #we now check what is the closest point to the location of this marker and move the marker to that location
        pos = space_to_normalized(mrk.co,size)
        for i,p in enumerate(points):
          if dist(pos,p)<d:
              t.markers.insert_frame(frame,normalized_to_space(p,size))
              points.pop(i)
              marked = True
              break
        #if no points were found close enough to this marker, we disable the marker.
        if not marked:
                mrk.mute = True

    #if there are points that haven't been assigned yet, check within lost tracks if any of them is close enough to be assigned to a new point.
    if len(points) > 0:
        keys = []
        for k,vl in lost.items():
            t,mrk = vl
            pos = space_to_normalized(mrk.co,size)
            for (i,p) in enumerate(points):
                if (dist(pos,p)<d):
                    mrk.mute = False
                    t.markers.insert_frame(frame,normalized_to_space(p,size))
                    points.pop(i)
                    keys.append(k)
        for k in keys:
            del lost[k]
    pp(lost)
    return


class CLIP_OT_colortrack(bpy.types.Operator):
    '''
        This operator will use the image pointed at by context.window_manager.op_props.dir to find the clusters of points which will
        form the new markers.
    '''
    bl_idname = "clip.color_track"
    bl_label = "Track Color"

    def execute(self, context):

        with ScenarioManager(context,context.scene.name,context.area.type) as sc:
            #this will delete safedelete.png if the source clip is a MOVIE
            dir = context.window_manager.op_props.dir
            delete_it = True
            if context.edit_movieclip.source != 'MOVIE':
                delete_it = False
            img = sc.get_image(dir,delete_it)

            context.window_manager.op_props.dir = bpy.data.filepath[:bpy.data.filepath.rfind("\\")] + "\\temp\\" + "safedelete.png"
            points = getPoints(img, context.space_data.clip.track_color.color, context.space_data.clip.track_color.thresh,context)

            assignMarkers(img, points, context)


        return {'FINISHED'}

class CLIP_OT_assignMarkersOnColor(bpy.types.Operator):
    '''
        This operator creates the matte of the current frame, filtering out any other colors except the one specified, then it invokes
        CLIP_OT_colortrack to work on that matte.

        See create_matte(context) and CLIP_OT_colortrack for more info
    '''
    bl_idname = "clip.assignmarkersoncolor"
    bl_label = "Assign Markers"
    bl_description = "Assigns markers on clusters formed mostly of the chosen color"

    def execute(self, context):

        get_frame_image(context)
        bpy.ops.clip.color_track()


        return {'FINISHED'}

class CLIP_OT_moveMarkers(bpy.types.Operator):
    '''
        Processes a frame, finds the points similarly to CLIP_OT_colortrack, but this time, instead of adding new markers,
        existing markers are moved to their appropriate location based on max distance
    '''
    bl_label = "Move Markers to Positions"
    bl_idname = "clip.movemarkers"

    def execute(self, context):
        with ScenarioManager(context,context.scene.name,"CLIP_EDITOR") as sc:
            scene, props, space, clip, tracks, current_frame, clip_end, clip_start = get_vars_from_context(context)
            cur = scene.frame_current
            scene.frame_current+=1
            get_frame_image(context)
            delete_it = True
            if context.edit_movieclip.source != 'MOVIE':
                delete_it = False
            img = sc.get_image(props.dir, delete_it)
            print("Current image being processed : {}".format(props.dir))
            context.window_manager.op_props.dir = bpy.data.filepath[:bpy.data.filepath.rfind("\\")] + "\\temp\\" + "safedelete.png"
            points = getPoints(img, context.space_data.clip.track_color.color,
                               context.space_data.clip.track_color.thresh, context)
            moveMarkers(tracks,points,scene.frame_current,clip.size,props.max_dist)


        return {'FINISHED'}

    @classmethod
    def poll(cls,context):
        return (context.area.spaces.active.clip is not None)

class TrackMarkersModalOperator(bpy.types.Operator):
    '''
        Invokes CLIP_OT_moveMarkers repeteadly until we reach the end frame of the currenct clip in the current scene.
    '''
    bl_idname = "tracking.move_markers"
    bl_label = "Random Markers"
    bl_description = "Track current markers, slowly but steady and with high accuracy"

    _timer = None

    #used for drawing on the screen
    _draw_handler = None
    gl = GlDrawOnScreen()
    progress = 0
    start = 0


    def modal(self, context, event):
        #Only respond to TIMER events, if ESC event was received, close the modal operator
        scene = context.scene
        if event.type in {'ESC'}:
            self.cancel(context)
            return {'FINISHED'}
        elif event.type not in {'TIMER'}:
            return {'PASS_THROUGH'}


        #if we reached the end frame, close operator
        if scene.frame_current >= scene.frame_end:
            self.cancel(context)
            return {'FINISHED'}

        #Stop timer while executing work
        self.stop_timer(context)

        #invoke CLIP_OT_moveMarkers
        bpy.ops.clip.movemarkers('INVOKE_DEFAULT')

        self.progress = (self.current - self.start + 1) / self.total
        self.current+=1

        # Start timer again for the next iteration
        self.start_timer(context)

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):

        scene, props, space, clip, tracks, current_frame, clip_end, clip_start = get_vars_from_context(context)
        self.total = scene.frame_end - scene.frame_current + 1
        self.progress = 0
        self.start = scene.frame_current
        self.current = self.start

        # draw progress
        args = (self, context)
        self._draw_handler = bpy.types.SpaceClipEditor.draw_handler_add(
            draw_callback, args,
            'WINDOW', 'POST_PIXEL'
        )

        self.start_timer(context)
        #register modal operator
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


    def stop_timer(self, context):
        context.window_manager.event_timer_remove(self._timer)

    def start_timer(self, context):
        self._timer = context.window_manager.event_timer_add(time_step=context.window_manager.op_props.time_step, window=context.window)

    def cancel(self, context):
        self.stop_timer(context)
        bpy.types.SpaceClipEditor.draw_handler_remove(self._draw_handler,'WINDOW')

    def __init__(self):
        self.t = time.time()

    def __del__(self):
        print("Finished in  %.2f seconds" % (time.time() - self.t))

    @classmethod
    def poll(cls, context):
        return (context.area.spaces.active.clip is not None)

class CLIP_PT_color(bpy.types.Panel):
    #This is the panel that gives you access to the operator CLIP_OT_AssignMarkersOnColor
    bl_label = "Color Tracker"
    bl_space_type = "CLIP_EDITOR"
    bl_region_type = "TOOLS"

    def draw(self, context):
        an = context.edit_movieclip
        wm = context.window_manager
        layout = self.layout
        layout.label("Track Color")
        layout.separator()

        row = layout.row(align=True)
        row.prop(an.track_color,"color")
        row = layout.row()
        row.prop(an.track_color,"thresh")
        row = layout.row()
        row.label("Pattern size")
        row.prop(an.track_color, "pattern_size")
        row = layout.row()
        row.label("Search box size")
        row.prop(an.track_color, "search_size")
        row = layout.row()
        row.label("Height to ignore")
        row.prop(wm.op_props, "ignore_height")
        #layout.operator("clip.color_track")
        row = layout.row(align=True)
        row.scale_y = 1.5
        row.operator("clip.assignmarkersoncolor", icon="PLAY")

class TrackPanel(bpy.types.Panel):
    '''
        This panel gives access to the modal operator TrackMarkersModalOperator.
    '''
    bl_label = "Track Markers"
    bl_idname = "trackmarkers"
    bl_space_type = 'CLIP_EDITOR'
    bl_region_type = 'TOOLS'
    bl_category = "Track"

    @classmethod
    def poll(cls, context):
        return (context.area.spaces.active.clip is not None)

    def draw(self,context):
        layout = self.layout
        wm = context.window_manager
        row = layout.row(align=True)
        row.scale_y = 1.5
        row.operator("tracking.move_markers", text="Automated tracking", icon="PLAY")

        layout.separator()

        row = layout.row()
        row.prop(wm.op_props, "time_step")

        row = layout.row()
        row.prop(wm.op_props, "max_dist")