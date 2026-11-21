# Wait for the BS-Roformer candidate: a WAV whose name contains "(Vocals)" in sep/out_rof that has stopped growing.
# Checks every 60 s for at most 12 minutes (the limit set by the task). Writes gecici/bekle_rof.json.
import glob, json, os, sys, time
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import SEP, CACHE

LIMIT = 12 * 60
t0 = time.time(); last = None; status = 'missing'; path = None
while True:
    v = sorted(glob.glob(SEP + '/out_rof/*(Vocals)*.wav'))
    if v:
        path = v[0]; sz = os.path.getsize(path)
        running = os.system("pgrep -f 'audio-separator.*bs_roformer' > /dev/null") == 0
        if last == sz and sz > 1000000 and (not running or time.time() - os.path.getmtime(path) > 90):
            status = 'ready'; break
        last = sz; status = 'growing'
    if time.time() - t0 > LIMIT:
        break
    time.sleep(60 if not v else 15)
res = dict(status=status, path=path, waited_s=round(time.time() - t0, 1), started_at=time.strftime('%H:%M:%S', time.gmtime(t0)),
           ended_at=time.strftime('%H:%M:%S', time.gmtime()),
           separator_still_running=os.system("pgrep -f 'audio-separator.*bs_roformer' > /dev/null") == 0)
os.makedirs(CACHE, exist_ok=True)
json.dump(res, open(CACHE + '/bekle_rof.json', 'w'), indent=1)
print(res)
