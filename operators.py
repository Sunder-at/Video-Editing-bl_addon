#!/usr/bin/env python3

import bpy
import re
from traceback import format_exc
from .sve_struct import sve, anim_base, modifier_default
from .effect_fcurve import effectC, fcurveC
from .utility import printc, get_by_area, immutable_change, driver_to_zero, get_from_path
from .bpy_ctypes import move_sequence
from .globals import G



def lock_tempscene():
    tempscene = bpy.data.scenes[G.TEMPSCENE]
    bpy.msgbus.clear_by_owner(G.TEMPSCENE)

    ### PROPERTY LOCKING - START
    for strip in tempscene.sequence_editor.sequences_all:
        bpy.msgbus.subscribe_rna(
            key=strip.path_resolve('lock',False),
            owner=tempscene, args=(1,), options={'PERSISTENT',},
            notify=immutable_change(strip, 'lock', True) )

    for channel_name in ['Channel 1','Channel 2']:
        channel = tempscene.sequence_editor.channels[channel_name]
        channel.lock = True
        bpy.msgbus.subscribe_rna(
            key=channel.path_resolve('lock',False),
            owner=tempscene, args=(1,), options={'PERSISTENT',},
            notify=immutable_change(channel, 'lock', True) )
    ### PROPERTY LOCKING - END


    properties = ['transform.offset_x', 'transform.offset_y', 'transform.rotation', 
                  'transform.origin', 'transform.scale_x', 'transform.scale_y', 
                  'use_flip_x', 'use_flip_y', 'crop.max_x', 'crop.max_y', 'crop.min_x', 'crop.min_y', ]
    for strip in tempscene.sequence_editor.sequences_all:
        if strip.type == 'SCENE':
            for prop in properties:
                driver_to_zero(strip, prop.split('.'))
            break

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
        return context.window.scene.name == G.TEMPSCENE and context.active_sequence_strip
    
    def cancel(self, context):
        return

    def execute(self, context):
        for aa in [sve.strip_source, sve.scene_source]:
            if aa not in G.edit_strip: 
                if len(bpy.data.scenes) > 1:
                    context.window.scene = [scene for scene in bpy.data.scenes if scene.name != G.TEMPSCENE][0]
                    bpy.data.scenes.remove(bpy.data.scenes[G.TEMPSCENE])
                    return {'CANCELLED'}
        
        if G.edit_strip[sve.scene_source] not in bpy.data.scenes:
            return {'CANCELLED'}
        orig_scene = bpy.data.scenes[ G.edit_strip[sve.scene_source] ]

        SEQUENCE_EDITOR = get_by_area("SEQUENCE_EDITOR")


        if not G.edit_strip[sve.strip_source] in orig_scene.sequence_editor.sequences:
            for strip in context.scene.sequence_editor.sequences_all:
                strip.select = False
            G.edit_strip.select = True
            with context.temp_override(area=SEQUENCE_EDITOR, selected_sequences= [G.edit_strip]):
                bpy.ops.sequencer.duplicate()
                orig_strip = context.active_sequence_strip
                
            move_sequence(context.scene, orig_scene, orig_strip )
            orig_scene.sequence_editor.active_strip = orig_strip
            orig_scene.sequence_editor.active_strip.name = G.edit_strip[sve.strip_source]
            orig_strip = orig_scene.sequence_editor.active_strip

            if sve.strip_source in orig_strip: del orig_strip[sve.strip_source]
            if sve.scene_source in orig_strip: del orig_strip[sve.scene_source]
        else:
            orig_strip = orig_scene.sequence_editor.sequences[ G.edit_strip[sve.strip_source] ]

        context.window.scene = orig_scene

        orig_strip.lock = False
        orig_strip.mute = False
        orig_strip.channel = orig_strip.channel

        props = orig_strip.id_properties_ensure().to_dict()
        for pp in props:
            if pp[:len(sve.effect_pre)] == sve.effect_pre:
                del orig_strip[pp]

        for _, effect in effectC.all.items():
            orig_strip[sve.effect_pre + effect.name] = stringify_effect(effect, orig_strip.frame_final_start)

        if not orig_scene.animation_data:
            orig_scene.animation_data_create()
        if not orig_scene.animation_data.action:
            orig_scene.animation_data.action = bpy.data.actions.new(orig_scene.name)

        action = orig_scene.animation_data.action

        fcurveC.recalc_all()
        
        for _, fcurve in fcurveC.all.items():
            fc_kfp = fcurve.fcurve.keyframe_points
            fc_mod = fcurve.fcurve.modifiers
            data_path = get_from_path(orig_strip, fcurve.path, lambda base, prop: base.path_from_id(prop))
            ofcurve = action.fcurves.find( data_path )
            if not ofcurve: ofcurve = action.fcurves.new( data_path )
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

        bpy.data.scenes.remove(bpy.data.scenes[G.TEMPSCENE])

        return {'FINISHED'}

