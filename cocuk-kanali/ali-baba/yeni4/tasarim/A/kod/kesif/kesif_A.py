# EXPLORATORY SCRIPT, kept as a record of what was run; superseded by the numbered scripts.
# first look at all I / IV / V7 choices per bar in C, F, G (became 03_olcum.py)
import sys, itertools
sys.path.insert(0, '/home/user/ring-tokat-3d/cocuk-kanali/ali-baba/yeni4/tasarim/A/kod')
from ortak import *
from olcut import *
from bant import Band, verse_sounding
F = Frames()
D = ['I', 'IV', 'V7']
BASE = {0: ['I','I','IV','I'], 2: ['I','I','IV','I'], 5: ['I','I'], 6: ['I','I','IV','I']}
for key in ['C', 'F', 'G']:
    band = Band(key)
    print('=====', key)
    for bar, lines in ((0, ['L1']), (2, ['L2']), (5, ['diye']), (6, ['L4'])):
        mask = np.isin(F.line, [LINES.index(l) for l in lines])
        res = []
        for combo in itertools.product(D, repeat=len(BASE[bar])):
            bars = dict(BASE); bars[bar] = list(combo)
            plan, deg = major_plan(key, bars)
            e = evaluate(F, plan, mask, sounding=verse_sounding(band, plan8_of(deg)))
            ef = evaluate(F, plan, mask, mode='frame')
            J = e['chord_tone'] - 2 * e['clash_sustained'] - 2 * e['outside_scale']
            res.append((J, combo, e, ef))
        res.sort(key=lambda q: -q[0])
        print(' bar', bar, lines, 'voiced', res[0][2]['voiced_s'])
        for J, combo, e, ef in res[:8] + [q for q in res if list(q[1]) == BASE[bar]]:
            print('   %-16s J %.3f | ct %.3f nc %.3f out %.3f | clash any %.3f sus %.3f (strict %.3f) runs %d | sound %.3f sus %.3f | frame: ct %.3f sus %.3f out %.3f' % (
                ' '.join(combo), J, e['chord_tone'], e['scale_non_chord'], e['outside_scale'], e['clash_any'], e['clash_sustained'], e['clash_sustained_strict'], e['sustained_clash_runs'],
                e['sounding_semitone'], e['sounding_semitone_sustained'], ef['chord_tone'], ef['clash_sustained'], ef['outside_scale']))
