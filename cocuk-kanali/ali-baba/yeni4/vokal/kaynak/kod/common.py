# Shared helpers for choosing / preparing the vocal source of v2_2.
# Everything is on the timeline of v2_2.mp3 decoded by ffmpeg (44.1 kHz).
import json, os, glob, subprocess, numpy as np, soundfile as sf, scipy.signal as ss

A = '/home/user/ring-tokat-3d/cocuk-kanali/ali-baba'
O = A + '/yeni4/vokal/kaynak'
CACHE = O + '/gecici'                 # deletable cache (decoded mix, intermediate json)
SEP = '/tmp/claude-0/-home-user-ring-tokat-3d/bd9d6832-1bf0-57ca-8544-ce6f4befd453/scratchpad/sep'
SR = 44100
TEMPO = json.load(open(A + '/yeni4/analiz/tempo/tempo.json'))
LAT = json.load(open(A + '/yeni4/analiz/tempo/lattice.json'))
BEAT = LAT['beat_period_s']           # refined beat period of the decoded mp3 (0.5714133 s)
PH0 = LAT['phase_first_beat_s']       # time of beat 0
BAR = 4 * BEAT
VERSE_DB = [v['first_downbeat'] for v in TEMPO['downbeat']['verses']]   # 7 verse downbeats
DUR = 105.0


def decode_mix():
    """mix decoded by ffmpeg: mono and stereo, 44.1 kHz, float32 WAV (no clipping, no dither)"""
    os.makedirs(CACHE, exist_ok=True)
    pm, ps = CACHE + '/mix_44k_mono.wav', CACHE + '/mix_44k_stereo.wav'
    if not os.path.exists(pm):
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', A + '/v2_2.mp3',
                        '-ar', str(SR), '-ac', '1', '-c:a', 'pcm_f32le', pm], check=True)
    if not os.path.exists(ps):
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', A + '/v2_2.mp3',
                        '-ar', str(SR), '-c:a', 'pcm_f32le', ps], check=True)
    return pm, ps


def load_mix(stereo=False):
    """Mix on the ffmpeg timeline. Mono = (L+R)/2 computed here from the float stereo decode
    (ffmpeg's own '-ac 1' gives 0.7071*(L+R) for float output and 0.5*(L+R) for 16-bit output;
    the time axis is identical, only the gain differs, so the mean is formed here to avoid that quirk)."""
    pm, ps = decode_mix()
    x, sr = sf.read(ps, dtype='float64'); assert sr == SR
    return x if stereo else x.mean(1)


def stem_paths():
    """returns dict name -> dict(vocals=path, instrumental=path or None)"""
    out = {}
    for name, folder in (('mdx', 'out_mdx'), ('rof', 'out_rof')):
        v = sorted(glob.glob(f'{SEP}/{folder}/*(Vocals)*.wav'))
        i = sorted(glob.glob(f'{SEP}/{folder}/*(Instrumental)*.wav'))
        if v:
            out[name] = dict(vocals=v[0], instrumental=i[0] if i else None)
    return out


def load_stem(path, mono=True):
    x, sr = sf.read(path, dtype='float64'); assert sr == SR, sr
    if mono and x.ndim > 1:
        x = x.mean(1)
    return x


def load_words():
    d = json.load(open(A + '/v2_2_words.json'))
    w = d['words'] if isinstance(d, dict) else d
    return [x for x in w if x.get('type') == 'word']


def regions():
    """Time regions on the mix timeline.
    sung_words : word intervals of the words file (all 105 words, incl. the sung animal sounds)
    sung_bars  : the 4 sung bars of every verse
    inst       : purely instrumental stretches, with safety margins against the voice:
                 intro 0.30 s .. first verse downbeat - 0.70 s; per verse: end of sung bar 3 + 0.50 s .. next verse
                 downbeat - 0.70 s; outro: end of the last sung bar + 0.50 s .. 104.5 s
    tails      : the first 0.5 s after the last sung bar of every verse (voice release / reverb tail)
    pre        : the 0.70 .. 0.05 s before every verse downbeat (the singer's breath intake sits here: it is voice,
                 not bleed, so it is kept out of 'inst' and reported separately)
    """
    w = load_words()
    sung_words = [(x['start'], x['end']) for x in w]
    sung_bars, inst, tails, pre = [], [], [], []
    inst.append((0.30, VERSE_DB[0] - 0.70))
    for i, d in enumerate(VERSE_DB):
        sung_bars.append((d, d + 4 * BAR))
        pre.append((d - 0.70, d - 0.05))
        end = VERSE_DB[i + 1] if i + 1 < len(VERSE_DB) else None
        a = d + 4 * BAR
        tails.append((a, a + 0.5))
        if end is not None:
            inst.append((a + 0.5, end - 0.70))
        else:
            inst.append((a + 0.5, DUR - 0.5))
    return dict(sung_words=sung_words, sung_bars=sung_bars, inst=inst, tails=tails, pre=pre)


def mask_from(intervals, n, sr=SR):
    m = np.zeros(n, bool)
    for a, b in intervals:
        m[max(0, int(round(a * sr))):min(n, int(round(b * sr)))] = True
    return m


def db(x, floor=1e-12):
    return 10 * np.log10(np.maximum(x, floor))


def rms_db(x):
    return float(db(np.mean(np.asarray(x, float) ** 2)))


def bandpass(x, lo, hi, order=6):
    if lo is None or lo <= 0:
        sos = ss.butter(order, hi, btype='low', fs=SR, output='sos')
    elif hi is None or hi >= SR / 2:
        sos = ss.butter(order, lo, btype='high', fs=SR, output='sos')
    else:
        sos = ss.butter(order, [lo, hi], btype='band', fs=SR, output='sos')
    return ss.sosfiltfilt(sos, x)


def stft(x, nfft=2048, hop=512):
    f, t, S = ss.stft(x, SR, window='hann', nperseg=nfft, noverlap=nfft - hop, boundary='zeros', padded=True)
    return f, t, S
