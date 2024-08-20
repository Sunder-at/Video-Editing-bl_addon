#!/usr/bin/env python3

import bpy
import re
from traceback import format_exc
from .sve_struct import sve, anim_base, modifier_default
from .effect_fcurve import effectC, fcurveC
from .utility import printc, get_by_area, immutable_change, driver_to_zero, \
    get_from_path, create_none_img, add_driver, remove_driver, fcurve_paths
from .globals import G



def lock_tempscene():
    # tempscene = bpy.data.scenes[G.TEMPSCENE]
    scene = bpy.context.scene
    bpy.msgbus.clear_by_owner(scene)

    ### PROPERTY LOCKING - START
    for strip in scene.sequence_editor.sequences:
        bpy.msgbus.subscribe_rna(
            key=strip.path_resolve('lock',False),
            owner=scene, args=(1,), options={'PERSISTENT',},
            notify=immutable_change(strip, 'lock', True) )

    for channel_name in ['Channel 1','Channel 2']:
        channel = scene.sequence_editor.channels[channel_name]
        channel.lock = True
        bpy.msgbus.subscribe_rna(
            key=channel.path_resolve('lock',False),
            owner=scene, args=(1,), options={'PERSISTENT',},
            notify=immutable_change(channel, 'lock', True) )
    ### PROPERTY LOCKING - END


    properties = ['transform.offset_x', 'transform.offset_y', 'transform.rotation', 
                  'transform.origin', 'transform.scale_x', 'transform.scale_y', 
                  'use_flip_x', 'use_flip_y', 'crop.max_x', 'crop.max_y', 'crop.min_x', 'crop.min_y', ]
    for strip in scene.sequence_editor.sequences:
        if strip.channel == 1:
            for prop in properties:
                driver_to_zero(strip, prop.split('.'))
            break

    def notify(*args, **kwargs):
        if G.orig_strip:
            G.orig_strip.transform.offset_x += 0.0
            G.orig_strip.transform.offset_y += 0.0
    
    bpy.msgbus.clear_by_owner(G.edit_strip)

    for ppath in fcurve_paths:
        bpy.msgbus.subscribe_rna(
            key=get_from_path(G.edit_strip, ppath, lambda base,prop: base.path_resolve(prop, False) ),
            owner=G.edit_strip, args=(1,), options={'PERSISTENT',},
            notify=notify )


def stringify_effect(effect: effectC, offset: int):
    string = 's' + str(effect.start - offset) + \
             'e' + str(effect.end   - offset) + ';' + effect.type + ';'

    if effect.type not in anim_base.all: return ''
    type_class: anim_base = anim_base.all[effect.type]
    return string + type_class.to_string(effect)

def parse_effect(string: str, offset: int):
    rframe = r"s(?P<start>-?\d+)e(?P<end>-?\d+);(?P<type>[^;]*);"
    
    match = re.match(rframe, string)
    mdict = {}

    if match:
        mdict = match.groupdict()
    else:
        return None
    mdict['start'] = int(mdict['start']) + offset
    mdict['end'] = int(mdict['end']) + offset
    if mdict['type'] not in anim_base.all:
        return None
    type_class: anim_base = anim_base.all[mdict['type']]
    mdict['props'] = type_class.parse(string[match.end():])
    
    return mdict




class SVEEffects_AddEffect_StartEnd(bpy.types.Operator):
    """animate_transform start"""
    bl_idname = "sequencer.sveeffects_animate_transform_startend"
    bl_label = "Start/End"
    bl_options = {'REGISTER', 'UNDO'}
    startend: bpy.props.IntProperty(
        name="Start/End",
        min=0, max=1,
        default=0,
    )

    @classmethod
    def poll(cls, context):
        strip = context.active_sequence_strip
        return strip and strip.as_pointer() in effectC.all
    
    def cancel(self, context):
        return

    def execute(self, context):
        strip = context.active_sequence_strip
        effect: 'effectC' = effectC.all[strip.as_pointer()]
        
        if effect.effect[sve.startend] != self.startend:
            effect.effect[sve.startend] = self.startend

            for fc in effect.fcurves:
                val0, val1 = effect.get_values(fc.sve_path)
                effect.set_values(fc.sve_path, val1, val0)

        return {'FINISHED'}

