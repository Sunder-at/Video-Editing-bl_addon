#!/usr/bin/env python3

import bpy
import math
from traceback import format_exc
from typing import Callable
from os import path, makedirs
from .globals import G

def get_by_area(type):
    for a in bpy.context.screen.areas: 
        if a.type == type: return a
    return None

def dorot(p1, p2, rota):
    at = math.atan( (p1/p2) if p2 != 0 else math.inf) - rota + (0.0 if p2 > 0.0 else math.pi)
    length = math.sqrt(p1**2 + p2**2)
    return length * math.sin(at), length * math.cos(at)
    
def printc(*args, **kwargs):
    area = get_by_area('CONSOLE')
    if area:
        s = "\n".join([str(arg) for arg in args])
        with bpy.context.temp_override(area=area):
            for line in s.split("\n"):
                bpy.ops.console.scrollback_append(text=line)

def get_from_path(base, path:list[str], getter: Callable):
    if len(path) == 1:
        return getter(base, path[0])
    else:
        return get_from_path( getattr(base, path[0]) , path[1:], getter)

def debuglist(base: any, props: list[str]):
    printc(str(base))
    for pp in props: debug(base, pp)

def debug(base: any, prop: str):
    def stringifylist(arr, max = 5):
        liststr = []
        islist = not isinstance(arr, bytes) and '__len__' in dir(arr) and arr.__len__() > 0
        if islist and max > 0:
            for ii in list(arr):
                liststr.append( stringifylist(ii, max - 1 ))
            return liststr
        else:
            return str(arr)
    attr = getattr(base, prop)
    stringified = stringifylist(attr)

    isvalid = bool(attr)
    propname = '  ' + str(prop)+ (' -NULL- ' if not isvalid else ' ')
    printc(propname + (' ' * (30 - len(propname)) ) + ' '+ str(stringified) )

def get_attributes(_class):
    return [dd for dd in dir(_class) if dd[:2] != '__' and dd not in ['_b_base_', '_b_needsfree_', '_fields_', '_objects']]

def bool_or(bools: list):
    for ll in bools:
        if bool(ll): 
            return True
    return False

def immutable_change(obj, prop, value):
    def notify(*args, **kwargs):
        if getattr(obj, prop) != value:
            setattr(obj, prop, value)
    def notify_array(*args, **kwargs):
        for aa in range(len(getattr(obj, prop))):
            if getattr(obj, prop)[aa] != value[aa]:
                getattr(obj, prop)[aa] = value[aa]
        
    if "'bpy_prop_array'" in str(getattr(obj, prop).__class__):
        value = [aa for aa in value]
        return notify_array
    return notify

def driver_to_zero(strip, path: list):
    def setdriver(fcurve, expression):
        fcurve.driver.type = 'SCRIPTED'
        fcurve.driver.expression = str( expression  )
        fcurve.driver.is_valid = True
    get_from_path(strip, path, lambda base, prop: base.driver_remove( prop )) 
    fc = get_from_path(strip, path, lambda base, prop: base.driver_add( prop )) 
    if isinstance(fc, list):
        props = get_from_path(strip, path, lambda base, prop: getattr(base, prop))
        for fcIndex in range(len(fc)):
            setdriver(fc[fcIndex], props[fcIndex])
    else:
        setdriver(fc, get_from_path(strip, path, lambda base, prop: getattr(base, prop)))

def try_def(call: Callable):
    def to_call(*args):
        try:
            call()
        except Exception as e:
            # with open('/home/sunder/.config/blender/3.6/scripts/addons/Added_Video_Editing/test', '+w') as file:
            printc(str(e))
            printc(str(format_exc()))
    return to_call

def add_driver(effect, driver_path: list, data_path: list):
    drivers = get_from_path(effect, driver_path, lambda base, prop: base.driver_add( prop )) 
    dpath = get_from_path(G.edit_strip, data_path, lambda base, prop: base.path_from_id( prop )) 
    if isinstance(drivers, list):
        for index, fc in enumerate(drivers):
            fc.driver.type = 'AVERAGE'
            fc.array_index = index
            var = fc.driver.variables.new()
            var.type = 'SINGLE_PROP'
            var.targets[0].data_path = dpath + '[%d]'%(index)
            var.targets[0].id_type = 'SCENE'
            var.targets[0].id = G.edit_scene
            fc.driver.is_valid = True
    else:
        fc = drivers
        fc.driver.type = 'AVERAGE'
        var = fc.driver.variables.new()
        var.type = 'SINGLE_PROP'
        var.targets[0].data_path = dpath
        var.targets[0].id_type = 'SCENE'
        var.targets[0].id = G.edit_scene
        fc.driver.is_valid = True




def remove_driver(effect, driver_path: list):
    get_from_path(effect, driver_path, lambda base, prop: base.driver_remove( prop ))

def create_none_img(srcstrip = None):
    strip = srcstrip if srcstrip != None else G.edit_strip
    if strip.type in ['IMAGE','MOVIE'] and len(strip.elements) > 0:
        w_img = int(strip.elements[0].orig_width)
        h_img = int(strip.elements[0].orig_height)
    else:
        w_img = int(G.edit_scene.render.resolution_x)
        h_img = int(G.edit_scene.render.resolution_y)
    filename = str(w_img)+'x'+str(h_img)


    makedirs(G.dir_temp, exist_ok=True)
    filepath = '%s/%s'%(G.dir_temp, filename)
    if not path.exists(filepath):
        img = bpy.data.images.new(filename, w_img, h_img, alpha=True)
        img.filepath = filepath
        img.pixels = [0.0] * w_img * h_img * 4
        img.update()
        img.save()
    return filepath

class change_checker():
    old_value = None
    def __init__(self, old_value=None) -> None:
        self.old_value = old_value
    def __call__(self, new_value) -> bool:
        if self.old_value != new_value:
            # printc(str(self.old_value) + ' - ' + str(new_value))
            self.old_value = new_value
            return True
        return False

fcurve_paths = [
    ['transform', 'offset_x',],
    ['transform', 'offset_y',],
    ['transform', 'rotation',],
    ['transform', 'origin',],
    ['transform', 'scale_x',],
    ['transform', 'scale_y',],
    ['transform', 'filter',],
    ['use_flip_x',],
    ['use_flip_y',],
    ['blend_alpha',],
    ['blend_type',],
    ['strobe',],
    ['use_reverse_frames',],
    ['color_saturation',],
    ['color_multiply',],
    ['use_float',],
    ['crop', 'max_x',],
    ['crop', 'max_y',],
    ['crop', 'min_x',],
    ['crop', 'min_y',],
]