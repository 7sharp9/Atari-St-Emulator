"""a3: ev4_hits.py -- the same throw as ev4_drive.py (FIRE held 750,000 steps from the select165 checkpoint) with `hits` over every push site, to see which producers fire for one thrown urn that lands on an altar top
(event 4 yes; event 11 requires the landing z to be 0; event 1 is the hit-scan site $00fa62)."""
from probe import *
snap = ROOT + '/scratchpad/cadaver/s88/parent/full_A/g1/D1_W1125000_0/ck_79_select165.snap'
h = HH.H(snap); r = h.r
sites = {'a114': 1, 'fa62': 1, 'f328': 4, '9286': 10, 'f69c': 11, 'f9a2': 12, 'b0f0': 13, 'f0c8': 25, 'fe24': 'match', 'fe36': 'gate', 'fe5a': 'verb'}
r.cmd('kbd ff 80', 's 300')
hh = r.hits(750000, *[int(a, 16) for a in sites])
print({'%s(e%s)' % (a, sites[a]): hh.get(int(a, 16), 0) for a in sites})
r.cmd('kbd ff 00', 's 30000'); h.close()