class SEQUENCER_PT_SVEEffects_startend(bpy.types.Menu):
    bl_idname = G.SEQUENCER_PT_SVEEffects_startend
    bl_label = "Start/End"

    def draw(self, context):
        layout = self.layout
        for index, type in enumerate(['Start', 'End']):
            row = layout.row()
            row.enabled = context.active_sequence_strip[sve.startend] != index
            row.operator(SVEEffects_AddEffect_StartEnd.bl_idname, text=type).startend = index


class SVEEffects_CloseEditor(bpy.types.Operator):
    """SVEEffects_CloseEditor"""
    bl_idname = "sequencer.sveeffects_close_editor"
    bl_label = "Save Changes"
    bl_options = {'REGISTER', 'UNDO'}


    @classmethod
    def poll(cls, context):
        # return context.window.scene.name == G.TEMPSCENE
        return G.edit_strip != None and sve.scene_source in G.edit_strip and G.edit_strip[sve.scene_source] == context.scene.name
    
    def cancel(self, context):
        return

    def execute(self, context):
        for aa in [sve.strip_source, sve.scene_source]:
            if aa not in G.edit_strip:
                return {'CANCELLED'}
        
        scene = context.scene
        if G.edit_strip[sve.scene_source] != scene.name:
            return {'CANCELLED'}

        SEQUENCE_EDITOR = get_by_area("SEQUENCE_EDITOR")
        bpy.msgbus.clear_by_owner(G.edit_strip)


        for ppath in fcurve_paths:
            remove_driver(G.orig_strip, ppath)
            
        props = G.orig_strip.id_properties_ensure().to_dict()
        for pp in props:
            if pp[:len(sve.effect_pre)] == sve.effect_pre:
                del G.orig_strip[pp]

        for _, effect in effectC.all.items():
            G.orig_strip[sve.effect_pre + effect.name] = stringify_effect(effect, G.orig_strip.frame_final_start)

        fcurveC.recalc_all()
        
        for _, fcurve in fcurveC.all.items():
            fc_kfp = fcurve.fcurve.keyframe_points
            fc_mod = fcurve.fcurve.modifiers
            data_path = get_from_path(G.orig_strip, fcurve.path, lambda base, prop: base.path_from_id(prop))
            ofcurve = G.action.fcurves.find( data_path )
            if not ofcurve: ofcurve = G.action.fcurves.new( data_path )
            ofc_kfp = ofcurve.keyframe_points
            ofc_mod = ofcurve.modifiers
            ofc_kfp.clear()
            for modf in list(ofc_mod):
                ofc_mod.remove(modf)

            ofc_kfp.add( len(fc_kfp) )

            for ii in range(len(fc_kfp)):
                ofc_kfp[ii].co = fc_kfp[ii].co
                ofc_kfp[ii].handle_left = fc_kfp[ii].handle_left
                ofc_kfp[ii].handle_right = fc_kfp[ii].handle_right
            
            ofc_kfp.sort()

            for modf in fc_mod:
                newmod = ofc_mod.new(modf.type)
                modifier_default(newmod, modf)
                newmod.frame_start = modf.frame_start
                newmod.frame_end = modf.frame_end

        G.edit_strip = None
        G.orig_strip = None
        G.action = None
        bpy.msgbus.clear_by_owner(scene)
        for channel_name in ['Channel 1','Channel 2']:
            channel = scene.sequence_editor.channels[channel_name]
            channel.lock = False
        for seq in list(scene.sequence_editor.sequences):
            if seq.channel == 1:
                seq.select = True
                scene.sequence_editor.active_strip = seq
            else:
                for fc in list(scene.animation_data.drivers):
                    if 'sequences_all["%s"]'%(seq.name) in fc.data_path:
                        scene.animation_data.drivers.remove(fc)
                scene.sequence_editor.sequences.remove(seq)
        

        for fc in list(scene.animation_data.drivers):
            if 'sequences_all["%s"]'%(scene.sequence_editor.active_strip.name) in fc.data_path:
                scene.animation_data.drivers.remove(fc)

        with context.temp_override(area=SEQUENCE_EDITOR):
            bpy.ops.sequencer.meta_separate()
            bpy.ops.anim.previewrange_clear()
        
        for seq in scene.sequence_editor.sequences:
            seq.select = False

        return {'FINISHED'}

