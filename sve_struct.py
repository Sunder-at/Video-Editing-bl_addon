#!/usr/bin/env python3

import bpy
import re

from typing import Callable
from .utility import get_from_path, add_driver, remove_driver,  create_none_img
from .globals import G

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from effect_fcurve import effectC

class modifier_default:
    base: dict[str] = {
        'blend_in' : 0.0,
        'blend_out' : 0.0,
        'influence' : 1.0,
        'mute' : False,
        'use_influence' : False,
        'use_restricted_range' : True,
    }
    _type: dict[str, dict] = {
        'NULL' : {},
        'GENERATOR' : {
            'coefficients':  [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            'mode':  'POLYNOMIAL',
            'poly_order':  0,
            'use_additive':  False,
        },
        'FNGENERATOR' : {
            'amplitude': 0.0,
            'function_type': 'SIN',
            'phase_multiplier': 0.0,
            'phase_offset': 0.0,
            'use_additive': False,
            'value_offset': 0.0,
        },
        'ENVELOPE' : {
            # control_points FModifierEnvelopeControlPoints bpy_prop_collection of FModifierEnvelopeControlPoint, (readonly)
            'default_max': 0.0,
            'default_min': 0.0,
            'reference_value': 0.0,
        },
        'CYCLES' : {
            'cycles_after': 0,
            'cycles_before':  0,
            'mode_after': 'NONE',
            'mode_before': 'NONE',
        },
        'NOISE' : {
            'blend_type': 'REPLACE',
            'depth': 0,
            'offset': 0.0,
            'phase': 0.0,
            'scale': 0.0,
            'strength': 0.0,
        },
        'LIMITS' : {
            'max_x': 0.0,
            'max_y': 0.0,
            'min_x': 0.0,
            'min_y': 0.0,
            'use_max_x': False,
            'use_max_y': False,
            'use_min_x': False,
            'use_min_y': False,
        },
        'STEPPED' : {
            'frame_end': 0.0,
            'frame_offset': 0.0,
            'frame_start': 0.0,
            'frame_step': 0.0,
            'use_frame_end': False,
            'use_frame_start': False,
        },
    }
    def __call__(self, modifier, def_props: dict | object = {}):
        if isinstance(def_props, dict):
            _type = def_props.get('type', 'NULL')
            if _type not in self._type: return
            for pp, default in self.base.items():
                setattr(modifier, pp, def_props.get(pp, default) )
            for pp, default in self._type[_type].items():
                setattr(modifier, pp, def_props.get(pp, default) )
        else:
            _type = getattr(def_props, 'type', 'NULL')
            if _type not in self._type: return
            for pp, default in self.base.items():
                setattr(modifier, pp, getattr(def_props, pp, default) )
            for pp, default in self._type[_type].items():
                setattr(modifier, pp, getattr(def_props, pp, default) )
            
modifier_default = modifier_default()

class typeC:
    class _base:
        @staticmethod
        def to_str(*args) -> str: return ''
        @staticmethod
        def to_type(s: str): return None
        @staticmethod
        def setter(effect, prop:str, default: Callable, *args): return
        @staticmethod
        def getter(effect, prop:str) -> tuple: return tuple()
        # def getter_to_str(_, effect: 'effectC', prop:str) -> str: return ''
        def getter_to_str(self, effect: 'effectC', prop:str) -> str: 
            return self.to_str( *self.getter(effect, prop) )

    class use(_base):
        @staticmethod
        def to_str(*args): 
            return ','.join([str(int(a)) for a in args])
        @staticmethod
        def to_type(s: str): 
            return [s0 == '1' for s0 in s.split(',')]
        @staticmethod
        def setter(effect, prop:str, default: Callable, *args: bool):
            match len(args):
                case 0:
                    effect[prop] = default(prop)
                case 1:        
                    effect[prop] = args[0]
        @staticmethod
        def getter(effect: 'effectC', prop:str) -> tuple:
            return (effect.effect[prop],)
        # def getter_to_str(effect: 'effectC', prop:str) -> str:
        #     return sve.typeC.getter_to_str(effect, prop, __class__)
    use = use()

    class dualfloat(_base):
        @staticmethod
        def to_str(*args): 
            return ','.join([str(a) for a in args])
        @staticmethod
        def to_type(s: str): 
            return [float(s0) for s0 in s.split(',')]
        @staticmethod
        def setter(effect, prop:str, default: Callable, *args: float):
            match len(args):
                case 0:
                    default0 = default(prop)
                    effect[prop] = default0
                    get_from_path(effect, sve.props[prop].path, lambda base, prop: setattr(base, prop, default0) )
                case 1:
                    effect[prop] = args[0]
                    get_from_path(effect, sve.props[prop].path, lambda base, prop: setattr(base, prop, args[0]) )
                case 2:
                    effect[prop] = args[0]
                    get_from_path(effect, sve.props[prop].path, lambda base, prop: setattr(base, prop, args[1]) )
        @staticmethod
        def getter(effect: 'effectC', prop:str) -> tuple:
            return effect.get_values( prop )
        # def getter_to_str(effect: 'effectC', prop:str) -> str:
        #     return sve.typeC.getter_to_str(effect, prop, __class__)
    dualfloat = dualfloat()

    class float(_base):
        @staticmethod
        def to_str(*args): 
            return str(args[0])
        @staticmethod
        def to_type(s: str): 
            return [float(s0) for s0 in s.split(',')]
        @staticmethod
        def setter(effect, prop:str, default: Callable, *args: bool):
            match len(args):
                case 0:
                    effect[prop] = default(prop)
                case 1:        
                    effect[prop] = args[0]
        @staticmethod
        def getter(effect: 'effectC', prop:str) -> tuple:
            return [effect.effect[prop]]
        # def getter_to_str(effect: 'effectC', prop:str) -> str:
        #     return sve.typeC.getter_to_str(effect, prop, __class__)
    float = float()
typeC = typeC()

class sve:
    startend = 'startend'
    offset_x = 'offset_x'
    offset_y = 'offset_y'
    scale_x = 'scale_x'
    scale_y = 'scale_y'
    rotation = 'rotation'
    opacity = 'opacity'
    use_offset = 'use_offset'
    use_scale = 'use_scale'
    use_rotation = 'use_rotation'
    use_opacity = 'use_opacity'
    noise_erraticness = 'noise_erraticness'
    noise_radius = 'noise_radius'
    noise_seed = 'noise_seed'

    effect_pre = 'sveeffect_'
    strip_source = 'strip_source'
    scene_source = 'scene_source'
    type = 'type'
    prop_use: list[str]
    prop_path: list[str]
    props: dict[str, 'propC']
    types: list[str]

    class propC:
        id_properties: dict = None
        atype: typeC._base = None
        path: list[str] = None
        use: list[str] = None
        def __init__(self, id_properties=None, atype=None, path=None, use=None) -> None:
            self.id_properties = id_properties
            self.atype = atype
            self.path = path
            self.use = use
    @staticmethod
    def getattr(base, prop, default):
        if prop in base:
            return base[prop]
        else:
            return default

    def __init__(self) -> None:
        self.props = {
            sve.startend: self.propC(
                id_properties = {'default': 0, 'min': 0, 'max': 1, },
                atype = typeC.dualfloat,
                path = ['transform', 'offset_x', ],
            ),
            sve.offset_x: self.propC(
                id_properties = {'subtype': 'PIXEL', },
                atype = typeC.dualfloat,
                path = ['transform', 'offset_x', ],
            ),
            sve.offset_y: self.propC(
                id_properties = {'subtype': 'PIXEL', },
                atype = typeC.dualfloat,
                path = ['transform', 'offset_y', ],
            ),
            sve.scale_x: self.propC(
                id_properties = {'subtype': 'NONE', },
                atype = typeC.dualfloat,
                path = ['transform', 'scale_x', ],
            ),
            sve.scale_y: self.propC(
                id_properties = {'subtype': 'NONE', },
                atype = typeC.dualfloat,
                path = ['transform', 'scale_y', ],
            ),
            sve.rotation: self.propC(
                id_properties = {'subtype': 'ANGLE', },
                atype = typeC.dualfloat,
                path = ['transform', 'rotation', ],
            ),
            sve.opacity: self.propC(
                id_properties = {'subtype': 'PERCENTAGE', 'min': 0.0, 'max': 1.0, 'default': 1.0},
                atype = typeC.dualfloat,
                path = ['blend_alpha', ],
            ),
            sve.use_offset: self.propC(
                id_properties = {'subtype': 'NONE', },
                atype = typeC.use,
                use = [sve.offset_x, sve.offset_y, ],
            ),
            sve.use_scale: self.propC(
                id_properties = {'subtype': 'NONE', },
                atype = typeC.use,
                use = [sve.scale_x, sve.scale_y, ],
            ),
            sve.use_rotation: self.propC(
                id_properties = {'subtype': 'NONE', },
                atype = typeC.use,
                use = [sve.rotation, ],
            ),
            sve.use_opacity: self.propC(
                id_properties = {'subtype': 'NONE', },
                atype = typeC.use,
                use = [sve.opacity, ],
            ),
            sve.noise_erraticness: self.propC(
                id_properties= {'subtype': 'PERCENTAGE', 'min': 0.0, 'max': 1.0},
                atype = typeC.float,
            ),
            sve.noise_radius: self.propC(
                id_properties= {'subtype': 'NONE', 'min': 0.0, 'max': 1000.0, 'step': 100.0},
                atype = typeC.float,
            ),
            sve.noise_seed: self.propC(
                id_properties= {'subtype': 'PERCENTAGE', 'min': 0.0, 'max': 1.0},
                atype = typeC.float,
            ),
        }
        def prop_filter(props_prop: str):
            return [pp for pp in self.props if getattr(self.props[pp], props_prop)]
        self.prop_use = prop_filter('use')
        self.prop_path = prop_filter('path')
sve = sve()


    
class anim_base:
    props: list[str]
    defaults: dict[str]
    prop_update: dict[str, Callable]
    all: dict[str, 'anim_base'] = {}
    name: str = 'anim_base'

    def __init__(self) -> None:
        self.all[self.__class__.__name__] = self
        
    def new_effectstrip(self, sequences, name, channel, frame_start): return None
    def layout(self, layout): return None
    def modifier(self, effect): return None
    def init(self, effect: 'effectC'): return


    def default(self, _type):
        if _type in self.defaults:
            return self.defaults[_type]
        elif sve.props[_type].path:
            return get_from_path(G.edit_strip, sve.props[_type].path, lambda base, prop: getattr(base, prop) )
        return None
    
    def to_string(self, effect: 'effectC') -> str:
        string = ''
        for prop in self.props:
            string += prop + ':' + sve.props[prop].atype.getter_to_str(effect, prop) + ';'
        return string
    
    def parse(self, string: str) -> dict:
        rprop = r"(?P<prop>\w+):(?P<value>[^;]*);"
        dd = {}
        iter = re.finditer(rprop, string)
        for match in iter:
            prop = match.group('prop')
            value = match.group('value')
            to_type = sve.props[prop].atype.to_type
            dd[prop] = to_type(value)
        return dd
    
    def to_effect(self, effect_strip, props: dict = {}):
        for prop in self.props:
            sve.props[prop].atype.setter(effect_strip, prop, self.default, *props.get(prop, []) )
            effect_strip.id_properties_ui(prop).update(**sve.props[prop].id_properties)
    
    def to_modifier(self, modifier, effect: 'effectC'):
        modif_prop = self.modifier(effect)
        if modif_prop:
            modifier_default(modifier, modif_prop)

    @staticmethod
    def sve_prop_change(prop):
        def prop_change(effect: 'effectC', value):
            for fc in effect.fcurves:
                if fc.sve_path == prop:
                    fc.keyframes_value_recalc()
        return prop_change


class anim_transform(anim_base):
    def __init__(self):
        super().__init__()
        self.name = 'Transform'
        self.props = [
            sve.startend, sve.offset_x, sve.offset_y, 
            sve.scale_x, sve.scale_y, sve.rotation, 
            sve.use_offset, sve.use_scale, sve.use_rotation, ]
        self.defaults = {
            sve.startend: 0,
            sve.use_offset: True,
            sve.use_scale: False,
            sve.use_rotation: False,
        }

        def sve_use_update(use: str):
            paths = sve.props[use].use
            def updater(effect: 'effectC', value):
                if value:
                    for path in paths:
                        remove_driver(effect.effect, sve.props[path].path)
                        remove_driver(effect.effect, ['["%s"]'%(path)])
                        effect.add_to_fcurve(path)
                else:
                    for path in paths:
                        effect.remove_from_fcurve(path)
                        add_driver(effect.effect, sve.props[path].path, sve.props[path].path)
                        add_driver(effect.effect, ['["%s"]'%(path)], sve.props[path].path)
            return updater
        self.prop_update = {
            sve.use_offset: sve_use_update(sve.use_offset),
            sve.use_scale: sve_use_update(sve.use_scale),
            sve.use_rotation: sve_use_update(sve.use_rotation),
            sve.offset_x: self.sve_prop_change(sve.offset_x), 
            sve.offset_y: self.sve_prop_change(sve.offset_y), 
            sve.scale_x: self.sve_prop_change(sve.scale_x), 
            sve.scale_y: self.sve_prop_change(sve.scale_y), 
            sve.rotation: self.sve_prop_change(sve.rotation), 
        }
    
    def to_string(self, effect: 'effectC') -> str:
        string = ''
        for use in [sve.use_offset, sve.use_scale, sve.use_rotation]:
            string += use + ':' + sve.props[use].atype.getter_to_str(effect, use) + ';'
            if effect.effect[use]:
                for prop in sve.props[use].use:
                    string += prop + ':' + sve.props[prop].atype.getter_to_str(effect, prop) + ';'
        return string
    def layout(self, layout, effect):

        layout_prop = {
            sve.offset_x: {'text':'Position X'},
            sve.offset_y: {'text':'Y'},
            sve.scale_x: {'text':'Scale X'},
            sve.scale_y: {'text':'Y'},
            sve.rotation: {'text':'Rotation'},
        }
        def l0(_col, _apath:str):
            args0, args1 = get_from_path(effect, sve.props[_apath].path, lambda base, prop: (base, prop,) )
            _col.prop(args0, args1, **layout_prop[_apath])

        def l1(_col, _apath:str):
            _col.prop(effect, '["%s"]'%(_apath), **layout_prop[_apath])

        if effect[sve.startend] == 0:
            layout_0, layout_1 = l0 , l1
        else:
            layout_1, layout_0 = l0 , l1

        col = layout.column(align=True)
        row = col.row(align=True)
        row.label(text='Editing')
        row.menu(G.SEQUENCER_PT_SVEEffects_startend, text= (['Start','End'])[effect[sve.startend]] )
        # row.menu_contents(G.SEQUENCER_PT_SVEEffects_startend)

        col = layout.column(align=True)
        col.prop(effect, '["%s"]'%(sve.use_offset), text='Use offset')
        if effect[sve.use_offset]:
            col0 = layout.column(align=True)
            col0.label(text='Offset Start')
            layout_0(col0, sve.offset_x)
            layout_0(col0, sve.offset_y)
            col0.label(text='Offset End')
            layout_1(col0, sve.offset_x)
            layout_1(col0, sve.offset_y)

        col.prop(effect, '["%s"]'%(sve.use_scale), text='Use scale')
        if effect[sve.use_scale]:
            col0 = layout.column(align=True)
            col0.label(text='Scale Start')
            layout_0(col0, sve.scale_x)
            layout_0(col0, sve.scale_y)
            col0.label(text='Scale End')
            layout_1(col0, sve.scale_x)
            layout_1(col0, sve.scale_y)

        col.prop(effect, '["%s"]'%(sve.use_rotation), text='Use rotation')
        if effect[sve.use_rotation]:
            col0 = layout.column(align=True)
            col0.label(text='Rotation Start')
            layout_0(col0, sve.rotation)
            col0.label(text='Rotation End')
            layout_1(col0, sve.rotation)
    
    def new_effectstrip(self, sequences, name, channel, frame_start):
        filepath = create_none_img()
        effectstrip = sequences.new_image(name, filepath, channel, frame_start)
        effectstrip.channel = channel
        return effectstrip
anim_transform = anim_transform()

class anim_shake(anim_base):
    def __init__(self):
        super().__init__()
        self.name = 'Shake'
        self.props = [
            sve.use_offset, sve.use_scale, 
            sve.use_rotation, sve.use_opacity, 
            sve.noise_erraticness, sve.noise_radius, sve.noise_seed]
        self.defaults = {
            sve.use_offset: True,
            sve.use_scale: False,
            sve.use_rotation: False,
            sve.use_opacity: False,
            sve.noise_erraticness: 0.5,
            sve.noise_radius: 10.0,
            sve.noise_seed: 0.5,
        }
        def sve_use_update(use: str):
            paths = sve.props[use].use
            def updater(effect: 'effectC', value):
                if value:
                    for path in paths:
                        effect.add_to_fcurve(path)
                else:
                    for path in paths:
                        effect.remove_from_fcurve(path)
            return updater
        def update(effect: 'effectC', value):
            for fc in effect.fcurves:
                fc.modifiers_value_recalc()

        self.prop_update = {
            sve.use_offset: sve_use_update(sve.use_offset),
            sve.use_scale: sve_use_update(sve.use_scale),
            sve.use_rotation: sve_use_update(sve.use_rotation),
            sve.use_opacity: sve_use_update(sve.use_opacity),
            sve.noise_erraticness: update,
            sve.noise_radius: update,
            sve.noise_seed: update,
        }

    def layout(self, layout, effect):
        col = layout.column(align=True)
        col.prop(effect, '["%s"]'%(sve.use_offset), text='Use offset')
        col.prop(effect, '["%s"]'%(sve.use_scale), text='Use scale')
        col.prop(effect, '["%s"]'%(sve.use_rotation), text='Use rotation')
        col.prop(effect, '["%s"]'%(sve.use_opacity), text='Use opacity')

        col = layout.column(align=True)
        col.prop(effect, '["%s"]'%(sve.noise_erraticness), text='Erraticness')
        col = layout.column(align=True)
        col.prop(effect, '["%s"]'%(sve.noise_radius), text='Radius')
        col = layout.column(align=True)
        col.prop(effect, '["%s"]'%(sve.noise_seed), text='Seed')


    def new_effectstrip(self, sequences, name, channel, frame_start): 
        # effectstrip = sequences.new_effect(name, 'ADJUSTMENT', channel, frame_start, frame_end = frame_start+1)
        # effectstrip.channel = channel
        # return effectstrip
        filepath = create_none_img()
        effectstrip = sequences.new_image(name, filepath, channel, frame_start)
        effectstrip.channel = channel

        return effectstrip
    
    def init(self, effect: 'effectC'): 
        for path in [sve.offset_x, sve.offset_y, sve.scale_x, sve.scale_y, sve.rotation]:
            add_driver(effect.effect, sve.props[path].path, sve.props[path].path)

    
    def modifier(self, effect: 'effectC'):
        return {
            'type': 'NOISE',
            'scale': 0.5 + 20.0 * (1.0 - sve.getattr(effect.effect, sve.noise_erraticness, 0.5)),
            'strength': sve.getattr(effect.effect, sve.noise_radius, 10.0),
            'offset': G.set_random * sve.getattr(effect.effect, sve.noise_seed, 0.5) * 1000.0,
        }
anim_shake = anim_shake()

class anim_opacity(anim_base):
    def __init__(self):
        super().__init__()
        self.name = 'Opacity'
        self.props = [
            sve.startend, sve.opacity, sve.use_opacity,]
        self.defaults = {
            sve.startend: 0,
            sve.use_opacity: True,
        }
        def sve_use_opacity(effect: 'effectC', value):
            if value:
                effect.add_to_fcurve(sve.opacity)
            else:
                effect.remove_from_fcurve(sve.opacity)

        self.prop_update = {
            sve.use_opacity: sve_use_opacity,
            sve.opacity: self.sve_prop_change(sve.opacity),
        }

    def layout(self, layout, effect):
        col = layout.column(align=True)
        layout_prop = {
            sve.opacity: {'text':''}
        }

        def l0(_col, _apath:str):
            args0, args1 = get_from_path(effect, sve.props[_apath].path, lambda base, prop: (base, prop,) )
            _col.prop(args0, args1, **layout_prop[_apath])

        def l1(_col, _apath:str):
            _col.prop(effect, '["%s"]'%(_apath), **layout_prop[_apath])

        if effect[sve.startend] == 0:
            layout_0, layout_1 = l0 , l1
        else:
            layout_1, layout_0 = l0 , l1

        # row.menu(G.SEQUENCER_PT_SVEEffects_startend, text= (['Start','End'])[effect[sve.startend]] )
        col = layout.column(align=True)
        col.label(text='Opacity Start')
        layout_0(col, sve.opacity)
        col.label(text='Opacity End')
        layout_1(col, sve.opacity)

    def new_effectstrip(self, sequences, name, channel, frame_start): 
        filepath = create_none_img()
        effectstrip = sequences.new_image(name, filepath, channel, frame_start)
        effectstrip.channel = channel
        return effectstrip
    def init(self, effect: 'effectC'): 
        for path in [sve.offset_x, sve.offset_y, sve.scale_x, sve.scale_y, sve.rotation]:
            add_driver(effect.effect, sve.props[path].path, sve.props[path].path)
anim_opacity = anim_opacity()

