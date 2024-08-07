#!/usr/bin/env python3
import bpy
from typing import Callable
from random import seed, random
from .sve_struct import sve, anim_base
from .utility import get_from_path, change_checker, printc
from .globals import G
from .bpy_ctypes import calc_bezier
    
class effectC:
    all: dict[str, 'effectC'] = {}
    effect: object
    fcurves: set['fcurveC']
    atype: anim_base
    
    def __new__(cls, *args):
        if len(args) == 1:
            return super(__class__, cls).__new__(cls)
        elif len(args) == 3:
            props = args[2]
            assert issubclass(props.__class__, dict) 
            if props.get('type','?') in anim_base.all:
                return super(__class__, cls).__new__(cls)
            return None
            
            


    def __init__(self, *args) -> None:
        def init3(self: 'effectC', name: str, scene, props: dict = {}) -> None:
            start = props.get('start', scene.frame_current)
            duration = props.get('end', start + 20) - start
            duration = 1 if duration < 1 else duration

            self.atype = anim_base.all[props['type']]
            self.effect = self.atype.new_effectstrip(scene.sequence_editor.sequences, name, 2, start)
            self.effect.frame_final_duration = duration
            scene.sequence_editor.active_strip = self.effect
            
            self.atype.to_effect(self.effect, props.get('props', {}) )
            self.effect[sve.type] = props['type']

        def init1(self: 'effectC', effectstrip):
            self.effect = effectstrip
            self.atype = anim_base.all[self.effect[sve.type]]
            self.effect[sve.type] = self.effect[sve.type]

        if len(args) == 1:
            init1(self, *args)
        elif len(args) == 3:
            init3(self, *args)
        
        self.fcurves = set()
        self.all[self.effect.as_pointer()] = self

        for prop, call in self.prop_update.items():
            call(self, self.effect[prop])
        G.strips[self.effect.as_pointer()] = self.effect

        self.atype.init(self)

        bpy.msgbus.clear_by_owner(self.effect)

        for prop in self.atype.props:
            if sve.props[prop].use:
                for use in sve.props[prop].use:
                    self.subscribe_prop(use)

        

    def add_to_fcurve(self, svepath: str):
        if svepath not in fcurveC.all:
            fcurve = fcurveC(svepath)
        else:
            fcurve = fcurveC.all[svepath]

        fcurve.add_effect(self)
        self.fcurves.add(fcurve)
        fcurve.frame_recalc()

    def remove_from_fcurve(self, svepath: str):
        if svepath not in fcurveC.all: return
        fcurve = fcurveC.all[svepath]
        fcurve.remove_effect(self)
        if fcurve in self.fcurves:
            self.fcurves.remove(fcurve)
        fcurve.frame_recalc()

    def get_values(self, sve_path) -> tuple[float,float]:
        val0 = get_from_path(self, sve.props[sve_path].path, lambda base, prop: getattr(base, prop))
        val1 = self.effect[sve_path]
        if self.startend: val0 , val1 = val1 , val0
        return val0 , val1
    
    def set_values(self, sve_path, val0, val1):
        if self.startend: val0 , val1 = val1 , val0
        get_from_path(self, sve.props[sve_path].path, lambda base, prop: setattr(base, prop, val0))
        self.effect[sve_path] = val1
        return val0 , val1
    
    def subscribe_prop(self, prop):
        def notify(*args, **kwargs):
            if prop in fcurveC.all:
                fcurveC.all[prop].keyframes_value_recalc()
        
        bpy.msgbus.subscribe_rna(
            key=get_from_path(self.effect, sve.props[prop].path, lambda base, targ: base.path_resolve(targ, False) ),
            owner=self.effect, args=(1,), options={'PERSISTENT',},
            notify=notify )
        

    
    @property
    def name(self) -> str:
        return self.effect.name
    @property
    def type(self) -> str:
        return self.effect[sve.type]
    @property
    def prop_update(self) -> dict[str, Callable]:
        return self.atype.prop_update
    @property
    def modifier(self) -> dict:
        return self.atype.modifier(self)
    @property
    def startend(self) -> str:
        return self.effect[sve.startend] if sve.startend in self.effect else 0
    @property
    def start(self) -> int:
        return self.effect.frame_final_start
    @property
    def end(self) -> int:
        return self.effect.frame_final_end
    @property
    def frame(self) -> int:
        return (self.start if self.startend == 0 else self.end)
    @property
    def transform(self):
        return self.effect.transform
    @property
    def blend_alpha(self):
        return self.effect.blend_alpha
    
