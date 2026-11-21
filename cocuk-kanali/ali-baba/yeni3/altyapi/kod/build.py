#!/usr/bin/env python3
# Ali Baba'nin Ciftligi - yeni3 backing builder (FluidSynth + mido), adapted from yeni2/kod/build.py.
#
# New song form (all in the vocal's own tempo, no key change inside the song):
#   intro 4 bars | 7 verses x 8 bars | ending 4 bars = 64 bars + ring-out tail
#   verse bars: 0 vocal L1 (band plays phrase A)      1 loud answer "E-I-E-I-O" (brass+glockenspiel)
#               2 vocal L2 (phrase A)                 3 loud answer
#               4 vocal L3 (repeated do, soft)        5 vocal L4 (soft answer under the vocal)
#               6 animal call 1 (thin texture)        7 animal call 2 (thin texture + snare pickup)
# The melody that plays UNDER the vocal (bars 0, 2, 4, 5) goes to its own stem (clarinet + light glockenspiel).
#
# usage: build.py --key C --name dogal --out <output folder> --work <scratch folder> [--bpm 116.015]
#        build.py --key G --name ezgi  --out <output folder> --work <scratch folder>
import argparse, json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
import numpy as np, mido, soundfile as sf, pyloudnorm
from scipy.ndimage import minimum_filter1d, maximum_filter1d, uniform_filter1d
from scipy.signal import resample_poly

ap = argparse.ArgumentParser()
ap.add_argument('--bpm', type=float, default=116.015)
ap.add_argument('--key', default='C', help='tonic of the major key (do), e.g. C or G')
ap.add_argument('--name', default=None, help='variant name used in file names (default: dogal for C, ezgi for G)')
ap.add_argument('--out', required=True)
ap.add_argument('--work', required=True)
ap.add_argument('--lufs', type=float, default=-14.0, help='integrated loudness target of altyapi_<name>.wav')
ap.add_argument('--ezgi-alti-db', type=float, default=-10.0,
                help='default level of the under-vocal stem: its RMS relative to the band RMS in the bars where it plays')
ap.add_argument('--tail', type=float, default=2.5, help='seconds of ring-out kept after the final hit')
A = ap.parse_args()
KEY = A.key
NAME = A.name or {'C': 'dogal', 'G': 'ezgi'}.get(KEY, 'ton_' + KEY)
O = A.out; S = os.path.join(A.work, NAME)
os.makedirs(O, exist_ok=True); os.makedirs(S, exist_ok=True); os.makedirs(os.path.join(O, 'midi'), exist_ok=True)

BPM = A.bpm; TPB = 480; BEAT = 60 / BPM; BAR = 4 * BEAT; sr = 44100
TEMPO_US = int(round(60e6 / BPM))          # MIDI tempo is an integer number of microseconds per beat
BEAT_MIDI = TEMPO_US / 1e6                 # what FluidSynth really plays (differs from BEAT by < 1 microsecond)
SF = '/usr/share/sounds/sf2/FluidR3_GM.sf2'
PRE = 1.0                                  # beats of silent pre-roll in the MIDI (cut after rendering)
LAT = 82                                   # samples: smallest FluidSynth render latency measured (see olcum_gecikme.py)
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
nm = lambda m: f"{NAMES[m % 12]}{m // 12 - 1}"
PC = {n: i for i, n in enumerate(NAMES)}; PC.update({'Db': 1, 'Eb': 3, 'Gb': 6, 'Ab': 8, 'Bb': 10})
TON = PC[KEY]

# ---- key handling: the arrangement is written in G (as in yeni2) and moved per part -------------------------
d = (TON - 7) % 12
AS = d if d <= 3 else d - 12               # accompaniment (banjo, piano, accordion, brass chords, fanfare): G -> C = -7
LEAD_DO = 65 + (TON - 5) % 12              # loud lead "do" in F4..E5:  G -> G4 (67),  C -> C5 (72)
ALT_DO = 69 + (TON - 9) % 12               # under-vocal "do" in A4..G#5: C -> C5 (72), G -> G5 (79)
DEG = {'I': 0, 'IV': 5, 'V7': 7}
CH = {k: [n + AS for n in v] for k, v in {'I': [55, 59, 62], 'IV': [55, 60, 64], 'V7': [54, 57, 60, 62]}.items()}
ROLL = {k: [n + AS for n in v] for k, v in {'I': [62, 67, 59, 67, 62, 67, 59, 67], 'IV': [64, 67, 60, 67, 64, 67, 60, 67],
                                            'V7': [62, 66, 60, 66, 62, 66, 57, 66]}.items()}
ROOT = {k: 36 + (TON + v) % 12 for k, v in DEG.items()}         # bass roots kept in C2..B2 in every key
FIFTH = {k: 36 + (TON + v + 7) % 12 for k, v in DEG.items()}
CHNAME = {'I': KEY, 'IV': NAMES[(TON + 5) % 12], 'V7': NAMES[(TON + 7) % 12] + '7'}

