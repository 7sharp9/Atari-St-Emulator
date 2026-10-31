"""Gate for recruitment (ai.md section 8): the presence list `$12f2`, the non-member filter `$4ade`, the Decisions
offer test `$1142` (k=6, the recruit icon `$489c`), the answer `$496c`, and Kristiansen's radio: its offer test
`$1102` (k=23), the non-member list `$fab4` and the random pick `$fa78`, run by the game in `stserver` on poked
states of d_decisions.snap and checked against recruit_model.py call by call.

usage: gate_recruit.py [states] [control]
Needs $MIDWINTER_WORK (default <root>/scratchpad/midwinter) holding d_decisions.snap and zuul067.st. Every state is a
labelled poke: the asker, the team list, positions near the asker, buildings, the flags word, the asked character's
Morale and name format, the team score and the asker's Optimism, and in some states random answer bytes and a random Morale
table. A control runs a broken model, which must fail: signed (the Morale change signed and indexed by the reply),
nocap (no Optimism cap on the team score), transpose (the answer read as [asker][candidate]), radius9
(presence within 9), anybuilding (the offer without the same-building test), radioany (the radio offered in any
building), pickfull (the radio's pick from the whole random word, not its low 5 bits).
"""
import os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
root = os.environ.get('M68000_ROOT') or HERE
while not os.path.exists(os.path.join(root, 'tools', 'rdis.py')):
    root = os.path.dirname(root)
WORK = os.environ.get('MIDWINTER_WORK') or os.path.join(root, 'scratchpad', 'midwinter')
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'army'))
sys.path.insert(0, os.path.join(root, 'tools'))
import recruit_model as rm  # noqa: E402
from army_model import Mem  # noqa: E402
from stclient import StServer  # noqa: E402

OUT = [(rm.RADIO_LIST, 33), (rm.TEAM, 40), (rm.RECS, 32 * 0x4a), (rm.PRESENT, 34), (rm.OTHERS, 34), (rm.CAND, 8), (rm.BUSY, 2),
       (rm.TEAM_SCORE, 2), (rm.TEXT, 256)]
SLOT_ICONS, SLOT_ACTIONS = 0x71000, 0x71100   # scratch tables for $de2's appends under $1142


class Score:
    def __init__(self, s):
        self.s, self.n, self.ok, self.shown = s, {}, {}, 0

    def check(self, m, label, extra=True):
        diffs = []
        for a, ln in OUT:
            got, exp = self.s.read(a, ln), bytes(m.b[a:a + ln])
            diffs += [(hex(a + j), exp[j], got[j]) for j in range(ln) if exp[j] != got[j]]
        ok = not diffs and extra
        self.n[label] = self.n.get(label, 0) + 1
        self.ok[label] = self.ok.get(label, 0) + ok
        if not ok and self.shown < 8:
            self.shown += 1
            print(f'  {label} differs: {diffs[:6]} extra={extra}')


