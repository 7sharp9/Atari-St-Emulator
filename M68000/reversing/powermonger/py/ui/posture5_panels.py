"""The two panel readers of the posture at posture 5 (strategy.md "Posture 5 forced into the trade"), by callcap against a
posture-3 control from the same snapshot: the captain panel $9036 (its "Aggression" line, `$90fe`) and the alliance offer
$c706 (its verb, `$c77e`). Both look up `table + 3 + byte[table + posture - 2]` in 3-entry tables, so posture 5 reads the
first character of the table's text as an offset.
    cd M68000 && uv run python reversing/powermonger/py/ui/posture5_panels.py [snap]   (default scratchpad/pm123/win/m1_ready.snap)
Pokes, per arm: the group's posture word (group A3 + 60 for $c706, side record + 136 for $9036) := 5 or 3, longword
writes keeping the following word. Exit 1 unless all four callcaps return."""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from uilib import ROOT, ram_of, repl, parse_callcaps, panel_text  # noqa: E402

snap = ROOT / (sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/pm123/win/m1_ready.snap')
R = ram_of(snap)
w = lambda x: (R[x] << 8) | R[x + 1]
side = w(0x57ffe)
a = 0x51538 + side * 0x13c                                # the local side's group 0 in the side-record frame ($9036's A3)
g0 = a + 0x4c                                             # the same group in $33b0's group-offset frame ($c706's A3)
bad = 0
for post in (3, 5):
    for tag, addr, cmd in (('captain panel $9036', a + 136, f'callcap 9036 20000 A3={a:x}'),
                           ('alliance offer $c706', g0 + 60, f'callcap c706 20000 A3={g0:x}')):
        cmds = ['disk scratchpad/powermonger.st', f'w {addr:x} {post:04x}{w(addr + 2):04x}']
        if 'c706' in cmd:
            cmds.append(f'w {g0 + 84:x} 00020000')       # 2 of goods 0, as req_panels.py
        cc = parse_callcaps(repl(snap, cmds + [cmd]))
        ok = bool(cc) and cc[-1]['returned']; bad += not ok
        print(f'== posture {post}, {tag} (poke {addr:x}): returned={ok}')
        for row in (panel_text(R, cc[-1]) or []) if cc else []:
            print('   |' + row + '|')
sys.exit(1 if bad else 0)
