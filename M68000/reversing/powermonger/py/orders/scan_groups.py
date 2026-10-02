"""List the live groups of a snapshot: (side, k), group offset, lead, men, state, target, carried goods."""
import sys, os
from pathlib import Path
ROOT = Path(os.environ.get("M68000_ROOT", Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(ROOT / "tools"))
from disassemble import ram_from_snap
import pm_fsm_ref as P
GROUP = 0x51538

def groups(r):
    out = []
    m = P.Mem(r)
    for side in range(5):
        for k in range(6):
            g = GROUP + side * 0x13c + 0x4c + 2 * k
            own = m.ws(g - 48)
            if own <= 0:
                continue
            out.append(dict(side=side, k=k, off=g - GROUP, A3=g, own=own, men=m.wu(g - 24), lead=m.wu(g - 12),
                            first=m.wu(g - 36), state=m.wu(g), tgt=m.wu(g + 24), food=m.wu(g + 36), post=m.wu(g + 60),
                            goods=[m.wu(g + 84 + 12 * i) for i in range(8)]))
    return out

if __name__ == "__main__":
    for s in sys.argv[1:]:
        r = ram_from_snap(str(ROOT / s))
        print(s)
        for g in groups(r):
            print("  side %d k %d off %#x own %d men %d lead %#x first %#x state %d tgt %#x food %d post %d goods %s" % (
                g['side'], g['k'], g['off'], g['own'], g['men'], g['lead'], g['first'], g['state'], g['tgt'], g['food'], g['post'], g['goods']))