def main():
    states = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    control = sys.argv[2] if len(sys.argv) > 2 else None
    kw = {'signed': {'signed_delta': True}, 'nocap': {'no_cap': True}, 'transpose': {'transpose': True}, 'radius9': {}, 'anybuilding': {}, 'radioany': {}, 'pickfull': {},
          None: {}}
    if control not in kw:
        sys.exit(f'unknown control {control}')
    s = StServer(root)
    s('load', snapshot=os.path.join(WORK, 'd_decisions.snap'), disk=os.path.join(WORK, 'zuul067.st'))
    base = s.read(0, 0x70100)
    fork = s('fork')['id']
    sc = Score(s)
    rng = random.Random(1989)
    offered = roffered = 0
    for state in range(states):
        s('restore', id=fork)
        m = Mem(base)

        def poke(a, width, v):
            v &= (1 << 8 * width) - 1
            s('poke', addr=a, width=width, value=v)
            m.b[a:a + width] = v.to_bytes(width, 'big')
        cur = 12 if rng.random() < 0.3 else rng.randrange(32)
        poke(rm.CUR, 2, cur)
        n = rng.choice([0, 1, 2, 5, 10, 20, 31, 32])
        members = rng.sample(range(32), n)
        if rng.random() < 0.7 and cur not in members:
            members[:1] = [cur]
        for j in range(39):
            poke(rm.TEAM + j, 1, members[j] if j < len(members) else 0xff)
        r0 = rm.rec(cur)
        x0, y0 = rm.coord(m, r0 + 34), rm.coord(m, r0 + 38)
        for c in rng.sample(range(32), rng.randrange(0, 12)):
            r = rm.rec(c)
            poke(r + 34, 4, ((x0 + rng.randrange(-10, 11)) & 0xffff) << 8 | rng.randrange(256))
            poke(r + 38, 4, ((y0 + rng.randrange(-10, 11)) & 0xffff) << 8 | rng.randrange(256))
        for c in range(32):
            if rng.random() < 0.5:
                poke(rm.rec(c) + 64, 1, rng.randrange(4))
        poke(r0 + 63, 1, rng.choice([0xff, 0x80, 0, 3, 5, 8, 14, 14]))
        poke(rm.RADIO_USES, 2, rng.choice([0, 1, 3, 0xffff]))
        poke(rm.FLAGS, 2, rng.choice([0, 2, 0x3f, 0x3d, 0xffff]))
        if rng.random() < 0.4:
            for _ in range(64):
                poke(rm.ANSWER + rng.randrange(1024), 1, rng.randrange(256))
        if rng.random() < 0.3:
            for j in range(128):
                poke(rm.DELTA + j, 1, rng.randrange(256))
        poke(rm.TEAM_SCORE, 2, rng.choice([0, 100, 200, 209, 210, 249, rng.randrange(400)]))
        poke(r0 + 6, 1, rng.randrange(256))

        rm.present(m, cur, 9 if control == 'radius9' else 8)
        s.call(0x12f2, a1=r0)
        sc.check(m, '$12f2')
        rm.others(m)
        s.call(0x4ade)
        sc.check(m, '$4ade')
        exp = rm.offer(m, cur, control == 'anybuilding')
        offered += exp
        s.call(0x1142, a0=r0, a1=SLOT_ICONS, a2=0x245fe, a3=SLOT_ACTIONS, a4=0x24284, a6=rm.A6, d0=0)
        got_d0 = s.reg('d0') & 0xffff
        act = int.from_bytes(s.read(SLOT_ACTIONS, 4), 'big')
        sc.check(m, '$1142', got_d0 == exp and (not exp or act & 0xffffff == 0x489c))
        exp = rm.radio_offer(m, cur, control == 'radioany')
        roffered += exp
        s.call(0x1102, a0=r0, a1=SLOT_ICONS, a2=0x245fe, a3=SLOT_ACTIONS, a4=0x24284, a6=rm.A6, d0=0)
        got_d0 = s.reg('d0') & 0xffff
        act = int.from_bytes(s.read(SLOT_ACTIONS, 4), 'big')
        sc.check(m, '$1102', got_d0 == exp and (not exp or act & 0xffffff == 0xf94c))
        fork2 = s('fork')['id']
        mem2 = bytes(m.b)
        n = rm.non_members(m)
        s.call(0xfab4)
        sc.check(m, '$fab4', s.reg('d1') & 0xffff == n)
        if n:
            s('restore', id=fork2)
            m = Mem(mem2)
            s.call(0xfa78, stops=[0xfa84])
            rnd = s.reg('d0')
            s('run', max_steps=100000, until_pc=0x800)
            rm.radio_pick(m, rnd, 0xffff if control == 'pickfull' else 0x1f)
            sc.check(m, '$fa78')
        s('restore', id=fork2)
        s('drop', id=fork2)
        m = Mem(mem2)
        others = [m.u8(rm.OTHERS + j) for j in range(33) if m.u8(rm.OTHERS + j) < 0x80]
        cand = rng.choice(others) if others and rng.random() < 0.6 else rng.randrange(32)
        poke(rm.rec(cand) + 1, 1, rng.choice([0, 5, 128, 200, 230, 249, rng.randrange(256)]))
        if rng.random() < 0.3:
            poke(rm.NAMEFMT + cand, 1, rng.randrange(8))
        rm.recruit(m, cand, cur, **kw[control])
        s('poke', addr=rm.CAND, width=2, value=cand)
        s.call(0x496c, a6=rm.A6)
        sc.check(m, '$496c')
    s('shutdown')
    for k in sc.n:
        print(f'{k}: {sc.ok[k]}/{sc.n[k]}')
    print(f'recruit offered in {offered} states, radio in {roffered}; branches:', ' '.join(f'{k}={v}' for k, v in sorted(rm.BRANCH.items())))
    print('PASS' if all(sc.ok[k] == sc.n[k] for k in sc.n) else 'FAIL')


if __name__ == '__main__':
    main()
