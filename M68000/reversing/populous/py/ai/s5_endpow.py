"""s5_endpow.py - the two endgame-power scenarios: a snapshot with the computer's (side 1) mana poked.
  F: cg1.snap (evil population behind), mana 90000 -> armageddon's population test fails, flood twice
  M: live/A_log/f01065.snap (evil 1480 vs 607), mana 90000 -> armageddon
Writes $POP_WORK/ai/F0.snap and M0.snap. Then run cmdlog.py + livecheck.py per site on them and
join.py F|M (see ai.md 5)."""
import os
from aicfg import *
from livelib import Sess
import ai_ref as A

MANA1 = A.sidest(1) + 12                                  # $3b242, signed long


def make(src, dst, mana):
    S = Sess(src)
    S.cmd('w %x %08x' % (MANA1, mana))
    m = S.snapram(dst)
    S.close()
    print(dst, 'mana', A.mana(m, 0), A.mana(m, 1), 'pop', A.sl(m, A.sidest(0) + 8), A.sl(m, A.sidest(1) + 8),
          'frame', A.rw(m, A.FRAME))


if __name__ == '__main__':
    make(P('cg1.snap'), P('F0.snap'), 90000)
    make(os.path.join(AI, 'live', 'A_log', 'f01065.snap'), P('M0.snap'), 90000)
