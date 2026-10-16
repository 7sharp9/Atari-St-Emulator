"""The dialog-button dispatch of $7658 (README "Dialog buttons by id"), one callcap per (id, button).

    cd M68000 && uv run python reversing/powermonger/py/ui/dlg_ids.py [snap]

Each case enters at $76f0 (after the click sound) with the dialog id in $7a3c (the word after it kept) and the button's
grid offset in D3, through a stub poked over the stripped debug stubs at $1ba62 (`movem.l D1-A6,-(A7)` / `jmp $76f0`; no
absolute reference to $1ba60..$1ba6e in the text segment), because every handler leaves through $7a22, which pops the
14 registers $7658's caller pushed. It prints whether the call returned and every changed byte outside the stack page, grouped into runs.
The expected effects (EXPECT) are the README table's; a case passes when every expected (address, value) is written.
Log in $PM_WORK (default scratchpad/pm160/dlg) as dlg_ids.out. Exit 1 on any failure.
"""
import os
import sys
from pathlib import Path


def find_root():
    p = Path(os.environ.get('M68000_ROOT') or Path(__file__).resolve())
    for q in [p, *p.parents]:
        if (q / 'tools/rdis.py').exists():
            return q
    sys.exit('repo root (the directory holding tools/rdis.py) not found')


ROOT = find_root()
os.environ.setdefault('M68000_ROOT', str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from uilib import ram_of, repl, parse_callcaps  # noqa: E402

WORK = ROOT / os.environ.get('PM_WORK', 'scratchpad/pm160/dlg')
snap = ROOT / (sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/pm142/rand1.snap')
R = ram_of(snap)
slot = int.from_bytes(R[0x58034:0x58038], 'big')          # the local side's command slot
keep = R[0x7a3e:0x7a40].hex()
slot0 = R[0x7a38:0x7a3a].hex()
CLOSE = {0x7a37: 0}                                        # clr.w $7a36: the dialog's slot freed
# (id, D3, label, expected {addr: value})
CASES = [
    (0x08, 0x11, 'GAME RETIRE', {slot + 1: 0x2e, **CLOSE}),
    (0x08, 0x41, 'GAME REPLAY MAP', {slot + 1: 0x28}),
    (0x08, 0xa1, 'GAME MULTI PLAY', {slot + 1: 0x2c}),
    (0x08, 0xd1, 'GAME RANDOM MAP', {slot + 1: 0x30}),
    (0x08, 0x101, 'GAME PAUSE', {slot + 1: 0x24}),
    (0x0c, 0x1ba, 'login CONNECT', {0x2df6d: 1, **CLOSE}),
    (0x0c, 0x1d6, 'login CANCEL', CLOSE),
    (0x0e, 0x92, 'menu Start New', {0x2df6f: 2, **CLOSE}),
    (0x0e, 0xda, 'menu Continue', {0x2df6f: 4, **CLOSE}),
    (0x0e, 0x122, 'menu Random Land', {0x2df6f: 6, **CLOSE}),
    (0x0e, 0x16a, 'menu Load Data Disk', {0x2df6f: 8, **CLOSE}),
    (0x10, 0xe2, 'disk OK', {0x2df6d: 0, **CLOSE}),
    (0x10, 0xf6, 'disk CANCEL', {0x2df6d: 1, **CLOSE}),
    (0x12, 0x68, 'connect CANCEL', CLOSE),
    (0x18, 0x8a, 'new conquest NO', {0x2df6d: 0, **CLOSE}),
    (0x1a, 0x146, 'alliance YES', {}),
    (0x1a, 0x162, 'alliance NO', {slot + 1: 0x32}),
]
bad = 0
log = []
for did, d3, label, exp in CASES:
    # baselines no case writes, so every expected write shows: $2df6c and $2df6e := $55, slot 0's word 0 := 1 (a panel open)
    pre = ['disk scratchpad/powermonger.st', f'w 7a3c {did:04x}{keep}', 'w 2df6c 00550055', f'w 7a36 0001{slot0}']
    stub = ['w 1ba62 48e77ffe', 'w 1ba66 4ef90000', 'w 1ba6a 76f00000']      # $1ba6c's word is 0000 in the image
    out = repl(snap, pre + stub + [f'callcap 1ba62 200000 D3={d3:x}'])
    log.append(f'### {did:#x} {d3:#x} {label}\n{out}')
    cc = parse_callcaps(out)
    if not cc:
        print(f'{did:#04x} {d3:#05x} {label}: no callcap output'); bad += 1; continue
    c = cc[-1]
    mem = {a: v for a, v in c['mem'].items() if not 0x2c000 <= a < 0x2d000}
    runs, cur = [], None
    for a in sorted(mem):
        if cur and a == cur[0] + len(cur[1]):
            cur[1].append(mem[a][1])
        else:
            cur = [a, [mem[a][1]]]; runs.append(cur)
    hit = all(a in mem and mem[a][1] == v for a, v in exp.items())
    ok = c['returned'] and hit
    bad += not ok
    shown = ' '.join(f'${a:x}:' + ''.join(f'{b:02x}' for b in bs) for a, bs in runs[:8])
    print(f'{did:#04x} {d3:#05x} {label:22s} returned={c["returned"]} expected={hit} | {len(mem)} bytes: {shown}')
WORK.mkdir(parents=True, exist_ok=True)
(WORK / 'dlg_ids.out').write_text('\n'.join(log))
print(f'{len(CASES) - bad}/{len(CASES)} pass')
sys.exit(1 if bad else 0)
