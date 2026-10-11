"""Generate group_soa.svg: the $51538 side record as structure-of-arrays.
Every row's offset, group-frame offset and meaning is taken from strategy.md
"$51538 group-order table" and "Data structures (C)"; see group_soa.facts.md."""
import os, html
here = os.path.dirname(os.path.abspath(__file__))
# (n, label, meaning, evidence)  evidence: pv lv cr na
ROWS = [
 (4,   "pending / link", "4(A1) := D7 by $6822; cleared by $4220 (pigeon landing), $6b20", "pv"),
 (16,  "",               "not named in strategy.md", "na"),
 (28,  "owner side",     "<= 0: no group, the AI skips it (not the men)", "pv"),
 (40,  "first man",      "roster head, next man via 26(man)", "cr"),
 (52,  "men",            "captain panel \"Troops\"; arm 1 tests < 22", "pv"),
 (64,  "lead",           "lead man's object offset (from $51b66)", "pv"),
 (76,  "state",          "$6 camp, $9 invent, $d fighting, ...", "pv"),
 (88,  "eat timer",      "$3e06 counts it to the side's eat period", "cr"),
 (100, "target",         "target link: a lord, settlement or object", "pv"),
 (112, "food",           "captain panel \"Food\"; AI groups seeded $5fff", "pv"),
 (124, "sender",         "lead of the side's first group; 0 for it ($6ac6)", "pv"),
 (136, "posture",        "2 Aggressive, 3 Neutral, 4 Passive; set per AI decision", "pv"),
 (148, "aggression",     "0 PowerMonger .. 7 Wimp; display only ($90de)", "pv"),
 (160, "goods x 8",      "8 arrays, item i at +160 + 12i (pike .. cannon)", "cr"),
 (256, "camp stamp",     "clock word at camp ($3720); waits $14 ticks", "pv"),
 (268, "prev state",     "state before camp ($3728); $6762 key", "pv"),
 (280, "opponent class", "opponent or target: 2 lord, 4 group, 6 man, 8/$a animal, $c", "pv"),
 (292, "opponent",       "opponent's record at the last $4bc8 ($4d6c); escort target", "pv"),
 (304, "",               "+304..+315 not named in strategy.md", "na"),
]
W, ROWH = 900, 25
top = 250
H = top + ROWH * (len(ROWS) + 1) + 108
cx0, cw = 222, 50          # six word cells
o = []
a = o.append
a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t4 d4" xml:space="preserve">')
a('<title id="t4">Group record: six-word arrays in the $51538 side record</title>')
a('<desc id="d4">The side record $51538 + side*$13c holds a 4-byte queued-order header and then parallel arrays of six words, one word per group k = 0..5: group k\'s word n is at base + n + 2k. '
  'Two frames address it: the AI loop uses A1 = base + 2k (offset n), the executor and entity modes use the group offset D2 = side*$13c + $4c + 2k (offset n - 76). '
  'Sources: reversing/powermonger/strategy.md "`$51538` group-order table" (the n(A1) table), "Data structures (C)" (pm_side_groups), "The commander AI `$6522`" (pending word), '
  '"The game\'s own text: names for the fields" (aggression display only); ai.md "`$4562` how an order reaches a subordinate captain" (word 48 the sender; $6ac6 reads 48(A1) with A1 = $51538 + D2, checked by disassembly). Full list: group_soa.facts.md.</desc>')
