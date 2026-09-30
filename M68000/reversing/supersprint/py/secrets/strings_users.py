"""strings_users.py - every printable string (>=3 chars) in ss.img (TEXT+DATA+BSS image) with its address and its users
(pea/lea/move.l #, absolute .l, PC-relative refs found in ss.asm, and absolute longwords in the image bytes)."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reach, sscfg
raw = open(sscfg.IMG, 'rb').read()
ins = reach.load(); th = reach.thunks()
# also ss.asm only covers TEXT <1bfd0; DATA range refs come from absolute/imm operands.
pat = re.compile(rb'[\x20-\x7e]{3,}')
strs = []
for m in pat.finditer(raw):
    strs.append((reach.TEXT0 + m.start(), m.group().decode('latin1')))
# refs: any operand mentioning $addr in range of image
users = {}
for a, t in ins:
    for m in re.finditer(r'\$([0-9a-f]{4,8})', t):
        v = int(m.group(1), 16)
        users.setdefault(v, []).append((a, t))
# absolute longwords in the image
lw = {}
for off in range(0, len(raw) - 3, 2):
    v = int.from_bytes(raw[off:off + 4], 'big')
    if reach.TEXT0 <= v < reach.TEXT0 + len(raw):
        lw.setdefault(v, []).append(reach.TEXT0 + off)
for a, s in strs:
    hits = []
    for v in range(a - 0, a + len(s) + 1):
        hits += [('%x:%s' % (x, t)) for x, t in users.get(v, [])]
        hits += [('lw@%x' % x) for x in lw.get(v, [])]
    print('%06x  %-40r  %s' % (a, s[:40], ' | '.join(hits[:4])))
