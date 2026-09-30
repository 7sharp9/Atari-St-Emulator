"""Start music song N (0-2) from the gameplay snapshot by the same RAM-only stub method as sfx_live.py (stub at $80000 calls $1d6ec with D0 = song),
then log note-ons (bp $1dd22)."""
import sys, json
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from repl import *
from prng import parse_regs
SNAP = 'scratchpad/impossamole/agents/unpoked/s11/seg11_shaft_exit.snap'
STUB = bytes.fromhex('4a3900080100' '6714' '7000' '103900080101' '423900080100' '4eb90001d6ec' '4ef90001ab8a')
def start_song(song):
    r = Repl(SNAP)
    b = STUB + b'\0' * ((-len(STUB)) % 4)
    for i in range(0, len(b), 4): r.cmd('w %x %s' % (0x80000 + i, b[i:i+4].hex()))
    r.cmd('w b1bc 4eb90008'); r.cmd('w b1c0 00000c39')
    assert r.mem(0xb1bc, 8).hex() == '4eb9000800000c39'
    r.cmd('s 30000')
    r.cmd('w 80100 01%02x0000' % song)
    return r
def log_notes(song, n, out):
    r = start_song(song)
    ev = []; t = 0
    for i in range(n):
        o = r.cmd('bp 1dd22 3000000')
        hit = [l for l in o if 'breakpoint' in l and ' hit ' in l]
        if not hit: break
        t += int(hit[0].split('after ')[1].split()[0])
        rg = parse_regs(o); a0 = rg['A0']; c = (a0 - 0x1f4ba) // 0x72
        ev.append(dict(t=t, ch=c, d0=rg['D0'] & 0xffff, trans=int.from_bytes(r.mem(a0 + 64, 2), 'big', signed=True),
                       length=r.w(a0 + 66), tempo=r.w(0x1eb36), a2=int.from_bytes(r.mem(a0 + 4, 4), 'big'), instr=r.w(a0 + 104)))
        r.cmd('s 1')
    end = (r.w(0x1eb2e), r.b(0xbb7a))
    r.close()
    json.dump(ev, open(out, 'w'))
    return ev, end
if __name__ == '__main__':
    song, n, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    ev, end = log_notes(song, n, out)
    print(len(ev), 'events; $1eb2e, $bb7a at end', end, ev[:2])
