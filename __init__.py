#!/usr/bin/env python3

bl_info = {
    "name": "Sunders-Video-Editing",
    "description": "Animate video strips fast.",
    "author": "SunderCode",
    "version": (1, 0),
    "blender": (3, 6, 2),
    "location": "Sequencer",
    "warning": "",
    "doc_url": "",
    "tracker_url": "",
    "support": "COMMUNITY",
    "category": "Sequencer",
}
import bpy
import gpu

from gpu_extras.batch import batch_for_shader

from .bpy_ctypes import get_running_op
from .utility import change_checker, dorot, printc, try_def, bool_or, get_by_area
from .effect_fcurve import effectC, fcurveC
from .sve_struct import sve, anim_base
from .operators import \
    SVEEffects_AddEffect,\
    SVEEffects_OpenEditor,\
    SVEEffects_CloseEditor,\
    SVEEffects_Menu,\
    SVEEffects_Tester,\
    SVEEffects_AddEffect_StartEnd, \
    SEQUENCER_PT_SVE_topforce, \
    SEQUENCER_PT_SVEEffects,\
    SEQUENCER_PT_SVEEffects_startend, \
    lock_tempscene
from .globals import G


def remove_strip(sPointer):
    if sPointer in effectC.all:
        for fcurve in effectC.all[sPointer].fcurves:
            fcurve.remove_effect(effectC.all[sPointer])
            fcurve.frame_recalc()
        del effectC.all[sPointer]
    del G.strips[sPointer]

def add_strip(strip):
    if sve.type in strip and strip[sve.type] in anim_base.all:
        effectC(strip)
    else:
        G.strips[strip.as_pointer()] = strip

# if an effect strip gets deleted/undeleted or non-effect strip is added/deleted, this keeps track
def check_strip_ledger():
    sequences = bpy.context.scene.sequence_editor.sequences
    if len(G.strips) != len(sequences):
        if len(G.strips) > len(sequences):
            seqPointers = [seq.as_pointer() for seq in sequences]
            for st in G.strips.copy():
                if st not in seqPointers:
                    remove_strip(st)
        elif len(G.strips) < len(sequences):
            for seq in sequences:
                if seq.as_pointer() not in G.strips:
                    add_strip(seq)
            fcurveC.recalc_all()

class check_effect_prop_change:
    effect_check: change_checker = change_checker()
    prop_check: dict[str, change_checker] = {}

    def __call__(self):
        strip = bpy.context.active_sequence_strip
        if not strip or strip.as_pointer() not in effectC.all: return
        effect: effectC = effectC.all[strip.as_pointer()]
        if self.effect_check(strip):
            self.prop_check.clear()
            for prop in effect.prop_update:
                self.prop_check[prop] = change_checker()
                self.prop_check[prop](strip[prop])
        else:
            for prop, checker in self.prop_check.items():
                if checker(strip[prop]):
                    effect.prop_update[prop](effect, strip[prop])
check_effect_prop_change = check_effect_prop_change()