class comparerC:
    start: int
    end: int
    effect: effectC
    effectID: int
    def __init__(self, effect: effectC) -> None:
        self.start = effect.start
        self.end = effect.end
        self.effect = effect
        self.effectID = id(effect)

    def __eq__(self, value: 'comparerC') -> bool:
        return [self.start, self.end, self.effectID] == [value.start, value.end, self.effectID]
    def __lt__(self, value: 'comparerC') -> bool:
        return [self.start, self.end, self.effectID] <  [value.start, value.end, self.effectID]
    def __gt__(self, value: 'comparerC') -> bool:
        return [self.start, self.end, self.effectID] >  [value.start, value.end, self.effectID]
    def __le__(self, value: 'comparerC') -> bool:
        return [self.start, self.end, self.effectID] <= [value.start, value.end, self.effectID]
    def __ge__(self, value: 'comparerC') -> bool:
        return [self.start, self.end, self.effectID] >= [value.start, value.end, self.effectID]
    
class rangeC(comparerC):
    start: int
    end: int
    effect: effectC
    frames: set[int]
    sve_path: str
    
    def __init__(self, effect: effectC, sve_path: str) -> None:
        super().__init__(effect)
        self.sve_path = sve_path
        self.frames = set()

    def __call__(self) -> dict[int, float]:
        vals = self.effect.get_values(self.sve_path)
        frame_dict: dict[int, float] = {
            self.start: vals[0],
            self.end  : vals[1],
        }
        for ff in self.frames:
            frame_dict[ff] = self.interpolate(self.start, self.end, vals[0], vals[1], ff)
        return frame_dict

    def interpolate(self, start_f: float, end_f: float, start_val: float, end_val: float, point: float) -> float:
        if point == start_f: return start_val
        elif point == end_f: return end_val
        if start_val == end_val: return start_val
        diff = end_f - start_f
        diff = 5.0 if diff > 5.0 else diff

        v1 = [start_f      , start_val]
        v2 = [start_f +diff, start_val]
        v3 = [end_f   -diff, end_val  ]
        v4 = [end_f        , end_val  ]

        return calc_bezier(v1, v2, v3, v4, point)


