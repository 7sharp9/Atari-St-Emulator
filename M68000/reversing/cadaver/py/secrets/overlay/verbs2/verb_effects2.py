"""verb_effects2.py [section ...]: live measurements of the object-script verbs that secrets.md lists as read, not run (Cadaver 80th pass, agent B).

Every check is a line `<label> ok|BAD`.  Two kinds of evidence:
  * callcap: the verb handler from the table $00ffba is called on a scratch script (A1 -> scratch, A4 = a valid RAM address) and the
    memory delta / register delta read back (the handler runs alone, interrupts masked, the state is restored afterwards);
  * natural / real: the verb runs inside the live game.  `natural` = an event injected into the ring queue for an object that carries the
    verb in its own level script; `real` = the body of object 2's (level 1: #27's) event-5 block is overwritten with a scratch script and
    event 5 is injected, so the real consumer $00fdbc runs it with interrupts on.  Injection appends at the write pointer 304(A5), pointer += 8,
    count 1154(A5) += 1 (writing at 152(A5) without advancing 304(A5), as treasury_gate_live.py does, is overwritten by the game's own pushes
    in level 1).  Noise from the running game is removed with a control run (noise_for).
Sections (files in this directory):  1 delete  2 showhide  3 anim  4 create  5 flags_ruck  6 misc  7 buy  8 extra
Run from anywhere:  uv run python verb_effects2.py   (needs the existing bin/Debug/net8.0/M68000.dll; sets ATARI_NOTRACE via Repl)."""
import sys, importlib, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib2

SECTIONS = {'1': 'sec1_delete', '2': 'sec2_showhide', '3': 'sec3_anim', '4': 'sec4_create', '5': 'sec5_flags_ruck', '6': 'sec6_misc', '7': 'sec7_buy', '8': 'sec8_extra'}
want = sys.argv[1:] or sorted(SECTIONS)
for k in want:
    print('=== section %s (%s)' % (k, SECTIONS[k]))
    importlib.import_module(SECTIONS[k]).run()
print()
print('per-verb evidence (ok/bad):', ', '.join('%d: %d/%d' % (v, c[0], c[1]) for v, c in sorted(lib2.TALLY.items())))
print('ok %d  bad %d' % (lib2.OK, lib2.BAD))
