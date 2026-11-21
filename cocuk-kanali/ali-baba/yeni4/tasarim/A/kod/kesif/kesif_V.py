# EXPLORATORY SCRIPT, kept as a record of what was run; superseded by the numbered scripts.
# first test of the dominant without its seventh on rendered audio; it patched the text of an EARLIER 04_ses_olcumu.py and no longer runs as is (the test is now part of 04_ses_olcumu.py)
# exploratory: does a plain V triad (no seventh) on beat 3 of bars 2 and 6 reduce the rub of the passing E?
import sys, os, runpy
sys.path.insert(0, '/home/user/ring-tokat-3d/cocuk-kanali/ali-baba/yeni4/tasarim/A/kod')
import numpy as np
import bant
from ortak import *
# add a 'V' degree to the band model (voicing = V7 without its seventh)
bant._CH['V'] = [54, 57, 62]; bant._ROLL['V'] = bant._ROLL['V7']; bant._DEG['V'] = 7
import importlib
src = open('/home/user/ring-tokat-3d/cocuk-kanali/ali-baba/yeni4/tasarim/A/kod/04_ses_olcumu.py', encoding='utf8').read()
src = src.replace('''PLANS = {''', '''PLANS = {
    "aday1V_I-I-I-V": {0: ['I', 'IV', 'I', 'I'], 2: ['I', 'I', 'I', 'V'], 5: ['I', 'I'], 6: ['I', 'I', 'I', 'V']},''')
src = src.replace('SES = os.path.join(ARA, "ses")', 'SES = "/tmp/claude-0/-home-user-ring-tokat-3d/bd9d6832-1bf0-57ca-8544-ce6f4befd453/scratchpad/sesV"')
src = src.replace('save_json(os.path.join(T, "ses_olcumu.json" if MODE == "note" else "ses_olcumu_kare_modu.json"), {', 'save_json("/tmp/claude-0/-home-user-ring-tokat-3d/bd9d6832-1bf0-57ca-8544-ce6f4befd453/scratchpad/sesV/out.json", {')
src = src.replace('for name in ("aday1_I-I-I-V7", "aday2_I-I-V7-V7"):', 'for name in ("aday1_I-I-I-V7", "aday1V_I-I-I-V"):')
sys.argv = ['x']
exec(compile(src, 'x', 'exec'))
