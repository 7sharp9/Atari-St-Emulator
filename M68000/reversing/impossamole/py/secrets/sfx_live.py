"""Live YM write log for a sound index: patch a trigger into the running game (RAM only, in this process), watch $ff8800..$ff8803.
Patch: the main-loop call at $b1bc (jsr $1ab8a) is redirected to a stub at $80000 (free RAM) that, when byte $80100 is non-zero, loads D0 = byte $80101,
D1 = byte $80102, clears the flag and calls the real sound entry $1c840, then jumps to $1ab8a.  The game code, the disk and the repo are untouched."""
import sys, re
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from repl import *
SNAP = 'scratchpad/impossamole/agents/unpoked/s11/seg11_shaft_exit.snap'
STUB = bytes.fromhex('4a3900080100' '671a' '7000' '103900080101' '423900080100' '123900080102' '4eb90001c840' '4ef90001ab8a')
assert len(STUB) == 6 + 2 + 2 + 6 + 6 + 6 + 6 + 6 == 40, len(STUB)
# entry filter at $1c840: the first instruction (tst.b $bb7a.l, 6 bytes) becomes jmp $80200; the filter drops every call from the game unless
# byte $80103 is set (our own trigger sets it), so the log holds only the triggered effect.
FILTER = bytes.fromhex('4a3900080103' '6602' '4e75' '423900080103' '4ef90001c84c')

def install(r):
    b = STUB + b'\0' * ((-len(STUB)) % 4)
    for i in range(0, len(b), 4):
        r.cmd('w %x %s' % (0x80000 + i, b[i:i+4].hex()))
    f = FILTER + b'\0' * ((-len(FILTER)) % 4)
    for i in range(0, len(f), 4):
        r.cmd('w %x %s' % (0x80200 + i, f[i:i+4].hex()))
    r.cmd('w 1c840 4ef90008')
    r.cmd('w 1c844 0200%s' % r.mem(0x1c846, 2).hex())
    assert r.mem(0x1c840, 6).hex() == '4ef900080200'
    r.cmd('w b1bc 4eb90008')
    r.cmd('w b1c0 00000c39')
    assert r.mem(0xb1bc, 8).hex() == '4eb9000800000c39'

def trigger(r, idx, param=0):
    r.cmd('w 80100 01%02x%02x01' % (idx, param))

WATCH = re.compile(r'WATCH: step=(\d+) pc=\$([0-9a-f]+) WriteByte \$00ff88(0[0-3]) <- \$([0-9a-f]+)')
def parse(lines):
    out = []
    for l in lines:
        m = WATCH.search(l)
        if m: out.append((int(m.group(1)), int(m.group(2), 16), int(m.group(3), 16), int(m.group(4), 16)))
    return out

def live(idx, steps=1500000, snap=SNAP, param=0, hold=None):
    r = Repl(snap)
    install(r)
    r.cmd('s 30000')
    ram_state = r.mem(0x1d0a2, 0x50), r.b(0x1cc79), r.b(0x1cc78)
    r.cmd('watch ff8800 4')
    trigger(r, idx, param)
    r.cmd(f's {steps}')
    log = parse(r.err)
    live_ram = None
    return r, log, ram_state

def groups(log):
    """split the raw write log into (register, value) pairs, in order (ff8800 <- reg select, ff8802 <- data)."""
    regs = []; cur = None
    for step, pc, addr, val in log:
        if addr == 0: cur = val
        elif addr == 2 and cur is not None: regs.append((step, pc, cur, val))
    return regs

if __name__ == '__main__':
    idx = int(sys.argv[1], 0)
    r, log, st = live(idx, 400000)
    g = groups(log)
    print(len(log), 'raw writes', len(g), 'register writes')
    for x in g[:60]: print(x)
    r.close()