class fcurveC:
    all: dict[str, 'fcurveC'] = {}
    fcurve: object
    effects : set[effectC]
    path: list[str]
    sve_path: str
    keyframes: list[rangeC]
    modifiers: list[comparerC]
    datapath: str
    check_change: change_checker
    default: float

    def __init__(self, sve_path: str) -> None:
        self.path = sve.props[sve_path].path
        self.sve_path = sve_path
        self.datapath = get_from_path(G.edit_strip, self.path, lambda base, prop: base.path_from_id( prop ))
        self.fcurve = G.action.fcurves.new( self.datapath )
        self.effects = set()
        self.keyframes = []
        self.modifiers = []
        self.check_change = change_checker()
        self.check_change(self.value)
        self.all[sve_path] = self
        self.default = self.value
    
        def notify(*args, **kwargs):
            if G.edit_strip.select or bpy.context.active_sequence_strip == G.edit_strip:
                self.if_not_on_fcurve()
            # printc('change '+self.sve_path)
            pass
        
        bpy.msgbus.subscribe_rna(
            key=get_from_path(G.edit_strip, self.path, lambda base, targ: base.path_resolve(targ, False) ),
            owner=G.edit_strip, args=(1,), options={'PERSISTENT',},
            notify=notify )
            


    def get_keyframes_modifiers(self) -> tuple[list[rangeC], list[comparerC], ]:
        keyframes: list[rangeC] = []
        modifiers: list[comparerC] = []
        
        for effect in self.effects:
            if effect.modifier:
                modifiers.append(comparerC(effect))
            else:
                keyframes.append(rangeC(effect, self.sve_path))
        
        modifiers.sort()

        if len(keyframes) <= 1:
            return keyframes, modifiers
        keyframes.sort()

        for fr0 in range(len(keyframes) - 1):
            kf0 = keyframes[fr0]
            for fr1 in range(fr0 + 1, len(keyframes)):
                kf1 = keyframes[fr1]
                # if start of next is less then end of previous -> overlap
                if kf1.start <= kf0.end:
                    kf0.frames.add( kf1.start )
                    if kf1.end <= kf0.end:
                        kf0.frames.add( kf1.end )
                    else:
                        kf1.frames.add( kf0.end )
        return keyframes, modifiers
    
    def frame_recalc(self):
        new_kf, new_mf = self.get_keyframes_modifiers()
        if self.keyframes != new_kf or len(new_kf) == 0:
            self.keyframes.clear()
            self.keyframes = new_kf
            self.keyframes_value_recalc()
        if self.modifiers != new_mf:
            self.modifiers.clear()
            self.modifiers = new_mf
            self.modifiers_value_recalc()
            

    def keyframes_value_recalc(self):
        frames: dict[int, float] = {}
        fcurve_kfp = self.fcurve.keyframe_points

        def add(k:int, v:float):
            if k in frames: frames[k] += v
            else: frames[k] = v
        
        for rr in self.keyframes:
            for frame, value in rr().items():
                add(frame, value)
        
        if len(self.keyframes) == 0:
            add(G.edit_strip.frame_start, self.default )

        
        kplen = len(fcurve_kfp)
        if len(frames) > kplen:
            fcurve_kfp.add(len(frames) - kplen)
        elif len(frames) < kplen:
            for ii in range(kplen - len(frames)):
                fcurve_kfp.remove(fcurve_kfp[-1], fast=True)
        fcurve_kfp.sort()
        keys: list = list(frames.keys())
        keys.sort()

        for iik in range(len(frames)):
            if list(fcurve_kfp[iik].co) != [float(keys[iik]), frames[keys[iik]], ]:
                fcurve_kfp[iik].co = [float(keys[iik]), frames[keys[iik]], ]
                fcurve_kfp[iik].handle_left = [float(keys[iik]) - 5.0, frames[keys[iik]], ]
                fcurve_kfp[iik].handle_right = [float(keys[iik]) + 5.0, frames[keys[iik]], ]

        fcurve_kfp.sort()
        self.check_change(self.value)
    
    def modifiers_value_recalc(self):
        seed(id(self.fcurve))
        G.set_random = random()
        fmod = list(self.fcurve.modifiers)
        smod = self.modifiers.copy()
        for ffm in fmod.copy():
            for ssm in smod.copy():
                if ssm.effect.modifier['type'] != ffm.type: continue
                ffm.frame_start = ssm.start
                ffm.frame_end = ssm.end
                ssm.effect.atype.to_modifier(ffm, ssm.effect)
                fmod.remove(ffm)
                smod.remove(ssm)
        
        for ffm in fmod.copy():
            for ssm in smod.copy():
                if ssm.effect.modifier['type'] != ffm.type: continue
                ffm.frame_start = ssm.start
                ffm.frame_end = ssm.end
                ssm.effect.atype.to_modifier(ffm, ssm.effect)
                fmod.remove(ffm)
                smod.remove(ssm)

                # if ssm[3]['type'] != ffm.type \
                #     or ssm[0] != ffm.frame_start \
                #     or ssm[1] != ffm.frame_end: continue
                # ssm[2].atype.to_modifier(ffm, ssm[2])
                # fmod.remove(ffm)
                # smod.remove(ssm)
        for ffm in fmod:
            self.fcurve.modifiers.remove(ffm)

        for ssm in smod:
            newfm = self.fcurve.modifiers.new(ssm.effect.modifier['type'])
            ssm.effect.atype.to_modifier(newfm, ssm.effect)
            newfm.frame_start = ssm.start
            newfm.frame_end = ssm.end



    def add_effect(self, effect: effectC):
        self.effects.add(effect)
        
    def remove_effect(self, effect: effectC):
        if effect in self.effects:
            self.effects.remove(effect)

    def if_not_on_fcurve(self):
        # evalue = self.evaluate
        curr = self.value
        prev = self.check_change.old_value
        if not self.check_change(curr): return
        diff = curr - prev
        for eff in self.effects:
            if not eff.modifier:
                vals = eff.get_values(self.sve_path)
                eff.set_values(self.sve_path, vals[0] + diff, vals[1] + diff)
        self.default += diff
        self.keyframes_value_recalc()

        # self.value = evalue


    @property
    def evaluate(self):
        return self.fcurve.evaluate(bpy.context.scene.frame_current)

    @property
    def value(self):
        return get_from_path(G.edit_strip, self.path, lambda base, prop: getattr(base, prop) )
    
    # @value.setter
    # def value(self, val):
    #     get_from_path(G.edit_strip, self.path, lambda base, prop: setattr(base, prop, val) )
    
    def recalc_all(self = None):
        for _, fcurve in fcurveC.all.items():
            fcurve.frame_recalc()