class SVEEffects_OpenEditor(bpy.types.Operator):
    """SVEEffects_OpenEditor"""
    bl_idname = "sequencer.sveeffects_open_editor"
    bl_label = "Effects Editor"
    bl_options = {'REGISTER', 'UNDO'}


    @classmethod
    def poll(cls, context):
        return context.active_sequence_strip and G.edit_strip == None
    
    def cancel(self, context):
        return

    def execute(self, context):
        effectC.all.clear()
        fcurveC.all.clear()
        G.strips.clear()

        SEQUENCE_EDITOR = get_by_area("SEQUENCE_EDITOR")

        scene = context.window.scene
        sequences = scene.sequence_editor.sequences
        G.orig_strip = scene.sequence_editor.active_strip

        for strip in sequences:
            strip.select = True

        with context.temp_override(area=SEQUENCE_EDITOR):
            bpy.ops.sequencer.meta_make()
            background = scene.sequence_editor.active_strip
            background.channel = 1

        filepath = create_none_img(G.orig_strip)
        G.edit_strip = sequences.new_image(G.orig_strip.name + '_proxy', filepath, 2, G.orig_strip.frame_final_start)
        G.edit_strip.channel = 2
        G.edit_strip.frame_final_duration = G.orig_strip.frame_final_duration

        G.strips[background.as_pointer] = background
        G.strips[G.edit_strip.as_pointer] = G.edit_strip

        if scene.animation_data == None:
            scene.animation_data_create()
        if scene.animation_data.action == None:
            bpy.data.actions.new(scene.name)
            scene.animation_data.action = bpy.data.actions[scene.name]
        G.action = scene.animation_data.action
        for fc in list(G.action.fcurves):
            if '"%s"'%(G.orig_strip.name) in fc.data_path:
                G.action.fcurves.remove(fc)

        for ppath in fcurve_paths:
            srcval = get_from_path(G.orig_strip, ppath, lambda base, prop: getattr(base, prop))
            get_from_path(G.edit_strip, ppath, lambda base, prop: setattr(base, prop, srcval))
            add_driver(G.orig_strip, ppath, ppath)

        lock_tempscene()
            
        with context.temp_override(area=SEQUENCE_EDITOR):
            for strip in scene.sequence_editor.sequences_all:
                strip.select = False
            G.edit_strip.select = True
            bpy.ops.sequencer.set_range_to_strips(preview=True)

        props = G.orig_strip.id_properties_ensure().to_dict()
        for pp in props:
            if sve.effect_pre in pp:
                parsed = parse_effect(props[pp], G.edit_strip.frame_final_start)
                name = pp[len(sve.effect_pre):]
                if parsed:
                    effectC(name, scene, parsed)
                    
        G.edit_strip[sve.strip_source] = G.orig_strip.name
        G.edit_strip[sve.scene_source] = scene.name
        fcurveC.recalc_all()

        for seq in scene.sequence_editor.sequences:
            seq.select = False

        return {'FINISHED'}