VERSES = [('inek', 'Çiftliğinde inekleri var', 'İnekler nasıl bağırır?'), ('koyun', 'Çiftliğinde koyunları var', 'Koyunlar nasıl meler?'),
          ('at', 'Çiftliğinde bir de atı var', 'Atı nasıl kişner?'), ('horoz', 'Çiftliğinde horozları var', 'Horozlar nasıl öter?'),
          ('ördek', 'Çiftliğinde ördekleri var', 'Ördekler nasıl bağırır?'), ('köpek', 'Çiftliğinde köpekleri var', 'Köpekler nasıl havlar?'),
          ('kedi', 'Çiftliğinde bir kedisi var', 'Kedisi nasıl miyavlar?')]
INTRO = 4; VB = 8; NV = 7; END = 4; TOTAL = INTRO + VB * NV + END
PA = ['I', 'I', 'IV', 'I']; AN = ['I', 'V7', 'I', 'I']; II = ['I'] * 4
# bars: (chord per beat, kind, verse index (-1 intro, NV ending), bar inside its section)
bars = [(PA, 'intro_a', -1, 0), (AN, 'intro_ans', -1, 1), (PA, 'intro_a', -1, 2), (AN, 'intro_ansfill', -1, 3)]
for k in range(NV):
    bars += [(PA, 'voc', k, 0), (AN, 'ans', k, 1), (PA, 'voc', k, 2), (AN, 'ans', k, 3),
             (II, 'voc3', k, 4), (AN, 'voc4', k, 5), (II, 'slot', k, 6), (II, 'slot2', k, 7)]
bars += [(AN, 'ans', NV, 0), (AN, 'ans2', NV, 1), (['IV', 'IV', 'V7', 'V7'], 'roll', NV, 2), (II, 'final', NV, 3)]
assert len(bars) == TOTAL
ROLE = {'intro_a': 'giriş: A cümlesi (lead: trompet+brass+glockenspiel, tam orkestra)', 'intro_ans': 'giriş: cevap "E-I-E-I-O" (lead, yüksek)',
        'intro_ansfill': 'giriş: cevap + kıtaya davul geçişi', 'voc': 'vokal + alttan A cümlesi (ezgi_alti)', 'ans': 'enstrümantal cevap "E-I-E-I-O" (yüksek: trompet+brass+glockenspiel)',
        'voc3': 'vokal satır 3 + alttan tekrarlı do (ezgi_alti)', 'voc4': 'vokal satır 4 "Dinle bak" + alttan yumuşak cevap (ezgi_alti)',
        'slot': 'HAYVAN SESİ 1 (ince doku: kick + hafif hi-hat + yumuşak bas)', 'slot2': 'HAYVAN SESİ 2 (ince doku + ölçü sonunda trampet girişi)',
        'ans2': 'bitiş: cevap, üçlü armonili', 'roll': 'bitiş: IV - V7, trampet rulosu + brass fanfarı', 'final': 'bitiş: son I vuruşu + crash'}

ev = {}
def add(ch, b, dur, n, v): ev.setdefault(ch, []).append((b, dur, int(n), int(min(127, v))))
BASS, BANJO, ACC, PNO, GLK, TPT, BRS, CLA, GLK2, DR = 0, 1, 2, 3, 4, 5, 6, 7, 8, 9
CHN = {BASS: 'bas', BANJO: 'banjo', ACC: 'akordeon', PNO: 'piyano', GLK: 'glockenspiel', TPT: 'trompet', BRS: 'brass', CLA: 'klarnet',
       GLK2: 'glockenspiel_hafif', DR: 'davul'}
PROG = {BASS: 33, BANJO: 105, ACC: 21, PNO: 1, GLK: 9, TPT: 56, BRS: 61, CLA: 71, GLK2: 9}
VOL = {BASS: 113, BANJO: 104, ACC: 86, PNO: 100, GLK: 120, TPT: 116, BRS: 102, CLA: 112, GLK2: 112, DR: 124}
PAN = {BASS: 64, BANJO: 36, ACC: 94, PNO: 54, GLK: 78, TPT: 60, BRS: 70, CLA: 64, GLK2: 64}
REV = {DR: 18, BASS: 8}
BAND = [BASS, BANJO, ACC, PNO, GLK, TPT, BRS, DR]; ALT = [CLA, GLK2]
# Negative track delay (in MIDI ticks, 1 tick = beat/480 = 1.08 ms) for patches whose sound starts late (measured in olcum_gecikme.py):
# the finger bass has ~22 ms of quiet pre-attack before the pluck, accordion / clarinet / brass section swell slowly.
ADV = {BASS: 19, ACC: 19, CLA: 14, BRS: 7}

mel = []   # melody note list for zaman_<name>.json and for the verification
def M(part, ch, bi, bt, dur, n, v, mono=True):
    add(ch, bi * 4 + bt, dur, n, v)
    mel.append({'parti': part, 'kanal': ch, 'enstruman': CHN[ch], 'olcu': bi, 'vurus': bt, 'midi': int(n), 'nota': nm(int(n)),
                'sure_vurus': dur, 'hiz': int(v), 'tek_ses': mono})

