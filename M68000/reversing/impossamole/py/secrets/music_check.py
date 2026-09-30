"""Compare the event-level sequencer (music_seq.py) with the live note-on log (music_live.py, bp $1dd22): locate the live sequence in the model's stream
(the snapshot starts mid-song), then count events whose channel, raw note, transpose, length and instrument agree, and whether the
gaps between successive events, in VBLs (steps / 12000), equal the modelled row times."""
import sys, json
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
from music_seq import *
def check(snap, song, jsonfile, tempo0=6):
    ram_ = ram(snap)
    live = json.load(open(jsonfile))
    ev, ch, g = run_song(ram_, song, tempo0=tempo0, max_events=8000)
    key = lambda e: (e[2], e[3], e[4], e[5], e[6])                # channel, note, transpose, length, instrument
    lkey = lambda l: (l['ch'], l['d0'] & 0xff, l['trans'], l['length'], l['instr'])
    L = [lkey(l) for l in live]
    best = None
    for j in range(len(ev) - len(L) + 1):
        ok = sum(1 for a, b in zip(ev[j:j+len(L)], L) if key(a) == b)
        if best is None or ok > best[0]: best = (ok, j)
        if ok == len(L): break
    ok, j = best
    # timing: gaps in VBLs
    gt = 0; gn = 0
    for a in range(1, len(L)):
        dt_live = (live[a]['t'] - live[a-1]['t']) / 12000.0
        dv = ev[j + a][1] - ev[j + a - 1][1]
        gn += 1
        if abs(dt_live - dv) <= 1.0: gt += 1
    return dict(song=song, live_events=len(L), matched=ok, model_index=j, model_row=ev[j][0], timing_ok=gt, timing_n=gn, model_events=len(ev))
if __name__ == '__main__':
    print(check(sys.argv[1], int(sys.argv[2]), sys.argv[3]))
