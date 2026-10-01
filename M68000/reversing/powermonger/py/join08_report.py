"""join08_report.py <out.txt> [men-hex,...]: parse the `m` dumps written by join08_watch.py (before/after or the sampled
trace) into one row per dump: lead mode/arrival/dwell/quota46, group state/men/first man/owner, lord 0 troops_field(8),
then per man: side(5) flags(7) mode(31)/arrival(30) dwell(18) link46 grp42.  Must use the same man list as the generator."""
import re, sys

HEX = re.compile(r'^(?:[0-9a-f]{2} ?)+$')
lines = [l.strip() for l in open(sys.argv[1], errors='replace') if HEX.match(l.strip())]
men = [0x32, 0x64, 0xc8, 0xfa, 0x12c, 0x15e]
if len(sys.argv) > 2:
    men = [int(x, 16) for x in sys.argv[2].split(',')]
per = 4 + len(men)
b = lambda row: bytes(int(x, 16) for x in row.split())
w = lambda d, o: (d[o] << 8) | d[o+1]
print(f"{len(lines)} dump lines, {len(lines)//per} samples; per sample: lead | grp | lord0 | men {[hex(m) for m in men]}")
for i in range(len(lines)//per):
    r = lines[i*per:(i+1)*per]
    lead, grp, tgt, lord = b(r[0]), b(r[1]), b(r[2]), b(r[3])
    # grp dump starts at record -48: -48 owner, -36 first man, -24 men, -12 lead, 0 state
    gs = f"owner {w(grp,0)} first {w(grp,12):#x} men {w(grp,24)} lead {w(grp,36):#x} state {w(grp,48)}"
    ls = f"lead {lead[31]:#04x}/{lead[30]:#04x} dwell {w(lead,18):#x} q46 {w(lead,46)} cell ({lead[8]},{lead[10]})"
    lo = f"L0 side {lord[5]} troops {w(lord,8)}"
    ms = ' | '.join(f"{(b(x))[5]:3d} {b(x)[7]:02x} {b(x)[31]:02x}/{b(x)[30]:02x} d{w(b(x),18):02x} l{w(b(x),46):x} g{w(b(x),42):x}" for x in r[4:])
    print(f"[{i}] {gs} || {ls} || {lo} || {ms}")