PHA = [(0, 0, .42), (0, .5, .42), (0, 1, .42), (-5, 1.5, .42), (-3, 2, .42), (-3, 2.5, .42), (-5, 3, .9)]   # do do do sol, la, la, sol,
ANS = [(4, 0, .42), (4, .5, .42), (2, 1, .42), (2, 1.5, .42), (0, 2, 1.5)]                                 # mi mi re re do
def lead_phraseA(bi):
    for i, (iv, bt, dur) in enumerate(PHA):
        n = LEAD_DO + iv; v = 120 if bt in (0, 1, 2, 3) else 112
        M('lead', TPT, bi, bt, dur, n, v); M('lead', GLK, bi, bt, dur, n + 12, 116)
        M('lead', BRS, bi, bt, dur, n, v - 12, mono=False); M('lead', BRS, bi, bt, dur, n - 12, v - 18, mono=False)
def lead_answer(bi, hi=False):
    for i, (iv, bt, dur) in enumerate(ANS):
        n = LEAD_DO + iv; v = 122 if i in (0, 2, 4) else 112
        M('lead', TPT, bi, bt, dur, n, v); M('lead', GLK, bi, bt, dur, n + 12, 118)
        M('lead', BRS, bi, bt, dur, n, v - 10, mono=False); M('lead', BRS, bi, bt, dur, n - 12, v - 14, mono=False)
        if hi: M('lead', BRS, bi, bt, dur, n + (4 if iv == 0 else 3), v - 16, mono=False)   # diatonic third above (sol sol fa fa mi)
    add(DR, bi * 4, .2, 55, 104)                                                            # splash on the answer
def alt_notes(bi, notes, v_on, v_off, vg):
    for (iv, bt, dur) in notes:
        n = ALT_DO + iv; on = float(bt).is_integer()
        M('ezgi_alti', CLA, bi, bt, dur, n, v_on if on else v_off)
        M('ezgi_alti', GLK2, bi, bt, min(dur, .5), n + 12, vg if on else vg - 10)
ALT_PHA = [(iv, bt, .46 if dur < .5 else .95) for (iv, bt, dur) in PHA]
ALT_DOREP = [(0, i * .5, .44) for i in range(8)]
ALT_ANS = [(iv, bt, .46 if dur < .5 else 1.5) for (iv, bt, dur) in ANS]

def drums_full(b0, k, kind):
    for bt in range(4):
        fillS = (kind == 'fillS' and bt == 3); fillB = (kind == 'fillB' and bt >= 2)
        add(DR, b0 + bt, .2, 36, 114)                                                      # driving kick on every beat
        if bt in (1, 3): add(DR, b0 + bt, .2, 38, 114); add(DR, b0 + bt, .2, 39, 104)      # snare + clap on 2 and 4
        if not (fillS or fillB):
            add(DR, b0 + bt, .1, 42, 86); add(DR, b0 + bt + .25, .1, 42, 46); add(DR, b0 + bt + .75, .1, 42, 52)
            if kind == 'cut' and bt == 3: add(DR, b0 + bt + .5, .1, 42, 70)                # no ringing open hat right before the animal slot
            else: add(DR, b0 + bt + .5, .2, 46, 80)                                        # open hat on the off-beat
        for s, v in ((0, 44), (.25, 36), (.5, 74), (.75, 40)): add(DR, b0 + bt + s, .1, 54, v)   # tambourine
        if k >= 2:                                                                         # extra percussion from verse 3 on
            add(DR, b0 + bt, .1, 56, 84); add(DR, b0 + bt + .5, .1, 76, 72)
            if bt in (1, 3): add(DR, b0 + bt + .75, .1, 77, 66)
    add(DR, b0 + 2.5, .2, 36, 92)
    if kind == 'fillS':                                                                    # short fill into the answer
        add(DR, b0 + 3.25, .1, 38, 88); add(DR, b0 + 3.5, .1, 48, 100); add(DR, b0 + 3.75, .1, 45, 108)
    if kind == 'fillB':                                                                    # big fill into the verse
        for i, (n, v) in enumerate([(38, 92), (38, 98), (50, 102), (50, 106), (48, 110), (47, 114), (45, 118), (43, 124)]):
            add(DR, b0 + 2 + i * .25, .1, n, v)