class check_running_op:
    def frame_update(self, effects = None):
        # if G.edit_strip:
        #     G.edit_strip.transform.offset_x += 0.0
        #     G.edit_strip.transform.offset_y += 0.0
        if G.orig_strip:
            G.orig_strip.transform.offset_x += 0.0
            G.orig_strip.transform.offset_y += 0.0

    def transform_value(self, sveusage: str):
        usages = sve.props[sveusage].use
        def doer(doer_effects: list[effectC]):
            fcurves = [fcurveC.all[fc] for fc in usages if fc in fcurveC.all]
            is_change = False
            for effect in doer_effects:
                is_change = is_change or bool_or([effect in fc.effects for fc in fcurves])
            if is_change:
                for upath in usages:
                    fcurveC.all[upath].keyframes_value_recalc()
                    
            self.frame_update()
        return doer

    def transform_frame(self):
        def doer(doer_effects: list[effectC]):
            fcurves = {fcurve for effect in doer_effects for fcurve in effect.fcurves}
            for fc in fcurves: fc.frame_recalc()
            self.frame_update()
        return doer


    operatorID = {}
    operator_just_ran: change_checker = change_checker()

    def __init__(self) -> None:
        self.operatorID = {
            'TRANSFORM_OT_translate': self.transform_value(sve.use_offset),
            'TRANSFORM_OT_rotate': self.transform_value(sve.use_rotation),
            'TRANSFORM_OT_resize': self.transform_value(sve.use_scale),
            # 'VIEW2D_OT_pan': None,
            'ANIM_OT_change_frame': self.frame_update,
            'TRANSFORM_OT_seq_slide': self.transform_frame(),
            'SEQUENCER_OT_slip': self.transform_frame(),
        }

    def __call__(self):
        def update_effect_on(op_idname: str, effects: list[effectC]):
            # printc(op_idname)
            opfunc = self.operatorID.get(op_idname)
            if opfunc: opfunc(effects)

        def update_edit_strip(op_idname: str):
            opids = {
                'TRANSFORM_OT_translate': sve.use_offset,
                'TRANSFORM_OT_rotate': sve.use_rotation,
                'TRANSFORM_OT_resize': sve.use_scale,
            }
            path = opids.get(op_idname)
            if path:
                for upath in sve.props[path].use:
                    if upath in fcurveC.all:
                        fcurveC.all[upath].if_not_on_fcurve()
        
        effects = [effectC.all[seq] for seq in effectC.all if effectC.all[seq].effect.select]
        if len(effects) == 0 and not G.edit_strip.select: return

        idname = get_running_op(bpy.context.window)
        
        old_value = self.operator_just_ran.old_value
        if self.operator_just_ran(idname) and old_value: 
            update_effect_on(old_value, effects)
            if G.edit_strip.select:
                update_edit_strip(old_value)
        if idname:
            update_effect_on(idname, effects)
check_running_op = check_running_op()

def draw_callback_seq_preview():
    if G.edit_strip == None: return
    
    check_effect_prop_change()
    check_strip_ledger()
    check_running_op()
    strip = bpy.context.active_sequence_strip
    if strip and strip.select and sve.type in strip and 'transform' in strip[sve.type]:
        region = bpy.context.region

        if not(bpy.context.scene.frame_current >= strip.frame_final_start and 
            bpy.context.scene.frame_current < strip.frame_final_end): return

        if strip.type in ['IMAGE','MOVIE'] and len(strip.elements) > 0:
            resxhalf = float(strip.elements[0].orig_width) / 2.0
            resyhalf = float(strip.elements[0].orig_height) / 2.0
        else:
            resxhalf = bpy.context.scene.render.resolution_x / 2.0
            resyhalf = bpy.context.scene.render.resolution_y / 2.0

        offx = strip[sve.offset_x]
        offy = strip[sve.offset_y]
        scax = strip[sve.scale_x]
        scay = strip[sve.scale_y]
        rota = strip[sve.rotation]
        crop_min_x = strip.crop.min_x
        crop_min_y = strip.crop.min_y
        crop_max_x = strip.crop.max_x
        crop_max_y = strip.crop.max_y

        # 1--2
        # |  |
        # |  |
        # 0--3
        xp = [
            offx + (- resxhalf + crop_min_x ) * scax,
            offx + (- resxhalf + crop_min_x ) * scax,
            offx + (+ resxhalf - crop_max_x ) * scax,
            offx + (+ resxhalf - crop_max_x ) * scax,
        ]
        yp = [
            offy + (- resyhalf + crop_min_y ) * scay,
            offy + (+ resyhalf - crop_max_y ) * scay,
            offy + (+ resyhalf - crop_max_y ) * scay,
            offy + (- resyhalf + crop_min_y ) * scay,
        ]

        dots = []
        for ii in range(4):
            dots.append( region.view2d.view_to_region(*dorot(xp[ii], yp[ii], rota),clip=False) )
        dots.append( region.view2d.view_to_region(*dorot(xp[0], yp[0], rota),clip=False) )

        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        gpu.state.blend_set('ALPHA')
        gpu.state.line_width_set(1.5)
        batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": dots})
        shader.uniform_float("color", (1.0, 1.0, 1.0, .1))
        batch.draw(shader)

        gpu.state.line_width_set(1.0)
        gpu.state.blend_set('NONE')


