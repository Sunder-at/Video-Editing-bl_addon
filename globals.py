#!/usr/bin/env python3
from os import path
from random import seed, random

class _G:
    strips: dict = {}
    edit_strip = None
    orig_strip = None
    action = None
    dir: str = path.dirname(__file__)
    dir_temp: str = path.dirname(__file__) + '/_temp'
    _set_random: float = 0.0

    @property
    def TEMPSCENE(self):
        return "SVE_tempScene"
    @property
    def TEMPACTION(self):
        return "SVE_tempAction"
    @property
    def SEQUENCER_PT_SVEEffects_startend(self):
        return 'SEQUENCER_PT_SVEEffects_startend'
    
    @property
    def set_random(self) -> float:
        return self._set_random

    @set_random.setter
    def set_random(self, seedint: int):
        seed(seedint)
        self._set_random = random()

G = _G()