def groove(b0, ch, k, dkind, stab=False):
    for bt in range(4):
        c = ch[bt]
        low = FIFTH[c] if (bt == 2 and c == ch[0] == ch[1]) else ROOT[c]
        add(BASS, b0 + bt, .45, low, 116); add(BASS, b0 + bt + .5, .38, ROOT[c] + 12, 104)            # octave-jumping bass
        for e in range(2): add(BANJO, b0 + bt + e * .5, .45, ROLL[c][bt * 2 + e], 100 if e == 0 else 90)   # banjo roll
        add(BANJO, b0 + bt + .25, .2, CH[c][-1], 70); add(BANJO, b0 + bt + .75, .2, CH[c][-1], 70)
        for n in CH[c]:
            add(PNO, b0 + bt + .5, .28, n + 12, 100)                                       # off-beat piano upstroke
            if bt in (1, 3): add(ACC, b0 + bt, .45, n + 12, 92); add(BANJO, b0 + bt, .3, n, 82)
            add(ACC, b0 + bt + .5, .25, n + 12, 74)                                        # off-beat accordion
        if bt in (0, 2): add(PNO, b0 + bt, .4, ROOT[c] + 12, 92); add(PNO, b0 + bt, .4, ROOT[c] + 24, 84)   # "oom"
        if stab and bt in (1, 3):
            for n in CH[c][-3:]: add(BRS, b0 + bt + .5, .22, n + 12, 96)
    drums_full(b0, k, dkind)

for bi, (ch, kind, k, vb) in enumerate(bars):
    b0 = bi * 4
    if kind == 'intro_a': groove(b0, ch, k, 'fillS'); lead_phraseA(bi)
    elif kind == 'intro_ans': groove(b0, ch, k, 'full'); lead_answer(bi)
    elif kind == 'intro_ansfill': groove(b0, ch, k, 'fillB'); lead_answer(bi)
    elif kind == 'voc': groove(b0, ch, k, 'fillS'); alt_notes(bi, ALT_PHA, 100, 90, 92)
    elif kind in ('ans', 'ans2'): groove(b0, ch, k, 'full'); lead_answer(bi, hi=(kind == 'ans2'))
    elif kind == 'voc3': groove(b0, ch, k, 'full', stab=True); alt_notes(bi, ALT_DOREP, 88, 78, 80)
    elif kind == 'voc4': groove(b0, ch, k, 'cut'); alt_notes(bi, ALT_ANS, 100, 90, 92)
    elif kind in ('slot', 'slot2'):                                                        # animal call: thin texture
        add(BASS, b0, .9, ROOT['I'], 80); add(BASS, b0 + 2, .9, FIFTH['I'], 74)
        for bt in range(4):
            add(DR, b0 + bt, .2, 36, 88 if bt in (0, 2) else 62)
            add(DR, b0 + bt, .1, 42, 56); add(DR, b0 + bt + .5, .1, 42, 38)
        if kind == 'slot2':                                                                # snare pickup back into the band
            add(DR, b0 + 3.5, .1, 38, 96); add(DR, b0 + 3.75, .1, 38, 118); add(DR, b0 + 3.75, .1, 45, 100)
    elif kind == 'roll':
        for i in range(16):
            add(DR, b0 + i * .25, .1, 38, 62 + i * 4)
            if i >= 12: add(DR, b0 + i * .25 + .125, .1, 38, 58 + i * 4)
        for bt in range(4): add(DR, b0 + bt, .2, 36, 112); add(DR, b0 + bt, .1, 56, 84)
        add(DR, b0, .2, 49, 112)
        for bt, c in ((0, 'IV'), (2, 'V7')):
            add(BASS, b0 + bt, 1.9, ROOT[c] + 12, 118)
            for n in CH[c]:
                add(ACC, b0 + bt, 1.8, n + 12, 100); add(PNO, b0 + bt, 1.0, n, 108); add(PNO, b0 + bt, 1.0, n + 12, 104)
                add(BANJO, b0 + bt, .6, n, 104); add(BRS, b0 + bt, 1.8, n, 104)
        for i, n in enumerate([72, 76, 79, 76, 74, 78, 81, 84]):                           # rising fanfare: IV arpeggio, V7 arpeggio
            M('lead', TPT, bi, i * .5, .45, n + AS, 118); M('lead', GLK, bi, i * .5, .45, n + AS + 12, 112)
            add(BRS, b0 + i * .5, .45, n + AS - 12, 100)
    elif kind == 'final':
        for i in range(10): add(DR, b0 + i * .25, .1, 38, 70 + i * 4)
        add(DR, b0 + 2.5, .1, 38, 112); add(DR, b0 + 2.75, .1, 38, 120)
        for bt, dur in ((0, 2.4), (3, 3.0)):
            add(BASS, b0 + bt, dur, ROOT['I'], 124); add(BASS, b0 + bt, dur, ROOT['I'] + 12, 120)
            add(DR, b0 + bt, .2, 36, 126); add(DR, b0 + bt, .2, 49, 124); add(DR, b0 + bt, .2, 57, 116); add(DR, b0 + bt, .2, 39, 108)
            if bt == 3: add(DR, b0 + bt, .2, 38, 124)
            for n in CH['I']:
                add(ACC, b0 + bt, dur, n + 12, 106); add(PNO, b0 + bt, dur, n, 114); add(PNO, b0 + bt, dur, n + 12, 108)
                add(BANJO, b0 + bt, dur, n, 110); add(BRS, b0 + bt, dur, n, 112); add(BRS, b0 + bt, dur, n + 12, 108)
            add(PNO, b0 + bt, dur, ROOT['I'] + 12, 112)
            for n in (79, 83, 86):                                                         # final I chord (root, third, fifth)
                M('lead', TPT, bi, bt, dur, n + AS, 122, mono=False); M('lead', GLK, bi, bt, dur, n + AS + 12, 118, mono=False)
