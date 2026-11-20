"""Pad path $25a6e (refuel, thrust leaves the pad) and the ceiling thrust cut $255de, driven in REPL runs.

  python pad_ceiling.py          from scratchpad/virus/drive/g_game2.snap (live game on the pad) and fl/f4.snap

Drives (hits counts instruction starts; every run is a fresh resume):
  pad, unpoked      hits 200000 255d4 25a6e 25aae 25a88 255f8      fuel is $0ff4, so fuel + $19 > $1000 and $25aae never stores (control)
  pad, fuel poked   ww 32a2e 100 (POKE) first: two pad ticks add $19 each, fuel $0100 -> $0132
  thrust            mouse down l; s 40000; hits 400000 ...        $25a6e 0, $255f8 (thrust taken) > 0
  ceiling           f4.snap: bp 255de; D2 before and after the bclr at $255de (y < $c900 signed)
"""
import os, re, subprocess, sys
_p = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_p))
import vcommon as V
ROOT = V.ROOT


def repl(snap, lines):
    p = subprocess.run(['dotnet', 'exec', os.path.join(ROOT, 'bin', 'Debug', 'net8.0', 'M68000.dll'), 'resume', snap, 'repl'],
                       input='\n'.join(lines + ['q']) + '\n', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=ROOT,
                       env=dict(os.environ, ATARI_NOTRACE='1'))
    return p.stdout


def hits(out):
    return {int(m.group(1), 16): int(m.group(2)) for m in re.finditer(r'^\s+\$([0-9a-f]+)\s+(\d+)\s+first', out, re.M)}


def mem(out):
    """Hex dump lines of the `m` commands, in order."""
    r = []
    for l in out.split('\n'):
        l = l.strip()
        if re.fullmatch(r'([0-9a-f]{2} )+[0-9a-f]{2}|[0-9a-f]{2}', l):
            r.append(bytes.fromhex(l.replace(' ', '')))
    return r


G = V.work('drive', 'g_game2.snap')
F4 = V.work('fl', 'f4.snap')
H = 'hits 200000 255d4 25a6e 25aae 25a88 255f8'
o = repl(G, ['m 32a2e 2', H, 'm 32a2e 2'])
h = hits(o)
m = mem(o)
print(f'pad, unpoked (control): ticks {h[0x255d4]}, pad {h[0x25a6e]}, refuel stores {h[0x25aae]}, fuel ${m[0].hex()} -> ${m[1].hex()}')
o = repl(G, ['ww 32a2e 100', 'm 32a2e 2', H, 'm 32a2e 2'])
h = hits(o)
m = mem(o)
print(f'pad, fuel poked to $0100: ticks {h[0x255d4]}, pad {h[0x25a6e]}, refuel stores {h[0x25aae]}, fuel ${m[0].hex()} -> ${m[1].hex()} '
      f'(+${int(m[1].hex(), 16) - int(m[0].hex(), 16):x} = {h[0x25aae]} x $19)')
o = repl(G, ['mouse down l', 's 40000', 'hits 400000 255d4 25a6e 25aae 255f8'])
h = hits(o)
print(f'thrust held: ticks {h[0x255d4]}, pad {h[0x25a6e]}, refuel stores {h[0x25aae]}, thrust path $255f8 {h[0x255f8]}')
o = repl(F4, ['bp 255de 60000000', 'r', 's 1', 'r', 'm 270b0 4'])
d2 = re.findall(r'\bD2:([0-9a-f]{8})', o)
y = mem(o)[-1][2:4].hex()
print(f'ceiling: D2 before the bclr ${d2[0]} -> ${d2[-1]} after, y = ${y} (below $c900 signed: {0x8000 <= int(y, 16) < 0xc900})')
