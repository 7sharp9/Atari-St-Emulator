import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
r = Ram(sys.argv[1] if len(sys.argv) > 1 else sscfg.SNAP_RACE)
offs = [-78,-98,-102,-106,-3602,-1722,-4936,-110,-118,-122,-126,-86,-90,-134,-138,-142,-146,-94,-1910,-4940,-1906,-4944,-82,-1196,-8076,-4080,-130,-6130,-6126,-114]
for o in offs: print('%6d(A4) = $%06x' % (o, r.g(o)))
