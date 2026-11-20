"""F# renderer's per-tick YM register log (wav/idNN_*.ticks.txt) against the Python model that gate_sound.py proved
against the emulator (gate A: 6305/6305 ticks). Same engine start (clean), same cap (150 ticks)."""
import glob, os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import vcommon
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ymmodel import *
D = vcommon.work('sound')
recs = load_records(os.path.join(D, 'records.bin'))
ok = n = 0
regs = set()
for i in range(54):
    f = glob.glob(D + f'/wav/id{i:02d}_*.ticks.txt')[0]
    fs = []
    for line in open(f):
        body = line.split(': ', 1)[1].strip()
        fs.append([tuple(int(x) for x in p[1:].split('=')) for p in body.split()] if body else [])
    m = Sound(recs); m.trigger(i)
    ms = []
    for t in range(len(fs)):
        ms.append(m.tick())
    for a, b in zip(fs, ms):
        n += 1; ok += (a == b)
        regs.update(r for r, v in a)
print(f'F# log vs model: {ok}/{n} ticks identical; registers ever written: {sorted(regs)}')
