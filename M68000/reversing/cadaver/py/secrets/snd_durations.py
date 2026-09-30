"""Per-sound summary by running the Python engine (proved against the game in snd_proof.py / snd_scenarios.py):
class, voices, priority, length in VBL frames until all voices are idle (or 'loops' if still busy after 6000 frames),
channels used (mixer tone/noise bits seen), distinct tone periods, plus literal PlaySound call sites found in the
main image (from sndcallers.py).  Writes snd_table.txt."""
import sys, os, collections, re
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
OUT = os.path.join(os.path.abspath(os.path.join(here, '..', '..', '..', '..')), 'scratchpad/cadaver/secrets_out'); os.makedirs(OUT, exist_ok=True)
from ram import ram
from cad_sound import Sound, REQ_TAB
base = ram()
# literal call sites
calls = collections.defaultdict(list)
L = []
for l in open(os.path.join(OUT, 'cad_all.asm')):
    m = re.match(r'\s+\$([0-9a-f]+): (.*)', l)
    if m: L.append((int(m.group(1), 16), m.group(2)))
for i, (a, t) in enumerate(L):
    if t.startswith('jsr $158f8') and a < 0x19000:
        for j in range(i - 1, max(0, i - 8), -1):
            mm = re.match(r'(moveq|move\.w|move\.l|move\.b) #\$?(-?[0-9a-f]+),D0$', L[j][1])
            if mm:
                v = mm.group(2); v = int(v, 10) if L[j][1].startswith('moveq') else int(v, 16); calls[v].append(a); break
rows = []
for k in range(62):
    e = REQ_TAB + 5 * k; pr = base[e]; kind = base[e + 1]
    s = Sound(base); s.play(k)
    frames = 0; tones = set(); noise = False; tonech = set()
    while frames < 6000:
        out = s.tick(); s.housekeeping(); frames += 1
        if any(out[1::2][:3] and 0 for _ in [0]): pass
        for v in range(3):
            per = out[2 * v] | (out[2 * v + 1] << 8); vol = out[8 + v]
            if vol and not (out[7] >> v) & 1: tones.add(per); tonech.add(v)
            if vol and not (out[7] >> (v + 3)) & 1: noise = True
        if (s.rb(0x162cc) & 7) == 0: break
    loops = frames >= 6000
    cls = 'queued' if pr & 0x80 else ('sfx' if kind in (1, 2) else 'prio3')
    rows.append((k, cls, kind, pr & 0x7f, 'loops' if loops else frames, sorted(tonech), 'noise' if noise else '-', len(tones), [hex(a) for a in calls.get(k, [])]))
with open(os.path.join(OUT, 'snd_table.txt'), 'w') as f:
    f.write('id class voices prio frames channels noise distinct_periods literal_call_sites\n')
    for r in rows: f.write(' '.join(str(x) for x in r) + '\n')
for r in rows: print(*r)
