"""provenance proof (tools/provenance.py): every link of every slice is checked against an independent REPL run.

    python3 server/provenance_proof.py <stserver.dll> <M68000.dll> <pre_pick.snap> <powermonger.st> <outdir>

Recording A is the `goto ctl` run of `last_writer_proof.py` (2,607,722 steps from PowerMonger's `pre_pick.snap`, no
inputs, a checkpoint every 500,000). Sliced: `$53006..$53007` (the captain's lead word) at each of the 19 steps a REPL
`watch 53006 2` lists a write, and six words of the same object (`$52ff8 $52ffa $53008 $53014 $53016 $53018`) at the
end of the run, whose writers take their values from registers and memory.

Each link is scored on its own:
- a memory link (last_writer of [lo,hi] at S: step W, PC, address, value) against a REPL `watch <lo> <len>` over the
  whole run: the last watch line at or before S must have the same step, PC, address and value. A slice that stops at
  "unchanged since the base" must have no watch line at or before S;
- a register link (last_reg_change: step W, PC, previous, value) against a REPL `bp <pc> 1` from step W-2: the bp must
  hit (PC is the writer at W-1), the registers it prints must hold `previous`, and `r` after `s 1` must hold `value`.
  bp does not count an RTE back to an instruction an interrupt was taken at; for such a link the PC in bp's register
  dump stands in for the hit, and the instruction at W-2 must be that `rte`.

Controls, from recording B (the same run with two inputs at the first arrival at `$1538e`, `move.w D0,48(A3)`:
`set_reg d0` low word $1234, and `poke $53015` = $77): the slice of the word the move writes (48(A3) there) one step
later must be the move with value $1234 and stop at the set_reg (input) at its step; the slice of `$53015` at the next `sub.b D0,45(A3)` write
must reach the poke as an input stop at its step. In A, every chain from `$53006` must end at an immediate equal to
the byte written. Exit status 0 = every link and control passes.
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from stclient import StServer  # noqa: E402
from provenance import Slicer, links, show  # noqa: E402

srv, core, snap, disk, out = sys.argv[1:6]
os.makedirs(out, exist_ok=True)
N = 2_607_722
FIELDS = [0x52ff8, 0x52ffa, 0x53008, 0x53014, 0x53016, 0x53018]
REGRE = re.compile(r'D0:(\w+) D1:(\w+) D2:(\w+) D3:(\w+)\s+D4:(\w+) D5:(\w+) D6:(\w+) D7:(\w+)\s+'
                   r'A0:(\w+) A1:(\w+) A2:(\w+) A3:(\w+)\s+A4:(\w+) A5:(\w+) A6:(\w+) A7:(\w+)\s+USP:(\w+) SSP:(\w+)'
                   r'[\s\S]*?PC: (\w+)')
NAMES = [f'd{i}' for i in range(8)] + [f'a{i}' for i in range(8)] + ['usp', 'ssp', 'pc']


def repl(script, tag):
    r = subprocess.run(['dotnet', 'exec', core, 'resume', snap, 'repl'], capture_output=True, text=True,
                       env=dict(os.environ, ATARI_NOTRACE='1'), input=f'disk {disk}\n{script}q\n')
    open(f'{out}/{tag}.out', 'w').write(r.stdout)
    open(f'{out}/{tag}.err', 'w').write(r.stderr)
    return r


def watch_lines(lo, n):
    r = repl(f'watch {lo:x} {n}\ns {N}\n', f'watch_{lo:x}_{n}')
    return [(int(m[1]), int(m[2], 16), int(m[3], 16), int(m[4], 16)) for m in
            re.finditer(r'^WATCH: step=(\d+) pc=\$([0-9a-f]+) \S+ \$([0-9a-f]+) <- \$([0-9a-f]+)', r.stderr, re.M)]


def walk(n):
    yield n
    for c in n['children']:
        yield from walk(c)


# ---- recording A and its slices ---------------------------------------------------------------------------------
W53006 = watch_lines(0x53006, 2)
print(f'REPL watch 53006 2: {len(W53006)} writes')
s = StServer(os.getcwd(), dll=srv)
B = s('load', snapshot=snap, disk=disk)['step']
s('record_start', every=500_000)
s('step', n=N)
s('record_stop')
trees = []
for w in W53006:
    trees.append((f'$53006 @{w[0]}', Slicer(s, 60, 150).slice_mem(0x53006, 0x53007, w[0])))
for a in FIELDS:
    trees.append((f'${a:x} @end', Slicer(s, 60, 150).slice_mem(a, a + 1, B + N)))
with open(f'{out}/slices.txt', 'w') as f:
    for name, t in trees:
        f.write(f'== {name}\n')
        show(t, f=f)
nodes = [n for _, t in trees for n in walk(t)]
mem_links = [n for n in nodes if n['kind'] == 'mem' and 'step' in n]
reg_links = [n for n in nodes if n['kind'] == 'reg' and 'step' in n]
base_stops = [n for n in nodes if n['kind'] == 'mem' and n.get('stop', '').startswith('unchanged')]
other_stops = sorted({n['stop'] for n in nodes if 'stop' in n})
print(f'{len(trees)} slices: {len(mem_links)} memory links, {len(reg_links)} register links, '
      f'{len(base_stops)} memory stops at the base; stop reasons: {other_stops}')
bad_checks = [n for n in nodes if n.get('check') == 'MISMATCH']
print(f'value checks: {sum(n.get("check") == "ok" for n in nodes)} ok, {len(bad_checks)} mismatch, '
      f'{sum(n.get("check") == "n/a" for n in nodes)} n/a (arithmetic: no prediction)')

# ---- memory links against REPL watches --------------------------------------------------------------------------
watches = {}
for n in mem_links + base_stops:
    watches.setdefault((n['lo'], n['hi']), None)
for (lo, hi) in watches:
    watches[(lo, hi)] = watch_lines(lo, hi - lo + 1)
mem_ok = 0
for n in mem_links:
    want = next((w for w in reversed(watches[(n['lo'], n['hi'])]) if w[0] <= n['at']), None)
    have = (n['step'], n['pc'], n['write'][0], n['write'][2])
    ok = have == want
    mem_ok += ok
    if not ok:
        print(f"DIFF memory ${n['lo']:x}..${n['hi']:x} @{n['at']}: slice {have}, watch {want}")
base_ok = 0
for n in base_stops:
    want = next((w for w in reversed(watches[(n['lo'], n['hi'])]) if w[0] <= n['at']), None)
    base_ok += want is None
    if want is not None:
        print(f"DIFF base stop ${n['lo']:x}..${n['hi']:x} @{n['at']}: watch has {want}")
print(f'memory links {mem_ok}/{len(mem_links)} against {len(watches)} REPL watches; base stops {base_ok}/{len(base_stops)}')

# ---- register links against REPL bp -----------------------------------------------------------------------------
checks = {}
for n in reg_links:
    checks.setdefault((n['step'], n['pc']), []).append(n)
pending = sorted(checks)
sessions = []
while pending:
    cur, rest, last = [], [], None
    for k in pending:
        (cur if last is None or k[0] >= last + 2 else rest).append(k)
        if cur and cur[-1] is k:
            last = k[0]
    sessions.append(cur)
    pending = rest
reg_ok = rte_ok = 0
for si, sess in enumerate(sessions):
    script, at = '', B
    for (W, pc) in sess:
        if W - 2 < at:
            sys.exit(f'link at {W} is too close to the base for a bp check')
        if W - 2 > at:
            script += f's {W - 2 - at}\n'
        script += f'bp {pc:x} 1\ns 1\nr\n'
        at = W
    r = repl(script, f'bp_{si}')
    text = r.stdout + r.stderr
    hits = re.findall(r'--- (breakpoint \$\w+ hit|gave up)', text)
    blocks = [dict(zip(NAMES, (int(x, 16) for x in m.groups()))) for m in REGRE.finditer(text)]
    if len(hits) != len(sess) or len(blocks) != 2 * len(sess):
        sys.exit(f'bp session {si}: {len(hits)} bp results and {len(blocks)} register blocks for {len(sess)} links')
    for j, (W, pc) in enumerate(sess):
        pre, post = blocks[2 * j], blocks[2 * j + 1]
        # bp does not count an RTE back to an instruction an interrupt was taken at (CLAUDE.md, `hits`/`bp` count
        # instruction starts): then the REPL's register dump at W-1 is the PC evidence, and the step into W-1 must
        # be that RTE (read from the recording: the opcode at the PC of W-2).
        rte = False
        if not hits[j].startswith('breakpoint'):
            s('replay_to', step=W - 2)
            rte = s('read', addr=int(s('regs')['pc'][1:], 16) & 0xffffff, len=2) == '4e73'
        for n in checks[(W, pc)]:
            ok = ((hits[j].startswith('breakpoint') or rte) and (pre['pc'] & 0xffffff) == (pc & 0xffffff)
                  and pre[n['reg']] == n['previous'] and post[n['reg']] == n['value'])
            reg_ok += ok
            rte_ok += ok and rte
            if not ok:
                print(f"DIFF register {n['reg']} step {W} pc ${pc:x}: bp {hits[j]}, pc ${pre['pc']:x}, "
                      f"{n['reg']} ${pre[n['reg']]:x} -> ${post[n['reg']]:x}, slice ${n['previous']:x} -> ${n['value']:x}")
print(f'register links {reg_ok}/{len(reg_links)} against REPL bp ({len(checks)} distinct writer steps, {len(sessions)} '
      f'sessions; {rte_ok} of them reached by an RTE, which bp does not count, so checked on the register dump)')

# ---- immediates at the end of the $53006 chains ---------------------------------------------------------------
imm_ok = imm_n = 0
for name, t in trees[:len(W53006)]:
    for n in walk(t):
        for c in n['children']:
            if c['kind'] == 'imm':
                imm_n += 1
                imm_ok += n.get('check') == 'ok' and c['value'] is not None and \
                    c['value'] & 0xff == n['value'] & 0xff and '#$' in n.get('insn', '')
terminals = [n for name, t in trees[:len(W53006)] for n in walk(t) if not n['children']]
print(f'$53006 chains: {imm_ok}/{imm_n} immediate stops equal the byte written; terminals: '
      f'{sorted({(n["kind"], n.get("stop", "")) for n in terminals})}')
s.close()

# ---- controls: recording B with two inputs ----------------------------------------------------------------------
s = StServer(os.getcwd(), dll=srv)
s('load', snapshot=snap, disk=disk)
s('record_start', every=500_000)
r = s('run', max_steps=N, until_pc=0x1538e)
T = r['step']
d0 = int(s('regs')['d0'][1:], 16)
DST = (int(s('regs')['a3'][1:], 16) + 48) & 0xffffff  # 48(A3): the word the move writes one step later
s('set_reg', name='d0', value=(d0 & 0xffff0000) | 0x1234)
s('poke', addr=0x53015, width=1, value=0x77)
s('step', n=B + N - T)
s('record_stop')
c1 = Slicer(s, 60, 150).slice_mem(DST, DST + 1, T + 1)
nxt = s('last_writer', lo=0x53015, hi=0x53015, step=B + N)['event']
c2 = Slicer(s, 60, 150).slice_mem(0x53015, 0x53015, nxt['step'])
with open(f'{out}/controls.txt', 'w') as f:
    show(c1, f=f)
    show(c2, f=f)
show(c1)
show(c2)
k1 = c1.get('step') == T + 1 and c1.get('value') == 0x1234 and any(
    n.get('stop') == 'input (journalled set_reg)' and n.get('step') == T for n in walk(c1))
k2 = nxt['step'] > T and any(n.get('stop') == 'input (journalled host write)' and n.get('step') == T for n in walk(c2))
print(f'control set_reg at {T}: {"pass" if k1 else "FAIL"}; control poke at {T} (next write {nxt["step"]}): {"pass" if k2 else "FAIL"}')
s.close()
total = len(mem_links) + len(reg_links)
print(f'links {mem_ok + reg_ok}/{total}')
ok = (mem_ok == len(mem_links) and reg_ok == len(reg_links) and base_ok == len(base_stops) and not bad_checks
      and imm_ok == imm_n > 0 and k1 and k2)
sys.exit(0 if ok else 1)
