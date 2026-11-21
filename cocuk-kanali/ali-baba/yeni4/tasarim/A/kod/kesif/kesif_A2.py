# EXPLORATORY SCRIPT, kept as a record of what was run; superseded by the numbered scripts.
# clash runs of the candidates for beats 2-3 of bars 2 and 6, per-verse note lengths (became the detail output of 03_olcum.py)
import sys, itertools
sys.path.insert(0, '/home/user/ring-tokat-3d/cocuk-kanali/ali-baba/yeni4/tasarim/A/kod')
from ortak import *
from olcut import *
from bant import Band, verse_sounding
F = Frames()
BASE = {0: ['I','IV','I','I'], 2: ['I','I','I','V7'], 5: ['I','I'], 6: ['I','I','I','V7']}
key='C'; band=Band(key)
for bar, line in ((2,'L2'),(6,'L4')):
    mask = F.line == LINES.index(line)
    for x in (['I','I','I','V7'], ['I','I','V7','V7'], ['I','I','IV','V7'], ['I','I','I','I'], ['I','I','IV','I']):
        bars = dict(BASE); bars[bar] = x
        plan, deg = major_plan(key, bars)
        e = evaluate(F, plan, mask, sounding=verse_sounding(band, plan8_of(deg)), detail=True)
        print(bar, x, {k: v for k, v in e.items() if k != 'runs'})
        for rr in e['runs']: print('      ', rr)
# per-verse voiced durations of the notes at beats 2..4 of L2 and L4
for line in ('L2','L4'):
    print(line)
    for v in range(7):
        m = (F.line == LINES.index(line)) & (F.verse == v)
        b0 = LINE_BAR[line]*4
        segs=[]; pos=F.pos[m]-b0; pc=F.pc_note[m]; t=F.t[m]
        i=0
        while i < len(pos):
            j=i
            while j+1 < len(pos) and pc[j+1]==pc[i] and t[j+1]-t[j] < 0.0051: j+=1
            if pos[i] > 1.8: segs.append('%s %.2f-%.2f (%d ms)' % (NOTE[pc[i]], pos[i], pos[j]+FP/BEAT, round((j-i+1)*5)))
            i=j+1
        print('  v%d: %s' % (v+1, ' | '.join(segs)))