def effects_scene_menu(self, context):
    if G.edit_strip != None:
        self.layout.menu(SVEEffects_Menu.bl_idname, text=SVEEffects_Menu.bl_label)

acceptable_types = ['IMAGE', 'META', 'SCENE', 'MOVIE', 'MOVIECLIP', 'MASK', 'COLOR', 'TEXT' ]
def main_scene_menu(self, context):
    if G.edit_strip == None:
        if context.active_sequence_strip and context.active_sequence_strip.type in acceptable_types:
            self.layout.operator(SVEEffects_OpenEditor.bl_idname, text =SVEEffects_OpenEditor.bl_label)
    else:
        self.layout.operator(SVEEffects_CloseEditor.bl_idname, text =SVEEffects_CloseEditor.bl_label)

handles = []
def add_handle(space, *args):
    draw_handle = space.draw_handler_add(*args) 
    def removefun():
        if 'RNA_HANDLE_REMOVED' not in draw_handle.__repr__(): space.draw_handler_remove( draw_handle , args[2])
    handles.append( removefun )
    
    return removefun

def reinstate():
    G.edit_strip = None
    G.orig_strip = None
    G.strips.clear()
    effectC.all.clear()
    fcurveC.all.clear()
    add_handle(bpy.types.SpaceSequenceEditor, try_def(draw_callback_seq_preview), tuple(), 'PREVIEW', 'POST_PIXEL' )
    
    for scene in bpy.data.scenes:
        if scene.sequence_editor == None: continue
        for strip in scene.sequence_editor.sequences:
            if strip.channel == 2 and sve.strip_source in strip:
                if strip[sve.strip_source] in scene.sequence_editor.sequences_all:
                    G.edit_strip = strip
                    G.orig_strip = scene.sequence_editor.sequences_all[ strip[sve.strip_source] ]

                    if scene.animation_data == None:
                        scene.animation_data_create()
                    if scene.animation_data.action == None:
                        bpy.data.actions.new(scene.name)
                        scene.animation_data.action = bpy.data.actions[scene.name]
                    G.action = scene.animation_data.action
                    

                    for fc in list(G.action.fcurves):
                        if '"%s"'%(G.orig_strip.name) in fc.data_path or '"%s"'%(G.edit_strip.name) in fc.data_path:
                            G.action.fcurves.remove(fc)

                    lock_tempscene()


                    SEQUENCE_EDITOR = get_by_area("SEQUENCE_EDITOR")

                    with bpy.context.temp_override(area=SEQUENCE_EDITOR):
                        for strip0 in scene.sequence_editor.sequences:
                            strip0.select = False
                        G.edit_strip.select = True
                        bpy.ops.sequencer.set_range_to_strips(preview=True)

                    for strip0 in scene.sequence_editor.sequences:
                        add_strip(strip0)
                    fcurveC.recalc_all()
                    return



classes = [
    SEQUENCER_PT_SVE_topforce,
    SEQUENCER_PT_SVEEffects,
    SEQUENCER_PT_SVEEffects_startend,
    SVEEffects_AddEffect,
    SVEEffects_AddEffect_StartEnd,
    SVEEffects_OpenEditor,
    SVEEffects_CloseEditor,
    SVEEffects_Menu,
    SVEEffects_Tester,
    ]

def register():
    for cl in classes:
        bpy.utils.register_class(cl)
    bpy.types.SEQUENCER_MT_editor_menus.append(effects_scene_menu)
    bpy.types.SEQUENCER_MT_editor_menus.append(main_scene_menu)
    bpy.app.timers.register(reinstate, first_interval=0.1, persistent= False)


def unregister():
    for hh in handles: hh()
    handles.clear()
    bpy.types.SEQUENCER_MT_editor_menus.remove(effects_scene_menu)
    bpy.types.SEQUENCER_MT_editor_menus.remove(main_scene_menu)
    for cl in classes:
        bpy.utils.unregister_class(cl)

@bpy.app.handlers.persistent
def loader(file):
    reinstate()

bpy.app.handlers.load_post.append(loader)
