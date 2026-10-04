"""Print the game-level call sequence of one main-loop iteration from an ATARI_TRACE_EVENTS log.
usage: evt_frame.py file.evt <anchorAddr> [skip]
anchor = a routine called once per iteration (call target).  Shows, for the (skip)th iteration, every
call whose *caller* pc is in COMMAND.PRG ($c470..$1f274) or is the trap#3 dispatcher ($a652), with
trap-3 calls labelled by service number, nesting depth tracked on the game stack only (interrupt
bodies are skipped), repeated identical siblings collapsed."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from evt_stats import load
T3 = [0xa6d6,0xaad8,0xab3a,0xa6fa,0xa86c,0xaa52,0xab5e,0xad10,0xad7c,0xaf08,0xaf70,0xafa0,0xb0d2,0xb0da,0xb0fc,0xb108,
      0xa6d4,0xaf08,0xbab8,0xb116,0xb12c,0xaf92,0xaa5a,0xbaba,0xa6d4,0xbac0,0xbb32,0xa6d4,0xbb34,0xa6d4,0xa6d4]
start, recs = load(sys.argv[1]); anchor = int(sys.argv[2], 16); skip = int(sys.argv[3]) if len(sys.argv) > 3 else 1
idx = [i for i, r in enumerate(recs) if r[4] == 3 and r[2] == anchor]
a, b = idx[skip], idx[skip + 1]
print("iteration steps", recs[a][0], "->", recs[b][0], "len", recs[b][0] - recs[a][0], "anchor calls", len(idx))
GAME = lambda pc: 0xc470 <= pc < 0x1f274
stack = []          # entries: 'g' game call frame, 'o' other
inint = 0
out = []
for sc, pc, tgt, op, kind, fl in recs[a:b]:
    if kind == 6: inint += 1; stack.append('i'); continue
    if kind == 4:
        if stack: 
            t = stack.pop()
            if t == 'i': inint -= 1
        continue
    if inint: 
        if kind == 3: stack.append('x')
        continue
    if kind == 3:
        if pc == 0xa652:
            n = T3.index(tgt) if tgt in T3 else -1
            out.append((len([s for s in stack if s=='g']), sc, f"TRAP3[{n}] -> ${tgt:04x}"))
            stack.append('x')
        elif GAME(pc):
            out.append((len([s for s in stack if s=='g']), sc, f"call ${tgt:06x} from ${pc:06x}"))
            stack.append('g')
        else: stack.append('x')
    elif kind == 5 and GAME(pc):
        out.append((len([s for s in stack if s=='g']), sc, f"trap #{op&0xf} from ${pc:06x}"))
# collapse repeats
prev = None; cnt = 0; first = 0
def flush():
    if prev: print(f"{'  '*prev[0]}{prev[2]}" + (f"  x{cnt}" if cnt > 1 else "") + f"   [@+{first-recs[a][0]}]")
for d, sc, s in out:
    if prev and (d, s) == (prev[0], prev[2]): cnt += 1; continue
    flush(); prev = (d, sc, s); cnt = 1; first = sc
flush()
