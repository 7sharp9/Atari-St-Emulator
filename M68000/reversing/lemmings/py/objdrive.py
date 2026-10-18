"""Object-map cell codes on lemming 0 of sel.snap: place it on level 1's flat ground next to the exit (a position poke,
an input), poke the two exit cells (column 222, rows 33 and 34) to a chosen code, and print the record's changes per
tick (36,000 steps) plus a `hits` census of the cell dispatch and the three handlers.
Run from M68000/ (ATARI_NOTRACE is set here):
  uv run python reversing/lemmings/py/objdrive.py <out dir> <code hex>... [--left]
code 11 is the level's own exit; 2..6 are mechanics.md "Collisions". --left starts the lemming at x=906 facing left
(the code-3 reversal). Rows 31..34 of that column hold the level's exit cells: `m 62f80+row*$198+222`.
"""
import os, struct, subprocess, sys
args = [a for a in sys.argv[1:] if not a.startswith('--')]
out, codes = args[0], [int(c, 16) for c in args[1:]]
left = '--left' in sys.argv
os.makedirs(out, exist_ok=True)
def run(name, body):
    p = os.path.join(out, name + '.txt')
    open(p, 'w').write('\n'.join(body + ['q']) + '\n')
    return subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', 'scratchpad/lemmings/sel.snap', 'repl',
                           '--disk-a', 'scratchpad/lemmings/lemmings.st'], input=open(p).read(), capture_output=True,
                          text=True, env=dict(os.environ, ATARI_NOTRACE='1')).stdout
for code in codes:
    pre = ['w 23484 038a0087', 'w 2348c ffff0000'] if left else ['w 23484 03660087']
    pre += ['w %x %02x000000' % (0x62f80 + r * 0x198 + 222, code) for r in (33, 34)]
    samp = []
    for i in range(40): samp += ['m 23484 44', 's 36000']
    o = run('c%x' % code, pre + samp)
    h = run('h%x' % code, pre + ['hits 1500000 8b6e 8aca 8b5c 8a62'])
    print('code %x hits: %s' % (code, ' '.join(l.split()[0] + '=' + l.split()[1] for l in h.splitlines() if l.strip().startswith('$00'))))
    last = None
    for i, l in enumerate(l.split() for l in o.splitlines() if len(l.split()) == 44 and all(len(t) == 2 for t in l.split())):
        b = bytes(int(t, 16) for t in l)
        key = (b[14:18].hex(), b[24], struct.unpack('>h', b[8:10])[0])
        if key != last:
            print(' tick', i, struct.unpack('>HH', b[:4]), 'dir', key[2], 'state', key[0], 'dead' if key[1] else '')
            last = key
