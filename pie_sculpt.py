bl_info = {
    "name": "Pie Sculpt",
    "author": "D_Ham",
    "version": (1, 1),
    "blender": (2, 90, 0),
    "location": "Name: Pie Sculpt, Key: ` ",
    "description": "Adds ease of use to sculpt mode",
    "warning": "",
    "doc_url": "",
    "category": "Sculpt",
}


import bpy
from bpy_extras import view3d_utils

#Main pie menu and calling operator
class PS_MT_pie_sculpt(bpy.types.Menu):
    bl_idname = "PS_MT_pie_sculpt"
    bl_label = "Pie Sculpt"

    def draw(self, context):
        pie = self.layout.menu_pie()
        pie.operator("ps.cube_add", text = "Mesh Add", icon = "BLENDER")
        pie.operator("ps.select_object", text = "Select Object", icon = "BLENDER")


class PS_OT_pie_sculpt(bpy.types.Operator):
    bl_idname = "ps.pie_sculpt"
    bl_label = "Pie Sculpt"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):      
        if context.mode in {'SCULPT', 'OBJECT', 'EDIT_MESH'}:#If we are in one of our three working modes
            bpy.ops.wm.call_menu_pie(name="PS_MT_pie_sculpt")
            return {'FINISHED'}
        else:
            print("Not in one of our 3 working modes")
            return {'CANCELLED'}
        

#Switch to object mode, Add cube, Add Sub-d mod, Subdiv 2x, back to sculpt mode for shaping
class PS_OT_cube_add(bpy.types.Operator):
    """Add sub-d Mesh"""
    bl_idname = "ps.cube_add"
    bl_label = "Cube Add"
    bl_options = {'REGISTER', 'UNDO'}

    def modal(self, context: bpy.types.Context, event: bpy.types.Event):
        #If we have no active object creat a new one and name it object_mesh
        if context.active_object == None:
            bpy.ops.mesh.primitive_cube_add()
            bpy.ops.ed.undo_push(message='Add an undo step *function may be moved*')#This is a hacky way of preventing a Undo/Redo ctrl + z crash
            context.active_object.name = "object_mesh"
            context.active_object.modifiers.new(name="Subdivision", type='SUBSURF')
            context.active_object.modifiers["Subdivision"].levels = 2
            context.object.data.use_mirror_x = True
        #apply our settings and turn off anything we turned on
        elif event.type == 'RET':
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.modifier_apply(modifier="Subdivision")
            context.object.data.use_mirror_x = False
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
            bpy.context.object.name = "sculpt_mesh"
            bpy.ops.object.mode_set(mode='SCULPT')
            return {'FINISHED'}
        #cancel object creation and do clean up if we have no objects in scene stay in object mode
        elif event.type in {'ESC', 'DEL', 'BACK_SPACE'}:#cancel and delete object
            if context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            else:
                bpy.ops.object.delete(use_global=False)
                return {'CANCELLED'}    
        #pass thru input to shape our object and prevent reuse of creation pie
        elif context.active_object.name == 'object_mesh' and event.type != 'ACCENT_GRAVE':
            return {'PASS_THROUGH'}
        #enforce editing of the object_mesh to avoid potential errors
        elif context.active_object.name != 'object_mesh' and context.mode == 'OBJECT':
            for ob in context.scene.objects:
                if ob.name != 'object_mesh':
                    bpy.ops.object.select_all(action='DESELECT')
                else:
                    ob.select_set(True)
                    context.view_layer.objects.active = ob
        return {'RUNNING_MODAL'}
    
    def invoke(self, context, event):
        if context.active_object != None:
            context.view_layer.objects.active = None
        #This is a great way to set workspace but not really needed in this context
        #if context.workspace != bpy.data.workspaces['Sculpting']:
        #   context.window.workspace = bpy.data.workspaces['Sculpting']
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    

class PS_OT_select_object(bpy.types.Operator):
    """Select Object"""
    
    bl_idname = "ps.select_object"
    bl_label = "Select Object"


    def modal(self, context, event):
        if event.type == 'TIMER':
            Raycast(context, event)
            
        elif event.type == 'LEFTMOUSE':
            if context.active_object is not None:
                bpy.ops.object.mode_set(mode='SCULPT')
                context.window_manager.event_timer_remove(self._timer)
            return {'FINISHED'}

        elif event.type in {'ESC', 'DEL', 'BACK_SPACE'}:
            bpy.ops.object.mode_set(mode='SCULPT')
            context.window_manager.event_timer_remove(self._timer)
            return {'CANCELLED'}

        else:
            return {'PASS_THROUGH'}
        
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        if context.space_data.type == 'VIEW_3D':
            if context.active_object is not None:
                bpy.ops.object.mode_set(mode='OBJECT')
                self._timer = context.window_manager.event_timer_add(0.01, window=context.window)
                context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "Active space must be a View3d")
            return {'CANCELLED'}

def Raycast(context, event):
    """Run this function on left mouse, execute the ray cast"""
    
    # get the context arguments
    region = context.region
    rv3d = context.region_data
    coord = event.mouse_region_x, event.mouse_region_y

    # get the ray from the viewport and mouse
    view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
    ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
    ray_target = ray_origin + view_vector

    def visible_objects_and_duplis():
        """Loop over (object, matrix) pairs (mesh only)"""

        depsgraph = context.evaluated_depsgraph_get()
        for dup in depsgraph.object_instances:
            if dup.is_instance:  # Real dupli instance
                obj = dup.instance_object
                yield (obj, dup.matrix_world.copy())
            else:  # Usual object
                obj = dup.object
                yield (obj, obj.matrix_world.copy())

    def ObjRaycast(obj, matrix):
        """Wrapper for ray casting that moves the ray into object space"""

        # get the ray relative to the object
        matrix_inv = matrix.inverted()
        ray_origin_obj = matrix_inv @ ray_origin
        ray_target_obj = matrix_inv @ ray_target
        ray_direction_obj = ray_target_obj - ray_origin_obj

        # cast the ray
        success, location, normal, face_index = obj.ray_cast(ray_origin_obj, ray_direction_obj)

        if success:
            return location, normal, face_index
        else:
            return None, None, None

    # cast rays and find the closest object
    best_length_squared = -1.0
    best_obj = None

    for obj, matrix in visible_objects_and_duplis():
        if obj.type == 'MESH':
            hit, normal, face_index = ObjRaycast(obj, matrix)
            if hit is not None:
                hit_world = matrix @ hit
                length_squared = (hit_world - ray_origin).length_squared
                if best_obj is None or length_squared < best_length_squared:
                    best_length_squared = length_squared
                    best_obj = obj

    # now we have the object under the mouse cursor,
    # we could do lots of stuff but for the example just select.
    if best_obj is not None and context.mode == 'OBJECT':
        # for selection etc. we need the original object,
        # evaluated objects are not in viewlayer
        bpy.ops.object.select_all(action='DESELECT')
        best_original = best_obj.original
        best_original.select_set(True)
        context.view_layer.objects.active = best_original


addon_keymaps = []


classes = (
    PS_MT_pie_sculpt,
    PS_OT_pie_sculpt,
    PS_OT_cube_add,
    PS_OT_select_object,
)


def register():
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new("ps.pie_sculpt", type='ACCENT_GRAVE', value='PRESS')
        addon_keymaps.append((km, kmi))
    
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    for c in classes:
        bpy.utils.unregister_class(c)