class SVEEffects_Tester(bpy.types.Operator):
    """Tester"""
    bl_idname = "sequencer.sveeffects_tester"
    bl_label = "tester"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return bool(context.active_sequence_strip)
    
    def cancel(self, context):
        return

    def execute(self, context):
        if context.active_sequence_strip == None: return {'CANCELLED'}

        # meta = context.scene.sequence_editor.sequences.new_meta('test', 4, context.scene.frame_current)
        # srcscene = bpy.data.scenes[G.edit_strip[sve.scene_source]]
        # to_meta_sequence(srcscene, meta)
        # try:
        #     # target = bpy.data.scenes['Scene'].sequence_editor.sequences_all["Color"]  
        #     # printc('effectC.all ' + str(effectC.all))
        #     # printc('fcurveC.all ' + str(fcurveC.all))
        #     # printc('G.strips ' + str(G.strips))
        #     # printc('G.edit_strip ' + str(G.edit_strip))
        #     # printc('G.action ' + str(G.action))
        #     # printc('G.TEMPSCENE ' + str(G.TEMPSCENE))
        #     # if sve.startend in  context.active_sequence_strip:
        #     # effect = context.active_sequence_strip
            
        #     # printc(str(context.area))
        #     # bpy.app.timers.register(lambda: printc(str(context.area)), first_interval=3, persistent= False)
        #     printc(G.dir)
        #     pass
        # except Exception as exc:
        #     printc(str(exc))
        #     printc(str(format_exc()))
            

        return {'FINISHED'}
    
class SVEEffects_AddEffect(bpy.types.Operator):
    """animate_transform"""
    bl_idname = "sequencer.sveeffects_animate_transform"
    bl_label = "animate_transform"
    bl_options = {'REGISTER', 'UNDO'}
    effect_type: bpy.props.StringProperty(
        name="Type",
    )

    @classmethod
    def poll(cls, context):
        return True
    
    def cancel(self, context):
        return
    
    def execute(self, context):
        if G.edit_strip == None or self.effect_type not in anim_base.all:
            return {'CANCELLED'}
        for sequence in context.scene.sequence_editor.sequences:
            sequence.select = False
        
        name = anim_base.all[self.effect_type].name
        effectC(name, context.scene, {'type': self.effect_type})
        fcurveC.recalc_all()

        return {'FINISHED'}
    

class SEQUENCER_PT_SVE_topforce(bpy.types.Panel):
    bl_label = "topforce"
    bl_space_type = 'SEQUENCE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Strip"
    bl_order = 0
    bl_options = set(['HIDE_HEADER'])

    @staticmethod
    def has_sequencer(context):
        return (context.space_data.view_type in {'SEQUENCER', 'SEQUENCER_PREVIEW'})

    @classmethod
    def poll(cls, context):
        strip = context.active_sequence_strip
        return strip and strip.as_pointer() in effectC.all
    
    def draw(self, context):
        pass

class SEQUENCER_PT_SVEEffects(bpy.types.Panel):
    bl_label = "Effect Transform"
    bl_space_type = 'SEQUENCE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Strip"
    bl_order = 0
    bl_parent_id = SEQUENCER_PT_SVE_topforce.__qualname__
    bl_options = set()
    
    @staticmethod
    def has_sequencer(context):
        return (context.space_data.view_type in {'SEQUENCER', 'SEQUENCER_PREVIEW'})

    @classmethod
    def poll(cls, context):
        strip = context.active_sequence_strip
        return strip and strip.as_pointer() in effectC.all

    def draw(self, context):
        effect = context.active_sequence_strip
        effectT: anim_base = effectC.all[effect.as_pointer()].atype

        layout = self.layout
        layout.use_property_split = True

        effectT.layout(layout, effect)


class SVEEffects_Menu(bpy.types.Menu):
    bl_idname = "SEQUENCER_MT_sve_menu_effects"
    bl_label = "Effects"
    bl_owner_id = "SEQUENCER_MT_image"

    def draw(self, context):
        layout = self.layout
        for tt in anim_base.all:
            layout.operator(SVEEffects_AddEffect.bl_idname, text = anim_base.all[tt].name).effect_type = tt
        # layout.operator(SVEEffects_Tester.bl_idname, text=SVEEffects_Tester.bl_label)

    @classmethod
    def poll(cls, context):
        return True
