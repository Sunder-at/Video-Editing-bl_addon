#!/usr/bin/env python3
from os import path
class _G:
    strips: dict = {}
    edit_strip = None
    action = None
    dir: str = path.dirname(__file__)
    dir_temp: str = path.dirname(__file__) + '/_temp'
    set_random: float = 0.0

    @property
    def TEMPSCENE(self):
        return "SVE_tempScene"
    @property
    def TEMPACTION(self):
        return "SVE_tempAction"
    @property
    def SEQUENCER_PT_SVEEffects_startend(self):
        return 'SEQUENCER_PT_SVEEffects_startend'

G = _G()