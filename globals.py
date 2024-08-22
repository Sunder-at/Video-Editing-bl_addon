#!/usr/bin/env python3
import bpy
from os import path
from random import seed, random
from tempfile import gettempdir

class _G:
    strips: set[str] = set()
    _edit_strip_name: str = None
    _orig_strip_name: str = None
    _edit_scene_name: str = None
    
    dir_temp: str = gettempdir()+'/sve_bl_addon_imgs'
    _set_random: float = 0.0

    @property
    def TEMPSCENE(self):
        return "SVE_tempScene"
    @property
    def TEMPACTION(self):
        return "SVE_tempAction"
    @property
    def SEQUENCER_MT_SVEEffects_startend(self):
        return 'SEQUENCER_MT_SVEEffects_startend'
    
    @property
    def set_random(self) -> float:
        return self._set_random

    @set_random.setter
    def set_random(self, seedint: int):
        seed(seedint)
        self._set_random = random()


    @property
    def edit_strip(self) -> object:
        scene = self.edit_scene
        if self._edit_strip_name != None and scene != None and self._edit_strip_name in scene.sequence_editor.sequences:
            return scene.sequence_editor.sequences[self._edit_strip_name]
        return None

    @property
    def orig_strip(self) -> object:
        scene = self.edit_scene
        if self._orig_strip_name != None and scene != None and self._orig_strip_name in scene.sequence_editor.sequences_all:
            return scene.sequence_editor.sequences_all[self._orig_strip_name]
        return None

    @property
    def edit_scene(self) -> object:
        if self._edit_scene_name != None and self._edit_scene_name in bpy.data.scenes:
            return bpy.data.scenes[self._edit_scene_name]
        return None

    @edit_strip.setter
    def edit_strip(self, name: str):
        self._edit_strip_name = name

    @orig_strip.setter
    def orig_strip(self, name: str):
        self._orig_strip_name = name

    @edit_scene.setter
    def edit_scene(self, name: str):
        self._edit_scene_name = name


    @property
    def action(self) -> object:
        if self.edit_scene:
            return self.edit_scene.animation_data.action

G = _G()