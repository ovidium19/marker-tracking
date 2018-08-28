import bpy

class VIEW_3D_OT_PoseBones(bpy.types.Operator):
    '''
        This operator will create empties on the bones of the current armature and will also
        create a 'Copy Location' constraint on each bone to link to its empty.
        You can specify on which layer to add the empties on from the Panel.
    '''

    bl_label = "Get Pose Bones"
    bl_idname = "armature.getposebones"
    bl_options = {'REGISTER','UNDO'}

    def execute(self, context):

        scene = context.scene
        wm = context.window_manager

        #the layer array specifies on which layers the empties will be visible
        layer1 = [False for _ in range(20)]
        layer1[wm.op_props.layer_empties-1] = True
        #get access to armature and its matrix location
        arm = context.active_object
        arm_loc = arm.matrix_world

        #the armature pose bones
        pose_bones = arm.pose.bones


        for i,pb in enumerate(pose_bones):
            #get the matrix location of each bone
            bone_loc = pb.bone.matrix_local

            #this will give you the world location of the bone
            f_loc = (arm_loc * bone_loc).to_translation()

            #Create a new empty with the computed location and small radius. Name will be integer starting from 1
            empty_obj = bpy.data.objects.new(name=str(i+1),object_data=None)
            empty_obj.location = f_loc
            empty_obj.empty_draw_size = 0.02
            empty_obj.empty_draw_type = "PLAIN_AXES"

            #Add this new empty object to the scene on the layers specified
            scene.objects.link(empty_obj)
            empty_obj.layers = layer1

            #create the new constraint between the pose bone and the target.
            constraint = pb.constraints.new('COPY_LOCATION')
            constraint.target = empty_obj
            #constraint.use_y= False


        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.active_object.type=='ARMATURE'

class CLIP_PT_EmptiesPoseBones(bpy.types.Panel):
    bl_label = "Link Bones to Empties"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"

    def draw(self,context):
        layout = self.layout
        #This property will specify on which layer the empties will be visible.
        layout.prop(context.window_manager.op_props,"layer_empties",text="Layer to use")
        layout.operator("armature.getposebones",text="Create Empties on Bones")