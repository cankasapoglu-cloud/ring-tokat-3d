#!/usr/bin/env python3
# (a) delivered score MIDI files: tempo, bar count, lead / under-vocal notes per bar read directly from the MIDI (independent of zaman json)
# (b) what the builder cuts away before t = 0 (pre-roll): do early-triggered instruments lose their attack on the very first downbeat?
# usage: 04_midi_ve_baslangic.py <delivered folder> <my work folder> <my re-render folder> <out json>
import sys, json, filecmp
import numpy as np, mido, soundfile as sf
DEL, WORK, MINE, OUTJ = sys.argv[1:5]
P = lambda *a: print(*a, flush=True); R = {}
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']; nm = lambda m: f'{NAMES[m % 12]}{m // 12 - 1}'
KIND = ['iA', 'iANS', 'iA', 'iANS'] + ['voc', 'ans', 'voc', 'slot', 'slot', 'fill', 'voc', 'ans'] * 7 + ['ans', 'ans', 'roll', 'final']
for key in ('G', 'C'):
    r = R[key] = {}
    for f in (f'altyapi_{key}.mid', f'ezgi_alti_{key}.mid'):
        r[f + '_same_as_rerender'] = filecmp.cmp(f'{DEL}/midi/{f}', f'{MINE}/midi/{f}', shallow=False)
    mid = mido.MidiFile(f'{DEL}/midi/altyapi_{key}.mid'); tpb = mid.ticks_per_beat; t = 0; notes = {}; tempo = None; on = {}
    for m in mid.tracks[0]:
        t += m.time
        if m.type == 'set_tempo': tempo = m.tempo
        if m.type == 'note_on' and m.velocity > 0: on[(m.channel, m.note)] = (t, m.velocity)
        elif m.type in ('note_off', 'note_on') and (m.channel, m.note) in on:
            t0, v = on.pop((m.channel, m.note)); notes.setdefault(m.channel, []).append((t0 / tpb, (t - t0) / tpb, m.note, v))
    mid2 = mido.MidiFile(f'{DEL}/midi/ezgi_alti_{key}.mid'); t = 0; on = {}
    for m in mid2.tracks[0]:
        t += m.time
        if m.type == 'note_on' and m.velocity > 0: on[(m.channel, m.note)] = (t, m.velocity)
        elif m.type in ('note_off', 'note_on') and (m.channel, m.note) in on:
            t0, v = on.pop((m.channel, m.note)); notes.setdefault(m.channel, []).append((t0 / tpb, (t - t0) / tpb, m.note, v))
    last = max(b + d for ch in notes.values() for b, d, n, v in ch)
    r.update(tempo_us=tempo, bpm=60e6 / tempo, ticks_per_beat=tpb, channels={c: len(v) for c, v in sorted(notes.items())}, last_note_end_beat=last)
    P(f'[{key}] score MIDI: tempo {tempo} us/beat = {60e6 / tempo:.5f} BPM; notes per channel {r["channels"]}; last note ends at beat {last:.2f} (64 bars = 256 beats)')
    def per_bar(ch):
        out = {}
        for b, d, n, v in sorted(notes.get(ch, [])): out.setdefault(int(b // 4), []).append((round(b % 4, 3), nm(n), round(d, 2), v))
        return out
    for ch, lab in ((5, 'trumpet (lead)'), (4, 'glockenspiel (lead)'), (7, 'clarinet (under-vocal)'), (8, 'light glockenspiel (under-vocal)'), (0, 'bass')):
        pb = per_bar(ch); kinds = {}
        for b in range(64): kinds.setdefault(KIND[b], set()).add(' '.join(f'{bt:g}:{n}' for bt, n, d, v in pb.get(b, [])) or '(silent)')
        r[lab] = {k: sorted(v) for k, v in kinds.items()}
        P(f'[{key}] {lab}: notes per bar kind (beat:note), all bars of a kind:')
        for k, v in kinds.items(): P(f'      {k:5s} ' + '  ||  '.join(sorted(v)))
    # drum notes per bar kind (GM: 36 kick, 38 snare, 39 clap, 42 closed hat, 46 open hat, 49/57 crash, 55 splash, 54 tambourine, 43-50 toms, 56 cowbell, 76/77 wood blocks)
    pb = {}
    for b, d, n, v in notes.get(9, []): pb.setdefault(int(b // 4), set()).add(n)
    kinds = {}
    for b in range(64): kinds.setdefault(KIND[b], set()).add(tuple(sorted(pb.get(b, []))))
    r['drums'] = {k: [list(x) for x in sorted(v)] for k, v in kinds.items()}
    P(f'[{key}] drum notes used per bar kind:'); [P(f'      {k:5s} {sorted(v)}') for k, v in kinds.items()]
    # other chord instruments in slot bars and bar 5 beats 0-1 (score level)
    viol = []
    for ch in (1, 2, 3, 4, 5, 6):
        for b, d, n, v in notes.get(ch, []):
            bar = int(b // 4)
            if KIND[bar] == 'slot' or (KIND[bar] == 'fill' and b % 4 < 2): viol.append((ch, round(b, 2), nm(n)))
            elif b + d > (bar + 1) * 4 + 1e-6 and KIND[min(bar + 1, 63)] == 'slot': viol.append(('hangs into slot', ch, round(b, 2), round(d, 2)))
    r['score_notes_in_thin_places'] = viol[:20]; P(f'[{key}] notes of banjo/accordion/piano/glockenspiel/trumpet/brass written inside slot bars or bar-5 beats 0-1, or held into a slot bar: {len(viol)} {viol[:8]}')
    # (b) pre-roll
    S = f'{WORK}/{key}'; meta = json.load(open(f'{S}/meta.json')); CUT = meta['CUT']; g = meta['gain']; sr = 44100
    out = {}
    for st in ('band', 'st_bas', 'st_brass', 'st_davul', 'st_trompet', 'st_banjo', 'st_piyano', 'st_glockenspiel'):
        x, _ = sf.read(f'{S}/{st}.wav', start=CUT - 2205, stop=CUT + 4410); pre = np.abs(x[:2205]).max() * g; post = np.abs(x[2205:]).max() * g
        j = np.where(np.abs(x[:2205]).max(1) * g > 10 ** (-60 / 20))[0]
        out[st] = dict(peak_cut_away_dbfs=float(20 * np.log10(pre + 1e-12)), peak_first_100ms_dbfs=float(20 * np.log10(post + 1e-12)), cut_sound_starts_ms_before_t0=float((2205 - j[0]) / sr * 1000) if len(j) else 0.0)
    r['preroll'] = out
    P(f'[{key}] sound thrown away before t = 0 (last 50 ms of the pre-roll), after master gain: ' + '; '.join(f'{k}: peak {v["peak_cut_away_dbfs"]:.1f} dBFS, starts {v["cut_sound_starts_ms_before_t0"]:.1f} ms before t=0 (first 100 ms kept: {v["peak_first_100ms_dbfs"]:.1f})' for k, v in out.items() if v['peak_cut_away_dbfs'] > -80))
json.dump(R, open(OUTJ, 'w'), indent=1, ensure_ascii=False, default=str)
