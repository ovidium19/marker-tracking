import bpy
from .utils import (
    get_vars_from_context,
    GlDrawOnScreen,
    draw_callback
)
import time

class CLIP_OT_ToSequence(bpy.types.Operator):
    '''
    This Operator simply renders the current scene and node_tree. Not meant to work by itself, it is
    invoked by the ConverModalOperator on every step.
    '''
    bl_label = "Move Markers to Positions"
    bl_idname = "clip.movtosequence"
    clip = None
    def execute(self, context):
        scene, props, space, clip, tracks, current_frame, clip_end, clip_start = get_vars_from_context(context)
        # Check if there is a clip to work on
        context.area.type = "CLIP_EDITOR"
        self.clip = context.edit_movieclip
        context.area.type = "NODE_EDITOR"
        if not self.clip:
            print("No clip recorded")
            return {'CANCELLED'}


        #render the current node_tree with these settings.
        #self.clip.current_path is the path where the current frame should be saved as an image.

        bpy.data.scenes[scene.name].render.filepath = self.clip.current_path
        bpy.data.scenes[scene.name].render.resolution_x = self.clip.size[0]
        bpy.data.scenes[scene.name].render.resolution_y = self.clip.size[1]
        bpy.data.scenes[scene.name].render.resolution_percentage = 100
        bpy.ops.render.render(write_still=True)

        return {'FINISHED'}


class ConvertModalOperator(bpy.types.Operator):
    '''
    This operator converts current clip from movie to image sequence.
    You have to specify a directory where the image sequence will be saved.
    The image sequence is saved as : capture0001 up to however many frames you are converting.
    No matter what your frame_start is set inside Blender, the count always starts from capture0001

    Best used to synchronize two different clips so that they have the same start frame and end frame.
    Other operators work better on image sequences than movies, so it's good to convert first.

    WARNING: This operator will crash Blender, but the image sequence will be saved. Make sure you save
             your work before executing this operator.
    '''
    bl_idname = "clip.convertit"
    bl_label = "Convert to Sequence"
    bl_description = "Convert clip to sequence from start frame to end frame"


    _timer = None

    _draw_handler = None

    gl = GlDrawOnScreen()

    progress = 0
    start = 0

    def modal(self, context, event):
        #Only respond to TIMER events.
        #If ESC is pressed, exit operator.
        scene = context.scene
        if event.type in {'ESC'}:
            self.cancel(context)
            return {'FINISHED'}
        elif event.type not in {'TIMER'}:
            return {'PASS_THROUGH'}


        #If work is done, set scene and area to the CLIP_EDITOR and finish operator
        if scene.frame_current >= scene.frame_end:

            context.space_data.node_tree = self.default_tree
            context.area.type = "CLIP_EDITOR"
            context.screen.scene = self.default_scene
            bpy.data.node_groups.remove(self.node_tree, True)
            bpy.data.scenes.remove(self.scene,True)
            self.cancel(context)
            return {'FINISHED'}

        #Stop the TIMER event and perform the work
        self.stop_timer(context)


        scene, props, space, clip, tracks, current_frame, clip_end, clip_start = get_vars_from_context(context)
        #creating the path for the current frame
        save_dir = self.clip.convert_path[:self.clip.convert_path.rfind("\\") + 1] + "capture" + str(self.count).zfill(
            5) + ".png"
        print("Working on {}".format(save_dir))
        self.clip.current_path = save_dir
        #invoke the operator from above
        bpy.ops.clip.movtosequence('INVOKE_DEFAULT')
        #increase frame and continue
        scene.frame_current+=1
        self.count+=1
        self.progress = (self.current - self.start + 1) / self.total
        self.current += 1

        # Start the TIMER again. When the TIMER event is called, this function will execute again.
        self.start_timer(context)

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        #Creates a new scene with a new CompositorNodeTree that simply captures the current frame in an image.
        scene = context.scene
        self.count = 1
        self.context = context
        self.clip = context.area.spaces.active.clip
        context.scene.frame_current = context.scene.frame_start
        self.default_scene = context.scene
        self.scene =bpy.data.scenes.new("ConvertStuff")
        self.scene.frame_start = self.default_scene.frame_start
        self.scene.frame_end = self.default_scene.frame_end
        self.scene.frame_current = self.default_scene.frame_start

        context.screen.scene = self.scene
        context.area.type = "NODE_EDITOR"
        context.space_data.tree_type = "CompositorNodeTree"
        context.scene.use_nodes = True

        tree_name = str(time.time()).partition(".")[0]
        self.node_tree =bpy.data.node_groups.new(tree_name,"CompositorNodeTree")
        self.default_tree = context.space_data.node_tree
        context.space_data.node_tree = self.node_tree
        tree = context.space_data.node_tree

        for node in tree.nodes:
            tree.nodes.remove(node)
        input_node = tree.nodes.new(type="CompositorNodeMovieClip")
        input_node.clip = self.clip

        output_node = tree.nodes.new(type="CompositorNodeComposite")
        links = tree.links
        links.new(input_node.outputs[0], output_node.inputs[0])

        self.total = scene.frame_end - scene.frame_current + 1
        self.progress = 0
        self.start = scene.frame_current
        self.current = self.start
        # draw progress
        args = (self, context)

        #add the draw handler to the Space. This lets us draw on the screen at the end of each step. The draw function called is imported from utils.py
        #under the name draw_callback
        self._draw_handler = bpy.types.SpaceNodeEditor.draw_handler_add(
            draw_callback, args,
            'WINDOW', 'POST_PIXEL'
        )

        #this line register the modal operator with the window allowing it to work in modal.
        context.window_manager.modal_handler_add(self)

        #Our modal doesn't want input, it just wants to do the same thing over and over until it's done. We respond only to TIMER events.
        #Start timer at first
        self.start_timer(context)

        return {'RUNNING_MODAL'}

    def stop_timer(self, context):
        context.window_manager.event_timer_remove(self._timer)

    def start_timer(self, context):
        self._timer = context.window_manager.event_timer_add(time_step=0.01,
                                                             window=context.window)

    def cancel(self, context):

        self.stop_timer(context)
        bpy.types.SpaceClipEditor.draw_handler_remove(self._draw_handler, 'WINDOW')

    def __init__(self):
        pass

    def __del__(self):
        pass

    @classmethod
    def poll(cls, context):
        return (context.area.spaces.active.clip is not None)

class ConvertPanel(bpy.types.Panel):
    bl_label = "Converter"
    bl_space_type = 'CLIP_EDITOR'
    bl_region_type = 'TOOLS'
    bl_category = "Clip"

    def draw(self, context):
        layout = self.layout
        mv = context.area.spaces.active.clip
        row = layout.row()
        row.scale_y = 1.5
        row.operator("clip.convertit", text="Convert to Sequence", icon="PLAY")
        row = layout.row()
        row.prop(mv,"convert_path")

