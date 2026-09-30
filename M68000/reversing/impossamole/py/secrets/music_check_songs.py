"""Songs 0-2 started from the gameplay snapshot: model (from row 0) against the live note-on log.  Prints matches and timing agreement."""
import sys, json
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
from music_seq import *
SNAP = ROOT + '/scratchpad/impossamole/agents/unpoked/s11/seg11_shaft_exit.snap'
r = ram(SNAP)
for s in range(3):
    try: live = json.load(open(WORK + f'/data/music_song{s}.json'))
    except Exception as e: print('song', s, 'no log', e); continue
    ev, ch, g = run_song(r, s, tempo0=int.from_bytes(r[0x1eb36:0x1eb38], 'big'), max_events=len(live) + 5)
    n = len(live)
    ok = sum(1 for a, l in zip(ev, live) if (a[2], a[3], a[4], a[5], a[6]) == (l['ch'], l['d0'] & 0xff, l['trans'], l['length'], l['instr']))
    tim = sum(1 for k in range(1, n) if abs((live[k]['t'] - live[k-1]['t']) / 12000.0 - (ev[k][1] - ev[k-1][1])) <= 1.0)
    # absolute timing of the k-th event vs its modelled VBL
    dev = max(abs(live[k]['t'] / 12000.0 - ev[k][1]) for k in range(n))
    print(f'song {s}: {n} live note-ons, {ok} equal (channel, note, transpose, length, instrument) in order; gaps within 1 VBL {tim}/{n-1}; max |live - model| start time {dev:.2f} VBLs')
