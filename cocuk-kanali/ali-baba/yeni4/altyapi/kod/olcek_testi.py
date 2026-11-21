#!/usr/bin/env python3
# Tempo re-render test: builds the backing again at another tempo (default 105.30 BPM, key G) into a scratch folder,
# runs the full verification (dogrula.py: beat grid and every melody note measured in the audio) on that render, and
# compares its zaman json with the delivered one: every time must be scaled by exactly old_bpm / new_bpm, everything
# else (bars, beats, notes, velocities, chords, texts) must be unchanged.
# usage: olcek_testi.py <output folder with zaman_G.json> <scratch folder> [new bpm] [key]
import json, os, subprocess, sys, time
O, W = sys.argv[1:3]; BPM2 = float(sys.argv[3]) if len(sys.argv) > 3 else 105.30; KEY = sys.argv[4] if len(sys.argv) > 4 else 'G'
KOD = os.path.dirname(os.path.abspath(__file__)); O2 = os.path.join(W, f'out_bpm_{BPM2:.2f}'); W2 = os.path.join(W, f'work_bpm_{BPM2:.2f}')
t0 = time.time()
subprocess.run([sys.executable, f'{KOD}/build.py', '--bpm', str(BPM2), '--key', KEY, '--out', O2, '--work', W2], check=True)
t_build = time.time() - t0
env = dict(os.environ, DOGRULAMA_JSON=f'{O2}/dogrulama.json')
r = subprocess.run([sys.executable, f'{KOD}/dogrula.py', O2, W2, KEY], capture_output=True, text=True, env=env)
open(f'{O2}/dogrulama.txt', 'w').write(r.stdout + r.stderr)
D = json.load(open(f'{O2}/dogrulama.json'))
A = json.load(open(f'{O}/zaman_{KEY}.json')); B = json.load(open(f'{O2}/zaman_{KEY}.json'))
ratio = A['tempo_bpm'] / B['tempo_bpm']                    # new time = old time * ratio
TIME = {'baslangic', 'bitis', 'olcu_baslangiclari', 'vurus_zamanlari', 'ses1_baslangic', 'ses2_baslangic', 'sure', 'muzik_bitis_sn', 'son_vurus_sn',
        'vurus_sn', 'olcu_sn', 'muzik_bitis', 'son_vurus', 'ilk_son_olcu_vurusu', 'ses_basina_yer_sn'}
SKIP = {'tempo_bpm', 'ana_kazanc', 'gecikme_telafisi', 'dosya_suresi_sn'}
st = {'time_values': 0, 'time_max_err_ms': 0.0, 'other_values': 0, 'other_diff': 0, 'bad': []}
def walk(a, b, key, path):
    if key in SKIP: return
    if isinstance(a, dict):
        if set(a) != set(b): st['bad'].append(path + ': keys differ'); return
        for k in a: walk(a[k], b[k], k, f'{path}/{k}')
    elif isinstance(a, list):
        if len(a) != len(b): st['bad'].append(path + ': length differs'); return
        for i, (x, y) in enumerate(zip(a, b)): walk(x, y, key, f'{path}[{i}]')
    elif key in TIME and isinstance(a, (int, float)) and not isinstance(a, bool):
        e = abs(b - a * ratio); st['time_values'] += 1; st['time_max_err_ms'] = max(st['time_max_err_ms'], 1000 * e)
        if e > 1.2e-4: st['bad'].append(f'{path}: {a} -> {b}, expected {a * ratio:.4f}')        # json values are rounded to 0.1 ms
    else:
        st['other_values'] += 1
        if a != b: st['other_diff'] += 1; st['bad'].append(f'{path}: {a!r} != {b!r}')
walk(A, B, None, '')
dur_ok = abs((B['dosya_suresi_sn'] - B['kuyruk_sn']) - (A['dosya_suresi_sn'] - A['kuyruk_sn']) * ratio) < 1.2e-4
g = D[KEY]['grid']; nt = D[KEY]['notes_total']
res = {'old_bpm': A['tempo_bpm'], 'new_bpm': B['tempo_bpm'], 'key': KEY, 'expected_time_ratio': round(ratio, 8),
       'build_seconds': round(t_build, 1),
       'json_time_values_compared': st['time_values'], 'json_time_max_error_ms': round(st['time_max_err_ms'], 4),
       'json_other_values_compared': st['other_values'], 'json_other_values_different': st['other_diff'],
       'file_duration_old_new_s': [A['dosya_suresi_sn'], B['dosya_suresi_sn']], 'file_duration_minus_tail_scales': bool(dur_ok),
       'bar_s_old_new': [A['olcu_sn'], B['olcu_sn']], 'bar_s_expected_new': round(240 / BPM2, 6),
       'audio_fitted_bar_s_new': g['fitted_bar_s'], 'audio_fitted_bpm_new': g['fitted_bpm'], 'audio_kick_drift_whole_song_ms': g['drift_whole_song_ms'],
       'audio_melody_notes_checked_matched_new': [nt['checked'], nt['matched']],
       'verification_of_new_render_failed_checks': D['failed_checks'], 'mismatches': st['bad'][:20]}
res['ok'] = bool(not st['bad'] and dur_ok and not D['failed_checks'] and r.returncode == 0)
json.dump(res, open(f'{O}/olcek_testi.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
sys.exit(0 if res['ok'] else 1)
