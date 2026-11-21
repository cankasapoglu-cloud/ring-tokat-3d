# EXPLORATORY SCRIPT, kept as a record of what was run; superseded by the numbered scripts.
# search with the chords as played (I, IV, V triad) and its robustness (became the cross-check in 03_olcum.py)
import sys, itertools
sys.path.insert(0, '/home/user/ring-tokat-3d/cocuk-kanali/ali-baba/yeni4/tasarim/A/kod')
from ortak import *
from olcut import *
from bant import Band, verse_sounding
F = Frames(); band = Band('C')
D = ['I', 'IV', 'V']
PLAIN = {0: ['I','I','IV','I'], 2: ['I','I','IV','I'], 5: ['I','I'], 6: ['I','I','IV','I']}
BAR_LINE = {0: 'L1', 2: 'L2', 5: 'diye', 6: 'L4'}
def shape_ok(bar, seq):
    full = (['I','I'] + list(seq)) if bar == 5 else list(seq)
    if bar == 0 and full[0] != 'I': return False
    nxt = full[1:] + ['I']
    if any(a == 'V' and b == 'IV' for a, b in zip(full, nxt)): return False
    if bar == 6 and full[-1] not in ('V', 'I'): return False
    return True
def table(mask_extra, mode='note', top=6, show=True):
    out = {}
    for bar, ln in BAR_LINE.items():
        mask = (F.line == LINES.index(ln)) & mask_extra
        rows = []
        for combo in itertools.product(D, repeat=len(PLAIN[bar])):
            if not shape_ok(bar, combo): continue
            bars = dict(PLAIN); bars[bar] = list(combo)
            plan, deg = major_plan('C', bars)
            e = evaluate(F, plan, mask, mode=mode, sounding=verse_sounding(band, plan8_of(deg)))
            J = e['chord_tone'] - 2 * (e['clash_sustained'] + e['outside_scale'])
            rows.append((J, ' '.join(combo), e))
        rows.sort(key=lambda q: -q[0])
        out[bar] = rows[0][1]
        if show:
            print('bar', bar)
            for J, c, e in rows[:top]:
                print('   %-12s J %.3f ct %.3f clash any %.3f sus %.3f runs %d sound %.3f %.3f' % (c, J, e['chord_tone'], e['clash_any'], e['clash_sustained'], e['sustained_clash_runs'], e['sounding_semitone'], e['sounding_semitone_sustained']))
    return out
ev = np.ones(F.n, bool)
ref = table(ev)
print('frame mode', table(ev, mode='frame', show=False))
for v in range(7): print('leave out', v+1, table(F.verse != v, show=False))
for v in range(7): print('alone', v+1, table(F.verse == v, show=False))
