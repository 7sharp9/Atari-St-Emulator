"""The object table `$23044` on a trap: sel.snap's slot 2 (the 6-frame looping object over the exit) is overwritten
with type 6 of the graphics set's type list (`212(A5)+112`, `$2759c + 6*$22`: a one-shot, 15-frame trap whose stamp is
code 4), the exit cells (222, 33..34) are poked to `$24` (object 2, code 4), and lemmings 0 and 1 are set down on the
flat ground left of it facing right (position pokes, inputs). Per arm it prints slot 2's flags and frame and both
records each tick (36,000 steps), and a `hits` census of the kill `$8c0a` and the trap's sound call `$8c16`.
Run from M68000/ (ATARI_NOTRACE is set here):
  uv run python reversing/lemmings/py/trapbusy.py <out dir>
"""
import os, struct, subprocess, sys
out = sys.argv[1]
os.makedirs(out, exist_ok=True)
SNAP, DISK = 'scratchpad/lemmings/sel.snap', 'scratchpad/lemmings/lemmings.st'
def run(name, body):
    p = os.path.join(out, name + '.txt')
    open(p, 'w').write('\n'.join(body + ['q']) + '\n')
    return subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', SNAP, 'repl', '--disk-a', DISK],
                          input=open(p).read(), capture_output=True, text=True, env=dict(os.environ, ATARI_NOTRACE='1')).stdout
def hexline(o, n):
    return [bytes(int(t, 16) for t in l.split()) for l in o.splitlines()
            if len(l.split()) == n and all(len(t) == 2 for t in l.split())]
# type 6's record, read from the snapshot so the copy is the game's own bytes
t6 = hexline(run('type6', ['m %x 36' % (0x2759c + 6 * 0x22)]), 36)[0]
slot2 = 0x23044 + 2 * 0x22
copy = ['w %x %s' % (slot2 + i, t6[i:i + 4].hex()) for i in range(0, 36, 4)]   # the last long also writes slot 3's flags (0)
ARMS = {  # name: (trap cells, lemming 0 x, lemming 1 x)
    'control': (0x00, 880, 872), 'alone': (0x24, 880, None), 'busy': (0x24, 880, 872), 'rearmed': (0x24, 880, 856)}
for name, (cell, x0, x1) in ARMS.items():
    pre = copy + ['w %x %02x000000' % (0x62f80 + r * 0x198 + 222, cell) for r in (33, 34)]
    for i, x in enumerate((x0, x1)):
        base = 0x23484 + i * 0x2c
        if x is None:   # park lemming 1 in the pen, where it was
            continue
        pre += ['w %x %04x0087' % (base, x), 'w %x 00010000' % (base + 8), 'w %x 00000000' % (base + 14)]
    samp = []
    for i in range(48): samp += ['m %x 4' % slot2, 'm 23484 88', 's 36000']
    o = run(name, pre + samp)
    h = run(name + '_hits', pre + ['hits 1728000 8c0a 8c16 8bea'])
    print('%s (cells %02x, x0 %s, x1 %s) hits: %s' % (name, cell, x0, x1, ' '.join(
        l.split()[0] + '=' + l.split()[1] for l in h.splitlines() if l.strip().startswith('$00'))))
    sl, rec = hexline(o, 4), hexline(o, 88)
    last = None
    for t, (s, r) in enumerate(zip(sl, rec)):
        fl, fr = struct.unpack('>HH', s)
        ls = []
        for i in range(2):
            b = r[i * 0x2c:(i + 1) * 0x2c]
            ls.append('L%d (%d,%d) %s%s' % (i, *struct.unpack('>HH', b[:4]), b[14:18].hex(), ' dead' if b[24] else ''))
        key = (fl, fr, ls[0], ls[1].split(')')[1])
        if key != last:
            print(' tick %2d slot2 flags %d frame %2d  %s  %s' % (t, fl, fr, ls[0], ls[1]))
            last = key
