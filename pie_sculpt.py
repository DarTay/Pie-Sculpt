bl_info = {
    "name": "Pie Sculpt",
    "author": "Darcy Taylor",
    "version": (1, 0),
    "blender": (2, 90, 0),
    "location": "View3D > Add > Mesh > New Object",
    "description": "Adds a new Mesh Object",
    "warning": "",
    "doc_url": "",
    "category": "Add Mesh",
}


import bpy
from bpy_extras import view3d_utils

#Main pie menu and calling operator
class PS_MT_pie_sculpt(bpy.types.Menu):
    bl_label = "Pie Sculpt"

    def draw(self, context):
        pie = self.layout.menu_pie()
        pie.operator("ps.cube_add", text = "Mesh Add", icon = "BLENDER")
        pie.operator("ps.select_object", text = "Select Object", icon = "BLENDER")
        pie.operator("ps.mask_brush", text = "Mask Brush", icon = "BLENDER")


class PS_OP_pie_sculpt(bpy.types.Operator):
    bl_idname = "ps.pie_sculpt"
    bl_label = "Pie Sculpt"

    def execute(self, context):
        for ob in context.scene.objects: #rename object to avoid a Blender crash and naming conflicts
            if ob.name == 'object_mesh':
                ob.name = "sculpt_mesh"
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

    def modal(self, context: bpy.types.Context, event: bpy.types.Event):

        for ob in context.scene.objects:#select the object_mesh item we just created
            if context.mode == 'OBJECT':   
                if ob.name != 'object_mesh':
                    bpy.ops.object.select_all(action='DESELECT')
                elif ob.name == 'object_mesh':
                    ob.select_set(True)
                    context.view_layer.objects.active = ob

        if event.type in {'ESC', 'DEL', 'BACK_SPACE'}:#cancel and delete object
            if context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            else:
                bpy.ops.object.delete(use_global=False)    
                return {'CANCELLED'}

        if event.type == 'ACCENT_GRAVE':
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.modifier_apply(modifier="Subdivision")
            bpy.ops.object.mode_set(mode='SCULPT')
            return {'FINISHED'}
        else:
            return {'PASS_THROUGH'}

        return {'RUNNING_MODAL'}
    
    def invoke(self, context, event):
        # Add and name object make sure there is at least one active object in the scene
        bpy.ops.mesh.primitive_cube_add()
        context.active_object.modifiers.new(name="Subdivision", type='SUBSURF')
        context.active_object.modifiers["Subdivision"].levels = 2
        context.active_object.name = "object_mesh"        
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


class PS_OT_select_object(bpy.types.Operator):
    """Select Object"""
    
    bl_idname = "ps.select_object"
    bl_label = "Select Object"


    def modal(self, context, event):
        if event.type == 'TIMER':
            bpy.ops.object.select_all(action='DESELECT')
            Raycast(context, event)
            return {'RUNNING_MODAL'}
        elif event.type == 'LEFTMOUSE':
            if context.active_object is not None:
                bpy.ops.object.mode_set(mode='SCULPT')
            context.window_manager.event_timer_remove(self._timer)
            return {'FINISHED'}
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            context.window_manager.event_timer_remove(self._timer)
            return {'CANCELLED'}
        else:
            return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        if context.space_data.type == 'VIEW_3D':
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
    if best_obj is not None:
        # for selection etc. we need the original object,
        # evaluated objects are not in viewlayer
        best_original = best_obj.original
        best_original.select_set(True)
        context.view_layer.objects.active = best_original


class PS_OT_mask_brush(bpy.types.Operator):
    bl_idname = "ps.mask_brush"
    bl_label = "Mask Brush"
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        if context.mode == 'SCULPT':
            print("In sculpt mode sculpt mode select mask brush")
            bpy.ops.wm.tool_set_by_id(name="builtin_brush.Mask",space_type="VIEW_3D")
            return {'FINISHED'}
        elif context.mode != 'SCULPT':
            print("Not in sculpt mode sculpt mode activate")
            bpy.ops.object.mode_set(mode='SCULPT')
            bpy.ops.wm.tool_set_by_id(name="builtin_brush.Mask", space_type="VIEW_3D")
            return {'FINISHED'}



addon_keymaps = []


classes = (
    PS_MT_pie_sculpt,
    PS_OP_pie_sculpt,
    PS_OT_cube_add,
    PS_OT_select_object,
    PS_OT_mask_brush,
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
