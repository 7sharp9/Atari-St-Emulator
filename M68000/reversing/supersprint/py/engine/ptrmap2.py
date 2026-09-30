import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
r = Ram(sys.argv[1] if len(sys.argv) > 1 else sscfg.SNAP_RACE)
for o in (-1192,-1188,-1184,-1180,-1176,-1172,-1170,-1168,-1166,-1164,-1162,-1160):
    print('%6d(A4) = $%08x  w=$%04x' % (o, r.g(o), r.gw(o)))
