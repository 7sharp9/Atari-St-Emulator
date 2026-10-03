"""run_all.py: every verb proof of agent A2 (91st pass) in one process: verbs 56, 90, 41 (+ the search $008e38), 44, 84, 91, 7, 8 and the out-of-range verb byte.
Prints each `<label> ok|BAD` line and the per-verb tally.  Run (OUTDIR env = scratch dir, default scratchpad/cadaver/s91_verbs): cd M68000 && .venv/bin/python reversing/cadaver/py/secrets/overlay/verbs3/run_all.py   (about 1.5 minutes; needs bin/Debug/net8.0/M68000.dll, ATARI_NOTRACE is set by Repl)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib2
import m56, m90, m41, m44, m_misc, m_badverb
for name, mod in (('verb 56', m56), ('verb 90', m90), ('verb 41 and the search', m41), ('verb 44', m44), ('verbs 84, 91, 7, 8', m_misc), ('verb byte >= 94', m_badverb)):
    print('=== ' + name)
    mod.run()
print()
print('per-verb evidence (ok/bad):', ', '.join('%d: %d/%d' % (v, c[0], c[1]) for v, c in sorted(lib2.TALLY.items())))
print('ok %d  bad %d' % (lib2.OK, lib2.BAD))
