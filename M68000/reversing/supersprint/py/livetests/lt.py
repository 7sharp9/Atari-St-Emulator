"""lt.py - shared helpers for the livetests scripts (thin layer over ai_econ/aiutil.Repl2).
Derives the repo root via sscfg; untracked data and snapshots go to scratchpad/supersprint/agents/livetests/data (sscfg.WORK)."""
import os, sys, struct, re, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(HERE, '..', 'ai_econ'))
import sscfg
from aiutil import Repl2, setwords, sx, A4
AI = os.path.join(sscfg.WORK, 'agents', 'ai_econ', 'data')   # read-only inputs from round 1
LT = os.path.join(sscfg.WORK, 'agents', 'livetests')
DATA = os.path.join(LT, 'data')
os.makedirs(DATA, exist_ok=True)
# 'qy'/'qx' are historical names: -3738 is Q x and -3746 Q y (mechanics.md, "Units"); bot.py reads them by offset
F = {'lap': -3906, 'drone': -3914, 'stun': -3810, 'wp': -3802, 'qy': -3738, 'qx': -3746, 'spd': -3730, 'cap': -3874,
     'hd': -3706, 'thd': -3714, 'acc': -3866, 'sx': -3690, 'sy': -3698, 'flags': -3826, 'div': -3882, 'chk': -3850,
     'tiles': -3842, 'wr': -3954, 'flag': -3778}
LO = A4 - 3960
def sample(r):
    b = r.mem(LO, 304)
    row = {}
    for k, off in F.items():
        o = A4 + off - LO
        row[k] = list(struct.unpack('>4h', b[o:o + 8]))
    return row
