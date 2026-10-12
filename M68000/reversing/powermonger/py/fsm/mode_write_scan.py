#!/usr/bin/env python3
"""Whole-image census of every instruction that can write an entity's mode byte (31) or previous mode (30).

usage: mode_write_scan.py [<ram image>] [lo hi]     (default scratchpad/pm123/win/m1_ready.ram, $10a6..$1c48a)

Three independent scans of the text segment:

  A  decode at EVERY even address (not a linear sweep, so data or a desynced sweep cannot hide an instruction) and keep
     each decode whose destination operand is d16(An)/d8(An,Xn) with displacement 28..31 and whose operand size makes
     it cover byte 30 or 31: move/clr/st/sf/s<cc>/addq/subq/addi/subi/ori/andi/eori/bset/bclr/bchg/neg/not/tas/movem.
     Each hit is tagged 'L' when the same address starts an instruction of the linear listing (tools/disassemble.py
     --all) and '-' when it is only an off-alignment decode (data or the middle of another instruction).
  B  raw byte patterns for an immediate store of a value V to offset 31 / 30, any An, any size, for V in TARGETS:
     move.b #V,31|30(An), move.w #xxV,30(An), move.w #Vxx,30(An), move.l #....,28(An) with V in byte 31 or 30,
     and the d8(An,Xn) forms; reported with alignment.
  C  walk-path terminator words $7d02+V (the $0e walk sets mode := word - $7d02, ai.md `$0e` row) anywhere in the image.

Output: stdout, and $PM_WORK/out/mode_write_scan.txt (default scratchpad/pm_fig).
"""
import os, re, struct, sys, subprocess

here = os.path.dirname(os.path.abspath(__file__))
root = here
while not os.path.exists(os.path.join(root, 'tools', 'rdis.py')):
    parent = os.path.dirname(root)
    if parent == root:
        sys.exit('repo root (tools/rdis.py) not found')
    root = parent
sys.path.insert(0, os.path.join(root, 'tools'))
from disassemble import Disassembler  # noqa: E402

work = os.environ.get('PM_WORK') or os.path.join(root, 'scratchpad/pm_fig')
outdir = os.path.join(work, 'out')
os.makedirs(outdir, exist_ok=True)
args = sys.argv[1:]
ram_path = args[0] if args else os.path.join(root, 'scratchpad/pm123/win/m1_ready.ram')
LO, HI = (int(args[1], 16), int(args[2], 16)) if len(args) >= 3 else (0x10a6, 0x1c48a)
ram = open(ram_path, 'rb').read()
dis = Disassembler(ram, rom_base=0)
TARGETS = [0x04, 0x64, 0x66, 0x70]

out = []


def p(s=''):
    print(s)
    out.append(s)


# linear listing: the instruction starts of a sweep
lst = subprocess.run([sys.executable, os.path.join(root, 'tools', 'disassemble.py'), '--rom', ram_path, '--base', '0',
                      '--all', '%x' % LO, '%x' % HI], capture_output=True, text=True).stdout
starts = {int(m.group(1), 16) for m in re.finditer(r'^\s*\$([0-9a-f]+):', lst, re.M)}

WRITE_OPS = re.compile(r'^(move|clr|st|sf|s[a-z]{2}|addq|subq|addi|subi|add|sub|ori|andi|eori|or|and|eor|bset|bclr|bchg|'
                       r'neg|negx|not|tas|movem|addx|subx)\b')
DEST = re.compile(r'(?:^|,|\s)(-?\d+)\(A(\d)(?:,[DA]\d\.[wl])?\)$')
SIZE = {'b': 1, 'w': 2, 'l': 4}

p('ram %s, scan $%x..$%x, %d linear instruction starts' % (os.path.relpath(ram_path, root), LO, HI, len(starts)))
p()
p('== A: decodes at every even address whose destination covers byte 30 or 31 ==')
hitsA = []
for a in range(LO, HI, 2):
    try:
        text, nxt = dis.decode_one(a)
    except Exception:
        continue
    op = text.split()[0]
    if not WRITE_OPS.match(op) or op.startswith(('cmp', 'tst', 'btst')):
        continue
    m = DEST.search(text)
    if not m:
        continue
    d = int(m.group(1))
    sz = SIZE.get(op.split('.')[-1], 1) if '.' in op else 1
    if op.startswith('movem'):
        sz = 64                      # register list: be generous
    if d <= 31 and d + sz > 30:
        hitsA.append((a, text, 'L' if a in starts else '-'))
for a, t, al in hitsA:
    p('  %s $%06x  %s' % (al, a, t))
p('A: %d hits, %d on the linear listing' % (len(hitsA), sum(1 for h in hitsA if h[2] == 'L')))
p()

p('== B: raw immediate stores of V to byte 31/30 (any An), V in %s ==' % ' '.join('$%02x' % v for v in TARGETS))


def w(a):
    return struct.unpack_from('>H', ram, a)[0]


nB = 0
for a in range(LO, HI - 8, 2):
    op = w(a)
    hit = None
    if op & 0xf1ff == 0x117c and w(a + 4) in (30, 31) and (w(a + 2) & 0xff) in TARGETS:
        hit = 'move.b #$%02x,%d(A%d)' % (w(a + 2) & 0xff, w(a + 4), (op >> 9) & 7)
    elif op & 0xf1ff == 0x11bc and (w(a + 4) & 0xff) in (30, 31) and (w(a + 2) & 0xff) in TARGETS:
        hit = 'move.b #$%02x,%d(A%d,Xn)' % (w(a + 2) & 0xff, w(a + 4) & 0xff, (op >> 9) & 7)
    elif op & 0xf1ff == 0x317c and w(a + 4) == 30 and (w(a + 2) & 0xff in TARGETS or w(a + 2) >> 8 in TARGETS):
        hit = 'move.w #$%04x,30(A%d)' % (w(a + 2), (op >> 9) & 7)
    elif op & 0xf1ff == 0x31bc and (w(a + 4) & 0xff) == 30 and (w(a + 2) & 0xff in TARGETS or w(a + 2) >> 8 in TARGETS):
        hit = 'move.w #$%04x,30(A%d,Xn)' % (w(a + 2), (op >> 9) & 7)
    elif op & 0xf1ff == 0x217c and w(a + 6) in (28, 30) and (w(a + 4) & 0xff in TARGETS or w(a + 4) >> 8 in TARGETS
                                                             or w(a + 2) & 0xff in TARGETS or w(a + 2) >> 8 in TARGETS):
        hit = 'move.l #$%04x%04x,%d(A%d)' % (w(a + 2), w(a + 4), w(a + 6), (op >> 9) & 7)
    if hit:
        nB += 1
        p('  %s $%06x  %s' % ('L' if a in starts else '-', a, hit))
p('B: %d hits' % nB)
p()

p('== C: walk-path terminator words $7d02+V ==')
nC = 0
for v in TARGETS:
    word = 0x7d02 + v
    for a in range(LO & ~1, len(ram) - 1, 2):
        if w(a) == word and a < 0x80000:
            nC += 1
            p('  $%06x  $%04x (mode $%02x)' % (a, word, v))
p('C: %d hits over $%x..$80000 (whole RAM below the screen)' % (nC, LO & ~1))
open(os.path.join(outdir, 'mode_write_scan.txt'), 'w').write('\n'.join(out) + '\n')