class SVEEffects_OpenEditor(bpy.types.Operator):
    """SVEEffects_OpenEditor"""
    bl_idname = "sequencer.sveeffects_open_editor"
    bl_label = "Effects Editor"
    bl_options = {'REGISTER', 'UNDO'}


    @classmethod
    def poll(cls, context):
        return context.window.scene.name != G.TEMPSCENE and context.active_sequence_strip
    
    def cancel(self, context):
        return

    def execute(self, context):
        effectC.all.clear()
        fcurveC.all.clear()
        G.strips.clear()
        G.edit_strip = None
        G.action = None
        
        SEQUENCE_EDITOR = get_by_area("SEQUENCE_EDITOR")
        
        if not SEQUENCE_EDITOR or context.window.scene.name == G.TEMPSCENE: return {'CANCELLED'}

        original_scene = context.window.scene

        sourceseq = context.active_sequence_strip
        with context.temp_override(area=SEQUENCE_EDITOR, selected_sequences= [sourceseq]):
            bpy.ops.sequencer.duplicate()
            G.edit_strip = context.active_sequence_strip

        if original_scene.animation_data and original_scene.animation_data.action:

            path_from_id = G.edit_strip.path_from_id()
            for fcurve in list(original_scene.animation_data.action.fcurves):
                if path_from_id in fcurve.data_path:
                    original_scene.animation_data.action.fcurves.remove(fcurve)


        G.edit_strip.select = False
        original_scene.sequence_editor.active_strip = sourceseq
        sourceseq.select = False

        if G.TEMPSCENE in bpy.data.scenes:
            bpy.data.scenes.remove(bpy.data.scenes[G.TEMPSCENE])
            
        bpy.ops.scene.new(type='EMPTY')
        bpy.data.scenes[-1].name = G.TEMPSCENE
        bpy.data.scenes[G.TEMPSCENE].sequence_editor_create()
        tempscene = bpy.data.scenes[G.TEMPSCENE]
        
        with context.temp_override(area=SEQUENCE_EDITOR):
            sourceseq.mute = True
            bpy.ops.sequencer.scene_strip_add(frame_start=1,scene=original_scene.name)
        context.active_sequence_strip.scene_input = 'SEQUENCER'
        context.active_sequence_strip.lock = True
        
        G.strips[context.active_sequence_strip.as_pointer()] = context.active_sequence_strip
        move_sequence(original_scene, tempscene, G.edit_strip )
        
        context.scene.sequence_editor.active_strip = G.edit_strip
        context.active_sequence_strip.name = sourceseq.name
        context.active_sequence_strip.channel = 2
        context.active_sequence_strip.lock = True
        context.active_sequence_strip.mute = False
        G.edit_strip = context.scene.sequence_editor.active_strip
        G.strips[G.edit_strip.as_pointer()] = G.edit_strip

        lock_tempscene()
            
        with context.temp_override(area=SEQUENCE_EDITOR):
            for strip in tempscene.sequence_editor.sequences_all:
                strip.select = False
            G.edit_strip.select = True
            bpy.ops.sequencer.set_range_to_strips(preview=True)

        tempscene.animation_data_create()
        if G.TEMPACTION in bpy.data.actions:
            bpy.data.actions.remove(bpy.data.actions[G.TEMPACTION])

        G.action = bpy.data.actions.new(G.TEMPACTION)
        G.action.frame_start = G.edit_strip.frame_final_start
        G.action.frame_end = G.edit_strip.frame_final_end
        tempscene.animation_data.action = G.action

        props = sourceseq.id_properties_ensure().to_dict()
        for pp in props:
            if sve.effect_pre in pp:
                parsed = parse_effect(props[pp], G.edit_strip.frame_final_start)
                name = pp[len(sve.effect_pre):]
                if parsed:
                    effectC(name, tempscene, parsed)
                    
        
        props = G.edit_strip.id_properties_ensure().to_dict()
        for pp in props:
            if pp[:len(sve.effect_pre)] == sve.effect_pre:
                del G.edit_strip[pp]
        G.edit_strip[sve.strip_source] = sourceseq.name
        G.edit_strip[sve.scene_source] = original_scene.name
        fcurveC.recalc_all()
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
        try:
            # def funcs():
            #     printc('thread1')
            #     sleep(3)
            #     printc('thread2')
            # target = bpy.data.scenes['Scene'].sequence_editor.sequences_all["Color"]  
            # printc('effectC.all ' + str(effectC.all))
            # printc('fcurveC.all ' + str(fcurveC.all))
            # printc('G.strips ' + str(G.strips))
            # printc('G.edit_strip ' + str(G.edit_strip))
            # printc('G.action ' + str(G.action))
            # printc('G.TEMPSCENE ' + str(G.TEMPSCENE))
            # if sve.startend in  context.active_sequence_strip:
            # effect = context.active_sequence_strip
            
            # printc(str(context.area))
            # bpy.app.timers.register(lambda: printc(str(context.area)), first_interval=3, persistent= False)
            printc(G.dir)
            pass
        except Exception as exc:
            printc(str(exc))
            printc(str(format_exc()))
            

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
        if G.edit_strip == None or G.action == None or self.effect_type not in anim_base.all:
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
            layout.operator(SVEEffects_AddEffect.bl_idname, text = tt).effect_type = tt
        # layout.operator(SVEEffects_Tester.bl_idname, text=SVEEffects_Tester.bl_label)

    @classmethod
    def poll(cls, context):
        return True
