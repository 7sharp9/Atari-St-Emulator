"""arm_census.py <snap>...: which `$65b4` decide arm each AI group would take in each snapshot (strategy.md "The commander AI").

For every command slot whose state byte (4(A0)) is 4, every group (D7 = 10..0) with `28() > 0` is run through `cmdai_ref._decide` on a copy of the
snapshot's RAM with its state forced to 6 (camp), and the arm the model reaches is counted (`TRACE`): getmen, escort, attack, food, food_none, getmen2, idle0,
idle_nomen, xfer.  A group in state 9, or 6 past its wait, is one `$6522` really decides for; the others are listed under "other state" so the table
shows what each arm would need.  `-v` prints one line per group: side, D7, state, men, food, pending, arm.

    cd M68000 && python reversing/powermonger/py/cmdai/arm_census.py [-v] <snap>...
"""
import collections
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get('M68000_ROOT', Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pm_fsm_ref as P  # noqa: E402
import cmdai_ref as C  # noqa: E402
from disassemble import ram_from_snap  # noqa: E402


def groups(snap):
    ram = ram_from_snap(snap)
    if len(ram) < 0x59000:
        return
    m0 = P.Mem(ram)
    A0 = C.CMD
    while A0 != C.CMD_END:
        if m0.bu(A0 + 4) == 4:
            side = m0.bu(A0)
            base = (C.GROUPS + C.sp16((side * 0x13c) & 0xffff)) & 0xfffff
            for D7 in range(10, -1, -2):
                A1 = base + D7
                D2 = m0.wu(A1 + 28)
                if C.s16(D2) <= 0:
                    continue
                m = P.Mem(ram)
                C.TRACE.clear()
                st = m.wu(A1 + 76)
                pend = m.wu(A1 + 4)
                A2 = (C.OBJ + C.sp16(m.wu(A1 + 64))) & 0xfffff
                arm = None
                m.ww(A1 + 76, 6)       # decide as a camped group: `$68fe` answers differently for a group in state 8 or $d (its own target is skipped)
                try:
                    C._decide(m, A0, A1, A2, D2, D7)
                    arm = C.TRACE[-1] if C.TRACE else '?'
                except Exception as e:  # a state the model does not cover
                    arm = 'ERR ' + type(e).__name__
                yield side, D7, st, C.s16(m.wu(A1 + 52)), C.s16(m.wu(A1 + 112)), pend, arm
        A0 += 6


if __name__ == '__main__':
    args = sys.argv[1:]
    verbose = args[:1] == ['-v']
    if verbose:
        args = args[1:]
    live, other = collections.Counter(), collections.Counter()
    for s in args:
        for side, D7, st, men, food, pend, arm in groups(s):
            decides = pend == 0 and st in (9, 6)
            (live if decides else other)[arm] += 1
            if verbose:
                print('%s side %d D7 %2d state %2d men %3d food %6d pending %d %s%s' % (
                    os.path.basename(s), side, D7, st, men, food, pend, arm, '' if decides else '  (not decided)'))
    print('decided groups (state 9 or 6, nothing pending):', dict(live))
    print('other groups (what the arm would be in decide):', dict(other))
