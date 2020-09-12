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


#Main pie menu and calling operator
class PS_MT_pie_sculpt(bpy.types.Menu):
    bl_label = "Pie Sculpt"

    def draw(self, context):
        pie = self.layout.menu_pie()
        pie.operator("ps.cube_add", text = "Mesh Add", icon = "BLENDER")
        pie.operator("ps.select", text = "Select Active", icon = "BLENDER")
        pie.operator("ps.mask_brush", text = "Mask Brush", icon = "BLENDER")


class PS_OP_pie_sculpt(bpy.types.Operator):
    bl_idname = "ps.pie_sculpt"
    bl_label = "Pie Sculpt"

    def execute(self, context):
        bpy.ops.wm.call_menu_pie(name="PS_MT_pie_sculpt")
        return{'FINISHED'}


#Switch to object mode, Add cube, Add multires, Subdiv 3x, back to sculpt mode for shaping
class PS_OT_cube_add(bpy.types.Operator):
    """Add sub-d Mesh"""
    bl_idname = "ps.cube_add"
    bl_label = "Cube Add"

    def modal(self, context: bpy.types.Context, event: bpy.types.Event):
        if event.type == 'Q':#if event.type != 'F1' finalize our object and go back to sculpt mode
            bpy.ops.object.mode_set(mode='OBJECT')
            if context.mode != 'SCULPT' and context.active_object.name == "object_mesh":
                context.active_object.name = "sculpt_mesh"
                bpy.ops.object.modifier_apply(modifier="Subdivision")
                bpy.ops.object.mode_set(mode='SCULPT')
                return {'FINISHED'}
        elif event.type in {'RIGHTMOUSE', 'ESC'}:#cancel and delete object
            if context.active_object.name == "object_mesh":
                bpy.ops.object.delete(use_global=False)
                #TODO set active object back to pervious object and go back to sculpt mode
                #if active_object == none just stay in object mode
                return {'CANCELLED'}
        else:
            return {'PASS_THROUGH'}
        return {'RUNNING_MODAL'}
    
    def invoke(self, context, event):
        #create our multires cube
        bpy.ops.mesh.primitive_cube_add()

        if context.active_object.name != "object_mesh": #rename the cube
            context.active_object.name = "object_mesh"
        if not context.active_object.modifiers: #if we have no modifiers add modifier
            context.active_object.modifiers.new(name="Subdivision", type='SUBSURF')
            context.active_object.modifiers["Subdivision"].levels = 2

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


class PS_OT_select(bpy.types.Operator):
    """Select Object"""
    bl_idname = "ps.select"
    bl_label = "Object Select"


    def modal(self, context: bpy.types.Context, event: bpy.types.Event):
        print("Doing modal stuff until.....")
        if event.type == 'Q': #Selection complete go back to sculpt mode
            bpy.ops.object.mode_set(mode='SCULPT')
            return {'FINISHED'}
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            #cancel operations and undo steps and set mode back to previous mode
            bpy.ops.object.mode_set(mode='SCULPT')
            return {'CANCELLED'}
        else:
            return {'PASS_THROUGH'}
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        bpy.ops.object.mode_set(mode='OBJECT')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}



class PS_OT_mask_brush(bpy.types.Operator):
    bl_idname = "ps.mask_brush"
    bl_label = "Mask Brush"
    
    def execute(self, context):
        if context.active_object is None:
            print("Active object == none: Cancel")
            return {'CANCELLED'}
        elif context.mode == 'SCULPT':
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
    PS_OT_select,
    PS_OT_mask_brush,
)


def register():
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new("ps.pie_sculpt", type='Q', value='PRESS')
        addon_keymaps.append((km, kmi))
    
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    for c in classes:
        bpy.utils.unregister_class(c)