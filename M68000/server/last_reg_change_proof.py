"""last_reg_change proof (DEVELOPING.md, "Record and replay"): the recording's answer equals a brute-force per-step scan.

    python3 server/last_reg_change_proof.py <stserver.dll> <pre_pick.snap> <powermonger.st> <outdir>

From PowerMonger's `pre_pick.snap` (as `last_writer_proof.py`), one `stserver` records 1,200,000 steps with a
checkpoint every 250,000 and one input: `set_reg d7` (d7 xor $10000) at base + 700,000. A second, independent
`stserver` loads the same snapshot and steps the same run one instruction at a time, reading every register after each
step (and after the same `set_reg`, applied at the same step), and lists every change of every register: (step, PC of
the instruction, previous, value, host or not). Then `last_reg_change reg S [mask]` for all 19 registers at the base,
at and one after each checkpoint, at and after the input, at the end and at 5 spread steps, plus d0 under masks $ff and
$ffff0000 and sr under mask $ff00. Each must equal the brute force's last change at or before S in the masked bits
(null if none since the base), source included: the brute force calls a step an interrupt entry when it lands on a
handler named by the base's autovectors or MFP vectors. Eight more a7 and sr cases sit at the first eight a7 changes the
brute force calls interrupt entries. Falsifier: any case differs. Also printed: how many answers lie in an interval
before S's own, the cases a search confined to S's interval would get wrong.
Exit status 0 = all pass.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from stclient import StServer  # noqa: E402

srv, snap, disk, out = sys.argv[1:5]
os.makedirs(out, exist_ok=True)
N, EVERY, IN_AT = 1_200_000, 250_000, 700_000
REGS = ['d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7', 'a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7', 'usp', 'ssp', 'sr']


def regs(s):
    r = s('regs')
    return {k: int(r[k].lstrip('$'), 16) for k in REGS + ['pc']}


# Recording.
rec = StServer(os.getcwd(), dll=srv)
B = rec('load', snapshot=snap, disk=disk)['step']
rec('record_start', every=EVERY)
rec('step', n=IN_AT)
d7 = regs(rec)['d7']
rec('set_reg', name='d7', value=d7 ^ 0x10000)
rec('step', n=N - IN_AT)
r = rec('record_stop')
print(f"recorded {r['base']}..{r['end']}: {r['checkpoints']} checkpoints, {r['inputs']} input(s)")
cks = [B + k * EVERY for k in range(r['checkpoints'])]

# Brute force: an independent process, one step per call.
bf = StServer(os.getcwd(), dll=srv)
bf('load', snapshot=snap, disk=disk)
changes = {k: [] for k in REGS}  # reg -> [(step, pc, prev, value, host)]
# An interrupt entry, told apart independently: the step lands on a handler named by an autovector ($64-$7c) or an
# MFP vector ($100-$13c) as they stand at the base.
HANDLERS = {int(bf('peek', addr=a, width=4)[0][1:], 16) & 0xffffff for a in list(range(0x64, 0x80, 4)) + list(range(0x100, 0x140, 4))}
cur = regs(bf)
for i in range(1, N + 1):
    bf('step', n=1)
    new = regs(bf)
    t = B + i
    kind = 'exception' if (new['pc'] & 0xffffff) in HANDLERS else 'cpu'
    for k in REGS:
        if new[k] != cur[k]:
            changes[k].append((t, cur['pc'], cur[k], new[k], kind))
    if i == IN_AT:
        bf('set_reg', name='d7', value=d7 ^ 0x10000)
        after = regs(bf)
        for k in REGS:
            if after[k] != new[k]:
                changes[k].append((t, after['pc'], new[k], after[k], 'host'))
        new = after
    cur = new
bf.close()
with open(f'{out}/changes.txt', 'w') as f:
    for k in REGS:
        f.write(f'{k} {len(changes[k])}\n')
print('brute force changes per register:', {k: len(v) for k, v in changes.items()})


def want(reg, S, mask):
    for (t, pc, prev, val, host) in reversed(changes[reg]):
        if t <= S and (prev ^ val) & mask:
            return (t, pc, prev, val, host)
    return None


S_pts = sorted(set([B, B + IN_AT, B + IN_AT + 1, B + N] + [c for c in cks] + [c + 1 for c in cks]
                   + [B + (N * k) // 6 + 17 for k in range(1, 6)]))
M32 = 0xffffffff
cases = [(reg, S, M32) for reg in REGS for S in S_pts]
ex = [c[0] for c in changes['a7'] if c[4] == 'exception'][:8]
cases += [(reg, S, M32) for S in ex for reg in ('a7', 'sr')]
cases += [(reg, S, m) for (reg, m) in [('d0', 0xff), ('d0', 0xffff0000), ('sr', 0xff00)] for S in S_pts]
match = earlier = nulls = host = exc = bex = 0
for reg, S, mask in cases:
    w = want(reg, S, mask)
    g = rec('last_reg_change', reg=reg, step=S, mask=mask)
    e = g['event']
    have = None
    if e:
        have = (e['step'], int(e['pc'][1:], 16), int(e['previous'][1:], 16), int(e['value'][1:], 16), e['source'])
        exc += e['source'] == 'exception'
    ok = have == w
    match += ok
    nulls += w is None
    host += bool(w and w[4] == 'host')
    bex += bool(w and w[4] == 'exception')
    own_ck = max(c for c in cks if c <= S)
    if w and w[0] <= own_ck:
        earlier += 1
    if not ok:
        print(f'DIFF {reg} S={S} mask=${mask:x}: last_reg_change {have} ({g["intervals"]} interval(s)), brute force {w}')
rec.close()
print(f'{len(cases)} cases: {nulls} null (no change since the base), {host} host (the set_reg), '
      f'{earlier} answered from an interval before S\'s own, {exc} reported as exception entries ({bex} by the brute force)')
print(f'last_reg_change {match}/{len(cases)}')
sys.exit(0 if match == len(cases) else 1)
