"""Live note-on log of the music module: bp $1dd22 (the common tail of every note), read D0 (raw note byte), A0 (channel struct $1f4ba/$1f52c/$1f59e),
transpose 64(A0), length 66(A0), tempo $1eb36 and the step counter.  Saves a JSON list."""
import sys, json
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from repl import *
from prng import parse_regs
def log_notes(snap, n=400, maxstep=3000000, out=None):
    r = Repl(snap)
    ev = []; t = 0
    for i in range(n):
        o = r.cmd(f'bp 1dd22 {maxstep}')
        hit = [l for l in o if 'breakpoint' in l and ' hit ' in l]
        if not hit: break
        t += int(hit[0].split('after ')[1].split()[0])
        rg = parse_regs(o)
        a0 = rg['A0']; ch = (a0 - 0x1f4ba) // 0x72
        ev.append(dict(t=t, ch=ch, d0=rg['D0'] & 0xffff, trans=r.w(a0 + 64) if False else int.from_bytes(r.mem(a0 + 64, 2), 'big', signed=True),
                       length=r.w(a0 + 66), tempo=r.w(0x1eb36), a2=int.from_bytes(r.mem(a0 + 4, 4), 'big'), instr=r.w(a0 + 104)))
        r.cmd('s 1')
    r.close()
    if out: json.dump(ev, open(out, 'w'))
    return ev
if __name__ == '__main__':
    snap, n, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    ev = log_notes(snap, n, out=out)
    print(len(ev), 'note-ons; first', ev[:6])