# crashes at section starts
add(DR, 0, .2, 49, 112)
for k in range(NV): add(DR, (INTRO + k * VB) * 4, .2, 49, 116); add(DR, (INTRO + k * VB) * 4, .2, 57, 96)
add(DR, (INTRO + NV * VB) * 4, .2, 49, 118)

FINAL_HIT = (TOTAL - 1) * BAR + 3 * BEAT
N = int(round((FINAL_HIT + A.tail) * sr))
END_BEAT = PRE + TOTAL * 4 + 12            # keep FluidSynth rendering past the tail

def write(path, chans, pre=PRE):
    # pre > 0: render version (pre-roll + track-delay compensation); pre = 0: plain score on the grid (kept in midi/)
    mid = mido.MidiFile(ticks_per_beat=TPB); tr = mido.MidiTrack(); mid.tracks.append(tr)
    msgs = [(0, 0, mido.MetaMessage('set_tempo', tempo=TEMPO_US))]
    for c in chans:
        if c != DR:
            msgs.append((0, 1, mido.Message('program_change', channel=c, program=PROG[c])))
            msgs.append((0, 1, mido.Message('control_change', channel=c, control=10, value=PAN[c])))
        msgs.append((0, 1, mido.Message('control_change', channel=c, control=7, value=VOL[c])))
        msgs.append((0, 1, mido.Message('control_change', channel=c, control=91, value=REV.get(c, 40))))
        adv = ADV.get(c, 0) if pre else 0
        for (b, dur, n, v) in ev.get(c, []):
            msgs.append((round((pre + b) * TPB) - adv, 3, mido.Message('note_on', channel=c, note=n, velocity=v)))
            msgs.append((round((pre + b + dur) * TPB) - adv, 2, mido.Message('note_off', channel=c, note=n, velocity=0)))
    if pre: msgs.append((round(END_BEAT * TPB), 4, mido.Message('control_change', channel=15, control=7, value=100)))
    msgs.sort(key=lambda m: (m[0], m[1])); t = 0
    for (tk, _, m) in msgs: tr.append(m.copy(time=tk - t)); t = tk
    mid.save(path)
def render(mid, wav):
    subprocess.run(['fluidsynth', '-ni', '-q', '-g', '0.22', '-r', str(sr), '-O', 'float', '-F', wav, SF, mid], check=True, capture_output=True)
CUT = int(round(PRE * BEAT_MIDI * sr)) + LAT
def rd(p):
    x, r = sf.read(p, dtype='float64'); assert r == sr and x.shape[1] == 2
    x = x[CUT:]
    x = x[:N].copy() if len(x) >= N else np.vstack([x, np.zeros((N - len(x), 2))])
    x[:44] *= np.linspace(0, 1, 44)[:, None]        # 1 ms fade-in (only pre-attack noise lives there)
    return x
def wr(p, x):
    assert np.abs(x).max() < 1.0
    sf.write(p, x, sr, subtype='PCM_16')

jobs = [(f'st_{CHN[c]}', [c]) for c in BAND + ALT] + [('band', BAND), ('alt', ALT)]
for n, chans in jobs: write(f'{S}/{n}.mid', chans)
with ThreadPoolExecutor(4) as ex: list(ex.map(lambda j: render(f'{S}/{j[0]}.mid', f'{S}/{j[0]}.wav'), jobs))
# MIDI without pre-roll, kept next to the audio (time 0 = start of the WAV files)
write(f'{O}/midi/altyapi_{NAME}.mid', BAND, pre=0); write(f'{O}/midi/ezgi_alti_{NAME}.mid', ALT, pre=0)

band = rd(S + '/band.wav'); alt = rd(S + '/alt.wav')
db = lambda v: 20 * np.log10(v + 1e-12)
rms = lambda x: np.sqrt((x ** 2).mean())
# ---- default level of the under-vocal stem: RMS relative to the band in the bars where it plays -------------
amask = np.zeros(N, bool)
for bi, (ch, kind, k, vb) in enumerate(bars):
    if kind in ('voc', 'voc3', 'voc4'): amask[int(bi * BAR * sr):int((bi + 1) * BAR * sr)] = True
ks = 10 ** (A.ezgi_alti_db / 20) * rms(band[amask]) / rms(alt[amask])
alt = alt * ks

# ---- mastering: one gain + look-ahead peak limiter on the band; the stem gets the same gain, no limiter -----
def _release(g, a):
    out = np.empty_like(g); e = 1.0
    for i in range(g.shape[0]):
        t = g[i]
        if t < e: e = t
        else: e = a * e + (1 - a) * t
        out[i] = e
    return out
try:
    from numba import njit
    _release = njit(_release)
except Exception as ex_:
    print('numba not available, slow limiter loop:', ex_)
