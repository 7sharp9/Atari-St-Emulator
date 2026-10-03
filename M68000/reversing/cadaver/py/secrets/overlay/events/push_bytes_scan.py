"""a3: push_bytes_scan.py -- alignment-proof check of push_sites_scan.py: scan the raw bytes (not a listing) of the resident image ($001000-$019100 of gameplay_empire.snap and level1_loaded.snap) and of every overlay .bin for
the 16-bit displacement $0130 (= 304) used as d16(A5) (the instruction word before it has an A5-displacement effective address as source (low 6 bits $2d) or destination (bits 11-6 = $2d>>0 swapped: mask $0fc0 == $0b40)),
and the same for $0482 (1154) and for 152.  Prints counts per image; push_sites_scan.py's listing reaches 304(A5) in the same number of instructions iff no push hides in a misaligned stretch.
Usage (from M68000/): .venv/bin/python reversing/cadaver/py/secrets/overlay/events/push_bytes_scan.py"""
import sys, os, glob, struct
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../../..'))
OUTDIR = os.environ.get('OUTDIR') or os.path.join(ROOT, 'scratchpad/cadaver/s91_events'); os.makedirs(OUTDIR, exist_ok=True)   # scratch output (callcap json, caches, scan listings)
sys.path.insert(0, ROOT + '/tools')
from disassemble import ram_from_snap
def scan(data, base, lo, hi, disp):
    hits = []
    for off in range(lo - base, hi - base - 3, 2):
        if struct.unpack_from('>H', data, off + 2)[0] != disp: continue
        op = struct.unpack_from('>H', data, off)[0]
        if (op & 0x3f) == 0x2d or (op & 0x0fc0) == 0x0b40: hits.append(base + off)
    return hits
imgs = []
for tag in ('gameplay_empire', 'level1_loaded'):
    ram = ram_from_snap(ROOT + '/scratchpad/cadaver/%s.snap' % tag)
    imgs.append((tag + ' resident $1000-$19100', ram, 0, 0x1000, 0x19100))
for f in sorted(glob.glob(ROOT + '/scratchpad/cadaver/secrets_out/overlay/overlay_*.bin')):
    d = open(f, 'rb').read()
    if struct.unpack_from('>I', d, 0)[0] == len(d) - 4: d = d[4:]
    imgs.append((os.path.basename(f), d, 0x4c65e, 0x4c65e, 0x4c65e + len(d)))
for name, d, base, lo, hi in imgs:
    print('%-40s 304(A5): %2d   1154(A5): %2d   152(A5): %2d' % (name, len(scan(d, base, lo, hi, 304)), len(scan(d, base, lo, hi, 1154)), len(scan(d, base, lo, hi, 152))))

# cross-check against the listings: every byte-level hit must be the start of a listed instruction that mentions the same displacement
import re
def listing(path):
    d = {}
    for l in open(path).read().splitlines():
        m = re.match(r'\s*\$([0-9a-f]+)(?: \(\+[0-9a-f]+\))?:\s*(.*)', l)
        if m: d[int(m.group(1), 16)] = m.group(2)
    return d
pairs = [('gameplay_empire resident $1000-$19100', OUTDIR + '/whole_l0.asm'), ('level1_loaded resident $1000-$19100', OUTDIR + '/whole_l1.asm')]
for name, d, base, lo, hi in imgs:
    if name.endswith('.bin'): pairs.append((name, ROOT + '/scratchpad/cadaver/secrets_out/overlay/' + name.replace('.bin', '.lst')))
byname = {n: (d, b, lo, hi) for n, d, b, lo, hi in imgs}
print()
for name, lst in pairs:
    L = listing(lst); d, b, lo, hi = byname[name]
    for disp, pat in ((304, r'(?<![\d-])304\(A5\)'), (1154, r'(?<![\d-])1154\(A5\)'), (152, r'(?<![\d-])152\(A5\)')):
        miss = [hex(a) for a in scan(d, b, lo, hi, disp) if not (a in L and re.search(pat, L[a]))]
        print('%-40s %4d(A5): byte hits not matched by a listed instruction: %s' % (name, disp, miss))
