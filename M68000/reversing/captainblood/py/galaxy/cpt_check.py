"""cpt_check.py <cpt_load.txt> <depacked BLOOD.CPT>: the two 512-byte table dumps in cpt_load.sh's output (before, after the load
click) against the galaxy table in BLOOD.CPT (file offset $1b2 = $18 header + 8 + $100 state + ($ba4e - $b9bc)).
Prints entries equal to the file before and after, status bytes equal, and whether any hz200 in 0..65535 reproduces the file's
galaxy through galaxy_model (a search hit would mean the file's galaxy came from this generator)."""
import sys, re, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from galaxy_model import galaxy
L = [l.strip() for l in open(sys.argv[1]) if re.match(r'^[0-9a-f]{2}( [0-9a-f]{2}){63,}$', l.strip())]
assert len(L) == 2, len(L)
before, after = (bytes.fromhex(l.replace(' ', '')) for l in L)
cpt = open(sys.argv[2], 'rb').read()[0x1b2:0x1b2 + 512]
n = lambda t: sum(t[4*i:4*i+4] == cpt[4*i:4*i+4] for i in range(128))
print('table before the load click == BLOOD.CPT: %d/128 entries' % n(before))
print('table after the load click  == BLOOD.CPT: %d/128 entries' % n(after))
print('status byte (+3) boot galaxy == CPT galaxy: %d/128' % sum(before[4*i+3] == cpt[4*i+3] for i in range(128)))
tgt = [int.from_bytes(cpt[4*i:4*i+2], 'big') for i in range(128)]
hit = None
for hz in range(1 << 16):
    m, rej = galaxy(hz)
    if rej <= 100000 and m[127] == tgt[127] and m[126] == tgt[126]: hit = hz; break
print('hz200 in 0..65535 reproducing the CPT galaxy:', hit)
