"""overlay_map.py [overlay_levelN.bin] [base_hex] -> overlay_levelN.lst
Standalone structural map + recursive-descent listing of the level-code overlay (bytes as loaded at 2534(A5); the .bin
from extract_overlay.py WITHOUT its leading 4-byte length word is what RAM holds; this script accepts either and strips
the length if it equals len-4).  Header (big-endian words, offsets from base):
  +0 init routine (record 0 first word, called via $e298 with D0=0), +2 table1 (object-class use/touch), +4 table2 (spell
  effects), +6 table3 (timer expiry handlers), +8 list4 ((object id, value) save pairs, negative key ends), +10 constant,
  +12.. 7 unused records (ffff,0000), then records k=10..19 = creature classes 1..10: (class behaviour routine, event table).
Prints the header, every table with entry targets, every class record, then writes a listing whose code is found by
recursive descent from all these entries (bsr/bra/bcc/dbf/lea pc targets inside the overlay, both edges of conditionals)."""
import sys, struct, re, os
sys.path.insert(0, 'tools')
from disassemble import Disassembler
path = sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/cadaver/secrets_out/overlay/overlay_level0.bin'
base = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x4c65e
d = open(path, 'rb').read()
if struct.unpack_from('>I', d, 0)[0] == len(d) - 4: d = d[4:]
W = lambda o: struct.unpack_from('>H', d, o)[0]
S = lambda o: struct.unpack_from('>h', d, o)[0]
N = len(d)
dis = Disassembler(d, rom_base=base)
def rel(a): return a - base
print('overlay %d bytes at $%06x..$%06x' % (N, base, base + N))
print('header words 0-5:', ' '.join('%04x' % W(2 * i) for i in range(6)))
entries = {}   # offset -> label
EXTRA = {0x372: 'unreferenced helper (find object in room by id, result A0/D0)', 0x39c: 'unreferenced helper', 0x3c0: 'unreferenced helper', 0x402: 'unreferenced helper', 0x598: 'unreferenced helper (sign-compare direction chooser, called only by +39c)'} if 'level0' in path else {}
def add(o, lab):
    if 0 <= o < N and o not in entries: entries[o] = lab
add(W(0) + 2, 'init (record 0)')
# table1: entry count unknown, bound by smallest target
def offtable(start, n, lab):
    out = []
    for i in range(n):
        t = start + S(start + 2 * i); out.append(t); add(t, '%s[%d]' % (lab, i))
    return out
t1 = W(2); t2 = W(4); t3 = W(6); l4 = W(8)
n2 = W(t2) // 2; n3 = W(t3) // 2
print('header words 6,7 (Disk 2 overlays only):', '%04x %04x' % (W(12), W(14)))
print('table2 (spells) at +%x: %d entries' % (t2, n2)); T2 = offtable(t2, n2, 'spell')
print('table3 (timers) at +%x: %d entries' % (t3, n3)); T3 = offtable(t3, n3, 'timer')
# table1: find real count: first word/2 but bounded by smallest entry target >= start; entries whose target is past table start+first
# table1 is not sorted: first word is NOT the table size.  Table = words up to the smallest target offset seen so far.
T1 = []; lim = 1 << 30; i = 0
while t1 + 2 * i < lim:
    off = S(t1 + 2 * i); T1.append(t1 + off); lim = min(lim, t1 + off); i += 1
n1 = len(T1)
print('table1 (use/touch) at +%x: %d slots (smallest target +%x)' % (t1, n1, lim))
classes = {}
# class record array: offset 40 .. word0 (init routine) for the one-disk and Disk 2 levels 0-2; capped at 10 classes.  Disk 2's
# last two levels (pairs 21, 28) have other layouts (word0 = $1dc / $3c): records past word0 are then code, bounds-guarded below.
ncls = min(10, max(0, (W(0) - 40) // 4)) if W(0) < 0x100 else 4
for c in range(1, ncls + 1):
    k = 9 + c; a, b = W(4 * k), W(4 * k + 2)
    classes[c] = (a, b)
    if a + 2 < N: add(a + 2, 'class%d behaviour' % c)       # Disk 2 overlays: class 1's word is negative ($fbd6..): out of range, skipped
    if b and b + 2 < N and b % 2 == 0 and 0 < W(b) < 64:
        n = W(b) // 2
        for i in range(n):
            if b + 2 * i + 2 <= N - 2: add(b + S(b + 2 * i), 'class%d event[%d]' % (c, i))
for i, t in enumerate(T1): add(t, 'table1[%d]' % i)
# routines no bsr/jmp in the overlay reaches (found by reading the gaps; level 0 only): unreferenced helpers
for off, lab in EXTRA.items(): add(off, lab)
print('classes (behaviour record offset, event table offset):', {c: ('%x' % a, '%x' % b) for c, (a, b) in classes.items()})
# recursive descent
code = {}  # offset -> (text,size)
work = sorted(entries)
seen = set()
tgt = re.compile(r'\$([0-9a-f]+)')
while work:
    o = work.pop()
    while 0 <= o < N and o not in seen:
        seen.add(o)
        try:
            txt, nxt = dis.decode_one(base + o)
        except Exception:
            break
        code[o] = (txt, nxt - base - o)
        m = txt.split()[0]
        if m.startswith(('bsr', 'bra', 'b', 'dbf', 'dbra')) and not m.startswith(('bset', 'bclr', 'btst', 'bchg')):
            mm = tgt.findall(txt)
            if mm:
                t = int(mm[-1], 16) - base
                if 0 <= t < N and t not in entries and t not in seen: work.append(t)
        if 'PC) ==' in txt:
            mm = re.search(r'== \$([0-9a-f]+)', txt)
            if mm:
                t = int(mm.group(1), 16) - base
                if 0 <= t < N - 1 and not txt.startswith('jsr') and not txt.startswith('jmp'): pass
        o = nxt - base
        if m in ('rts', 'rte', 'bra', 'jmp') or txt.startswith(('bra ', 'jmp ')): break
        if txt.startswith('illegal'): break
# listing
out = []
o = 0
while o < N:
    if o in entries: out.append('; ---- +%03x  %s' % (o, entries[o]))
    if o in code:
        txt, sz = code[o]; out.append('  $%06x (+%03x): %s' % (base + o, o, txt)); o += sz
    else:
        out.append('  $%06x (+%03x): .word $%04x' % (base + o, o, W(o) if o + 1 < N else d[o])); o += 2
lst = os.path.splitext(path)[0] + '.lst'
open(lst, 'w').write('\n'.join(out) + '\n')
print('listing ->', lst, '; code bytes found', sum(s for _, s in code.values()), 'of', N)