def limiter(x, ceil, head=None, look_s=0.003, rel_s=0.080):
    """Look-ahead peak limiter. Returns (y, gain); |y| <= ceil - head is guaranteed (head: per-sample headroom to
    leave free, here the peak envelope of the under-vocal stem). Does nothing where |x| is already below that."""
    pk = np.abs(x).max(1)
    lim = ceil if head is None else ceil - head
    g = np.minimum(1.0, lim / np.maximum(pk, 1e-12))
    if g.min() >= 1.0: return x.copy(), g
    L = int(look_s * sr) // 2 * 2
    gm = minimum_filter1d(g, size=L + 1, origin=-(L // 2), mode='nearest')      # min over [n, n+L]: gain needed soon
    e = _release(gm, float(np.exp(-1.0 / (rel_s * sr))))                         # instant attack, exponential release
    gs = uniform_filter1d(e, size=L + 1, origin=L // 2, mode='nearest')          # mean over [n-L, n]: smooth the attack
    gs = np.minimum(gs, g)                                                       # numerical safety (already true analytically)
    return x * gs[:, None], gs
meter = pyloudnorm.Meter(sr)
def truepeak(x): return float(np.abs(resample_poly(x, 4, 1, axis=0)).max())
def fade(x):
    f = int(0.4 * sr); x = x.copy(); x[-f:] *= np.linspace(1, 0, f)[:, None]; return x
ceil_db = -1.5
while True:
    CEIL = 10 ** (ceil_db / 20)
    g = 10 ** (-9 / 20) / np.percentile(np.abs(band), 99.9)
    for it in range(12):
        # the band is limited to (ceiling - peak envelope of the stem), so that altyapi + ezgi_alti never exceeds the ceiling
        head = maximum_filter1d(np.abs(alt * g).max(1), size=int(0.02 * sr), mode='nearest')
        y, gr = limiter(band * g, CEIL, head); L = meter.integrated_loudness(fade(y))
        if abs(L - A.lufs) < 0.02: break
        g *= 10 ** ((A.lufs - L) / 20)
    a_out = fade(y); s_out = fade(alt * g)
    r_out = a_out + s_out                      # rehber is the exact sum; no second limiter
    assert np.abs(r_out).max() <= CEIL * (1 + 1e-9) and np.abs(a_out).max() <= CEIL * (1 + 1e-9)
    tp = max(truepeak(a_out), truepeak(r_out))
    if db(tp) <= -1.05 or ceil_db < -3: break
    ceil_db -= 0.2
gr_db = -db(gr); top = np.argsort(gr_db)[::-1]; worst = []
for i in top:
    if all(abs(i - j) > sr // 2 for j in worst): worst.append(int(i))
    if len(worst) == 5: break
print(f'[{NAME}] key {KEY}: master gain {g:.3f} ({db(g):.2f} dB), limiter ceiling {ceil_db:.1f} dBFS, altyapi {L:.2f} LUFS, '
      f'max gain reduction {gr_db.max():.2f} dB, time with >0.5 dB reduction {100 * (gr_db > 0.5).mean():.2f} %, >2 dB {100 * (gr_db > 2).mean():.2f} %, '
      f'true peak {db(tp):.2f} dBTP, stem factor {ks:.3f}')
print(f'[{NAME}] largest gain reductions at (s, bar, dB):', [(round(i / sr, 2), int(i / sr / BAR), round(float(gr_db[i]), 1)) for i in worst])
wr(f'{O}/altyapi_{NAME}.wav', a_out); wr(f'{O}/ezgi_alti_{NAME}.wav', s_out); wr(f'{O}/rehber_{NAME}.wav', r_out)

# ---- zaman_<name>.json ---------------------------------------------------------------------------------------
R = lambda v: round(float(v), 4)
bt0 = lambda bi: bi * BAR
def barinfo(bi):
    ch, kind, k, vb = bars[bi]
    return {'olcu': bi, 'bolum_ici_olcu': vb, 'baslangic': R(bt0(bi)), 'bitis': R(bt0(bi + 1)), 'rol': ROLE[kind], 'tur': kind,
            'akorlar': [CHNAME[c] for c in ch], 'dereceler': list(ch), 'vurus_zamanlari': [R(bt0(bi) + i * BEAT) for i in range(4)]}
notes = []
for m in sorted(mel, key=lambda m: (m['olcu'], m['vurus'], m['kanal'], m['midi'])):
    ch, kind, k, vb = bars[m['olcu']]
    notes.append({'parti': m['parti'], 'enstruman': m['enstruman'], 'bolum': 'giris' if k < 0 else ('bitis' if k >= NV else 'kita'),
                  'kita': k + 1 if 0 <= k < NV else None, 'olcu': m['olcu'], 'bolum_ici_olcu': vb, 'vurus': m['vurus'],
                  'midi': m['midi'], 'nota': m['nota'], 'baslangic': R(bt0(m['olcu']) + m['vurus'] * BEAT), 'sure': R(m['sure_vurus'] * BEAT),
                  'hiz': m['hiz'], 'tek_ses': m['tek_ses']})
KEYTR = {'C': 'Do majör (C)', 'G': 'Sol majör (G)'}.get(KEY, KEY + ' majör')
Z = {'baslik': "Ali Baba'nın Çiftliği", 'varyant': NAME, 'ezgi': 'Old MacDonald Had a Farm (geleneksel, kamu malı), çift hızda: her ölçüde bir cümle',
     'ton': KEYTR, 'do': KEY, 'ton_degisimi': None, 'olcu': '4/4', 'tempo_bpm': BPM, 'vurus_sn': round(BEAT, 6), 'olcu_sn': round(BAR, 6),
     'toplam_olcu': TOTAL, 'muzik_bitis_sn': R(TOTAL * BAR), 'son_vurus_sn': R(FINAL_HIT), 'dosya_suresi_sn': R(N / sr), 'kuyruk_sn': A.tail,
     'ornekleme_hz': sr,
     'key_legend': 'baslangic/bitis = start/end (s, from the start of the WAV files; time 0 = downbeat of bar 0, no count-in); olcu = bar index (0-based); '
                   'bolum_ici_olcu = bar inside its section; vurus = beat inside the bar (0-based, quarter notes); akorlar = chord on each of the 4 beats; '
                   'kitalar = verses; hayvan_sesi = animal slot (ses1/ses2 = downbeats of verse bars 6 and 7); ezgi_notalari = melody notes; '
                   'parti: "lead" = loud brass/glockenspiel tune (inside altyapi), "ezgi_alti" = soft tune under the vocal (separate stem); '
                   'sure = duration (s); hiz = MIDI velocity; tek_ses = monophonic on that instrument',
     'dosyalar': {'altyapi': f'altyapi_{NAME}.wav', 'ezgi_alti': f'ezgi_alti_{NAME}.wav', 'rehber': f'rehber_{NAME}.wav',
                  'midi_altyapi': f'midi/altyapi_{NAME}.mid', 'midi_ezgi_alti': f'midi/ezgi_alti_{NAME}.mid',
                  'not': 'altyapi = ezgi_alti HARİÇ tam orkestra (giriş, ö1/ö3 cevapları ve bitişteki yüksek lead dahil). rehber = altyapi + ezgi_alti. '
                         'ezgi_alti doğrusal (limitersiz) ve altyapi ile aynı ana kazançta; miks seviyesi serbestçe değiştirilebilir.'},
     'ana_kazanc': {'kazanc_dB': R(db(g)), 'limiter_tavan_dBFS': ceil_db, 'hedef_LUFS_altyapi': A.lufs,
                    'ezgi_alti_varsayilan_seviye_dB': A.ezgi_alti_db,
                    'ezgi_alti_seviye_notu': 'ezgi_alti RMS değeri, çaldığı ölçülerde (kıta ö0, ö2, ö4, ö5) orkestra RMS değerine göre bu kadar dB'},
     'gecikme_telafisi': {'aciklama': 'Sesi geç açılan enstrümanların notaları ızgaradan bu kadar ms ÖNCE tetiklenir (negatif iz gecikmesi); '
                                      'json içindeki nota zamanları ızgara (hedef) zamanlarıdır. midi/ klasöründeki dosyalar telafisiz, ızgara üzerindedir.',
                          'one_alma_ms': {CHN[c]: round(1000 * t * BEAT / TPB, 1) for c, t in ADV.items()}},
     'tonlama': {'lead_do': nm(LEAD_DO), 'ezgi_alti_do': nm(ALT_DO), 'eslik_kaydirma_yarim_ses_(G_referans)': AS,
                 'bas_kokleri': {CHNAME[c]: nm(ROOT[c]) for c in DEG}, 'akor_dizilimleri': {CHNAME[c]: [nm(n) for n in CH[c]] for c in DEG},
                 'yuksek_cevap': [nm(LEAD_DO + iv) for iv, _, _ in ANS], 'yuksek_cevap_glockenspiel': [nm(LEAD_DO + iv + 12) for iv, _, _ in ANS],
                 'vokal_alti_A_cumlesi': [nm(ALT_DO + iv) for iv, _, _ in PHA], 'vokal_alti_tekrarli_do': nm(ALT_DO),
                 'vokal_alti_yumusak_cevap': [nm(ALT_DO + iv) for iv, _, _ in ANS],
                 'vokal_alti_enstruman': 'klarnet (GM 71) + bir oktav üstünde hafif glockenspiel (GM 9)'},
     'form': {'giris_olcu': INTRO, 'kita_olcu': VB, 'kita_sayisi': NV, 'bitis_olcu': END,
              'kita_ici': ['ö0: vokal satır 1 — alttan A cümlesi (do do do sol, la la sol), akor I I IV I',
                           'ö1: enstrümantal cevap "E-I-E-I-O" (mi mi re re do), yüksek: trompet+brass+glockenspiel, akor I V7 I I',
                           'ö2: vokal satır 2 — alttan A cümlesi, akor I I IV I', 'ö3: enstrümantal cevap (yüksek), akor I V7 I I',
                           'ö4: vokal satır 3 — alttan tekrarlı do (sekizlik), akor I',
                           'ö5: vokal satır 4 "Dinle bak, dinle bak!" — alttan yumuşak cevap (mi mi re re do), akor I V7 I I',
                           'ö6: HAYVAN SESİ 1 (yalnız kick + hafif hi-hat + yumuşak bas), akor I',
                           'ö7: HAYVAN SESİ 2 (aynı ince doku; ölçünün en sonunda trampet girişi), akor I']},
     'giris': {'baslangic': 0.0, 'bitis': R(INTRO * BAR), 'olculer': [barinfo(i) for i in range(INTRO)]},
     'kitalar': []}
for k in range(NV):
    an, l2, l3 = VERSES[k]; v0 = INTRO + k * VB
    Z['kitalar'].append({'kita': k + 1, 'hayvan': an, 'ilk_olcu': v0, 'baslangic': R(bt0(v0)), 'bitis': R(bt0(v0 + VB)),
        'olcu_baslangiclari': [R(bt0(v0 + i)) for i in range(VB)],
        'akorlar': [[CHNAME[c] for c in bars[v0 + i][0]] for i in range(VB)],
        'satir1': {'soz': "Ali Baba'nın bir çiftliği var", 'baslangic': R(bt0(v0)), 'bitis': R(bt0(v0 + 1))},
        'cevap1': {'baslangic': R(bt0(v0 + 1)), 'bitis': R(bt0(v0 + 2))},
        'satir2': {'soz': l2, 'baslangic': R(bt0(v0 + 2)), 'bitis': R(bt0(v0 + 3))},
        'cevap2': {'baslangic': R(bt0(v0 + 3)), 'bitis': R(bt0(v0 + 4))},
        'satir3': {'soz': l3, 'baslangic': R(bt0(v0 + 4)), 'bitis': R(bt0(v0 + 5))},
        'satir4': {'soz': 'Dinle bak, dinle bak!', 'baslangic': R(bt0(v0 + 5)), 'bitis': R(bt0(v0 + 6))},
        'hayvan_sesi': {'baslangic': R(bt0(v0 + 6)), 'bitis': R(bt0(v0 + 8)), 'ses1_baslangic': R(bt0(v0 + 6)), 'ses2_baslangic': R(bt0(v0 + 7)),
                        'trampet_girisi': R(bt0(v0 + 7) + 3.5 * BEAT)},
        'olculer': [barinfo(v0 + i) for i in range(VB)]})
e0 = INTRO + NV * VB
Z['bitis'] = {'baslangic': R(bt0(e0)), 'muzik_bitis': R(TOTAL * BAR), 'son_vurus': R(FINAL_HIT), 'ilk_son_olcu_vurusu': R(bt0(TOTAL - 1)),
              'olculer': [barinfo(e0 + i) for i in range(END)]}
Z['ezgi_notalari_aciklama'] = ('lead: trompet = ana ses; brass aynı sesi ve bir oktav altını, glockenspiel bir oktav üstünü çalar. '
                               'ezgi_alti: klarnet = ana ses; hafif glockenspiel bir oktav üstünü çalar. Zamanlar nota başlangıcıdır (ızgara).')
Z['ezgi_notalari'] = notes
json.dump(Z, open(f'{O}/zaman_{NAME}.json', 'w'), ensure_ascii=False, indent=1)

# ---- data for the verification script ------------------------------------------------------------------------
json.dump({'name': NAME, 'key': KEY, 'bpm': BPM, 'BEAT': BEAT, 'BAR': BAR, 'BEAT_MIDI': BEAT_MIDI, 'TOTAL': TOTAL, 'INTRO': INTRO, 'VB': VB, 'NV': NV,
           'END': END, 'N': N, 'sr': sr, 'CUT': CUT, 'LAT': LAT, 'gain': g, 'ceil_db': ceil_db, 'ks': ks, 'alt_db': A.ezgi_alti_db,
           'max_gr_db': float(gr_db.max()), 'gr_frac_gt_0p5db': float((gr_db > 0.5).mean()), 'gr_frac_gt_2db': float((gr_db > 2).mean()),
           'gr_worst': [(i / sr, float(gr_db[i])) for i in worst],
           'bars': [(list(ch), kind, k, vb) for ch, kind, k, vb in bars], 'mel': mel, 'chn': {str(c): n for c, n in CHN.items()},
           'events': {CHN[c]: sorted(ev.get(c, [])) for c in BAND + ALT},
           'adv_ticks': {CHN[c]: t for c, t in ADV.items()}, 'TPB': TPB, 'PRE': PRE, 'TEMPO_US': TEMPO_US, 'AS': AS, 'LEAD_DO': LEAD_DO, 'ALT_DO': ALT_DO, 'ROOT': ROOT, 'FIFTH': FIFTH, 'CH': CH},
          open(f'{S}/meta.json', 'w'), ensure_ascii=False)
print(f'[{NAME}] bars {TOTAL}, bar {BAR:.5f} s, music end {TOTAL * BAR:.3f} s, final hit {FINAL_HIT:.3f} s, file {N / sr:.3f} s')