a('''<style>
text{font-family:Helvetica, Arial, sans-serif;fill:#1f2328;font-size:12px}
.t{font-size:16px;font-weight:bold}
.c{font-size:11.5px;fill:#424a53}
.m{font-family:Menlo, Consolas, "DejaVu Sans Mono", monospace;font-size:11.5px}
.mm{font-family:Menlo, Consolas, "DejaVu Sans Mono", monospace;font-size:10px;fill:#424a53}
.s{font-size:11px;fill:#424a53}
.h{font-size:12px;font-weight:bold}
.pv{fill:#dafbe1;stroke:#1a7f37;stroke-width:1.5}
.lv{fill:#ddf4ff;stroke:#0969da;stroke-width:1.5}
.cr{fill:#f6f8fa;stroke:#57606a;stroke-width:1.3;stroke-dasharray:6 3}
.in{fill:#fff1e5;stroke:#bc4c00;stroke-width:1.3;stroke-dasharray:2 3}
.na{fill:#ffffff;stroke:#afb8c1;stroke-width:1}
.cell{fill:#ffffff;stroke:#8c959f;stroke-width:0.8}
.k2{fill:#fff8c5;stroke:#9a6700;stroke-width:1.4}
</style>''')
a(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>')
a('<text x="20" y="26" class="t">Group fields are six-word arrays: group k\'s word n is at side base + n + 2k</text>')
a('<text x="20" y="45" class="c">Meaning-cell border = evidence for the field\'s role. Yellow column: group 2, the worked example below.</text>')
for x, cls, lab in ((20,"pv","proven (gated routine or whole-image scan)"),(300,"cr","code read"),(395,"na","not named")):
    a(f'<rect x="{x}" y="54" width="22" height="12" class="{cls}"/><text x="{x+27}" y="64" class="s">{lab}</text>')
# frames box
a('<rect x="20" y="80" width="420" height="152" rx="4" fill="#f6f8fa" stroke="#57606a" stroke-width="1"/>')
lines = [
 ('h','Two frames for the same word'),
 ('', 'side base = <tspan class="m">$51538 + side * $13c</tspan> (316 bytes, 5 sides)'),
 ('', 'AI loop <tspan class="m">$6564</tspan>: <tspan class="m">A1 = base + D7</tspan>, <tspan class="m">D7 = 2k</tspan>'),
 ('', '   field at <tspan class="m">n(A1)</tspan>, e.g. men <tspan class="m">52(A1)</tspan>'),
 ('', 'executor, entity modes: group offset'),
 ('', '   <tspan class="m">D2 = side * $13c + $4c + 2k</tspan>, field at <tspan class="m">(n - 76)</tspan>'),
 ('', '   e.g. men <tspan class="m">-24(A3)</tspan>, pending <tspan class="m">-72(A0)</tspan> at <tspan class="m">$4220</tspan>'),
 ('s','Header: long +0 queued flag, byte +1 type, word +2 parameter.'),
]
y = 100
for cls, t in lines:
    a(f'<text x="30" y="{y}"{" class=%s" % chr(34)+cls+chr(34) if cls else ""}>{t}</text>'); y += 18
# worked example
a('<rect x="460" y="80" width="420" height="152" rx="4" class="k2"/>')
ex = [
 ('h','Worked example: side 1, group 2 (k = 2, D7 = 4)'),
 ('', 'base = <tspan class="m">$51538 + $13c = $51674</tspan>'),
 ('', 'men: <tspan class="m">$51674 + 52 + 4 = $516ac</tspan>'),
 ('', 'group offset <tspan class="m">D2 = $13c + $4c + 4 = $18c</tspan>'),
 ('', 'men again: <tspan class="m">$51538 + $18c - 24 = $516ac</tspan>'),
 ('', 'owner: <tspan class="m">$51674 + 28 + 4 = $51694</tspan>'),
 ('s','Trap: 30(A1) is group k+1\'s owner, not a field of group k;'),
 ('s','a REPL "w" writes a longword, covering two groups\' words.'),
]
y = 100
for cls, t in ex:
    a(f'<text x="470" y="{y}"{" class=%s" % chr(34)+cls+chr(34) if cls else ""}>{t}</text>'); y += 18
# table header
hy = top
a(f'<text x="20" y="{hy}" class="h">n(A1)</text><text x="70" y="{hy}" class="h">group</text><text x="120" y="{hy}" class="h">field</text>')
for k in range(6):
    a(f'<text x="{cx0 + k*cw + 25}" y="{hy}" class="h" text-anchor="middle">k={k}</text>')
a(f'<text x="{cx0 + 6*cw + 12}" y="{hy}" class="h">meaning</text>')
y0 = hy + 8
for i, (n, lab, mean, ev) in enumerate(ROWS):
    y = y0 + i * ROWH
    ty = y + 16
    a(f'<text x="20" y="{ty}" class="m">+{n}</text>')
    if ev != "na":
        a(f'<text x="70" y="{ty}" class="m">{n-76}</text>')
    a(f'<text x="120" y="{ty}">{html.escape(lab)}</text>')
    for k in range(6):
        x = cx0 + k*cw
        cls = "k2" if k == 2 else ("cell" if ev != "na" else "na")
        a(f'<rect x="{x}" y="{y+2}" width="{cw}" height="{ROWH-4}" class="{cls}"/>')
        a(f'<text x="{x+cw/2}" y="{ty}" class="mm" text-anchor="middle">+{n+2*k}</text>')
    mx = cx0 + 6*cw + 8
    a(f'<rect x="{mx}" y="{y+2}" width="{W-20-mx}" height="{ROWH-4}" rx="3" class="{ev}"/>')
    a(f'<text x="{mx+6}" y="{ty}" class="s">{html.escape(mean)}</text>')
fy = y0 + len(ROWS) * ROWH + 22
foot = [
 'Cell numbers are byte offsets from the side base. +160 shows only item 0 (pike); item i\'s six words are at +160 + 12i .. +170 + 12i, up to +255.',
 'Proven: the field is an input or output of $6522 (gate_cmdai.py 323/323 natural), $6ac6 (exec_census.py 44/44), $3e06 or the order senders (gate_orders.py);',
 'aggression "display only" is a whole-image scan (py/aggr/scan_group_field.py, text segment to $1c488). Offsets are from the code, strategy.md "$51538".',
 '+280: $c a category-4 record, 0 unset; written by $4a7a and $4bc8 (classifier $4de2); $5778 overwrites it with the attacker\'s offset (bug, live 1/1).',
 'The captain panel $9090 recovers side and 2k from A3 - $51538 divided by $13c; it prints Food, Troops and the aggression line from these arrays.',
]
for j, t in enumerate(foot):
    a(f'<text x="20" y="{fy + j*16}" class="s">{html.escape(t)}</text>')
a('</svg>')
out = os.path.join(os.environ.get("PM_WORK", here), "group_soa.svg")
open(out, "w").write("\n".join(o) + "\n")
print(out, H)
