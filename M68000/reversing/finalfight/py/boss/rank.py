"""rank.py <dump>: DAMND's health, level (+96), defence class (+55) and damage-table pointer (+92) 30 frames into a run in which 168(A5) was poked before the init (runs.sh r0, r31)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dd import *
D = Dump(sys.argv[1])
print('%s: 168(A5)=%d hp %d/%d +96=%d def(+55)=%d 92=%06x' % (os.path.basename(sys.argv[1]), D.u16(30, 0xff8000 + 168), D.s16(30, BOSS + 24), D.u16(30, BOSS + 28), D.u8(30, BOSS + 96), D.u8(30, BOSS + 55), D.u32(30, BOSS + 92) & 0xffffff))
