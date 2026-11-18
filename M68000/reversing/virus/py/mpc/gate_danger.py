"""Gate for shot.ship_hit: the actor walker's ship box ($215ea..$21654), by POKING the ship next to an actor.

    uv run python gate_danger.py [--control c1]      (control: the box taken as -$c0 < d <= $c0)

From demo/S1b.snap the autopilot flies to arrival K; there the machine is forked and, per trial, the ship's position
($270b0) is poked to (the actor's position after this tick's walker pass, from shot.actor_step) + offset, its velocity
to 0, and the controls to "hold attitude, no thrust, no fire", so the ship does not move in the tick. Observed: the
breakpoint $21654 (the store of $62a5d) in tick K, and the death exit in tick K+1. Labelled poke: the box is the
game's, the encounter is not.
"""
import os, struct, sys
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import replay as R
import shot as S

c1 = '--control' in sys.argv
snap = os.path.join(R.ROOT, 'scratchpad/virus/demo/S1b.snap')
g = R.Game(snap); s = g.s
rd = lambda a, n: bytes.fromhex(s('read', addr=a, len=n))
OFFS = []
for ax in range(3):
    for d in (-0xc1, -0xc0, 0xbf, 0xc0):
        o = [0, 0, 0]; o[ax] = d; OFFS.append(o)
OFFS += [[-0xc0, -0xc0, -0xc0], [0xbf, 0xbf, 0xbf], [0xbf, -0xc0, 0xc0], [-0xc1, 0xbf, 0xbf], [0, 0, 0], [0x200, 0, 0]]
tot = [0, 0]; inside = 0
try:
    s('bp_set', addrs=[0x21654])
    ok, *_ = g.run_to_tick(3000000); assert ok
    k = 0
    for K, want in ((130, (S.B_SEEDER_FLY,)), (330, (S.B_PATROL_HOME, S.B_PATROL_ATTACK, S.B_PATROL_CRUISE)),
                    (60, (S.B_WAIT_SEEDER,)), (30, (S.B_WAIT_SEEDER,)), (215, (S.B_PATROL_CRUISE,))):
        if K < k:
            s('load', snapshot=snap); ok, *_ = g.run_to_tick(3000000); k = 0
        while k < K:
            steps = 0; path = []
            while True:
                ok, p, ext, _, st, why = g.run_to_tick(8000000); steps += st; path += p
                if not (ok and steps < 64 and not path): break
            k += 1
        fid = s('fork')['id']
        pool = S.unpack_pool(rd(0x31d54, 20 * struct.unpack('>h', rd(0x32a3e, 2))[0]))
        t44 = struct.unpack('>H', rd(0x32a44, 2))[0]; q0 = list(struct.unpack('>3h', rd(0x27134, 6)))
        idx = [i for i, a in enumerate(pool) if a[8] in want][0]
        att = struct.unpack('>2h', rd(0x32a32, 4))
        for off in OFFS:
            s('restore', id=fid)
            a = pool[idx]
            # the patrol reads the ship's position: iterate the fixed point (ship = actor' + off, actor' = f(ship))
            ship = [S.s16(a[i] + off[i]) for i in range(3)]
            for _ in range(6):
                nxt, info = S.actor_step(a, ship=ship, tick48=t44 + idx + 1, queue0=q0)
                ship2 = [S.s16(nxt[i] + off[i]) for i in range(3)]
                if ship2 == ship: break
                ship = ship2
            for i in range(3):
                s('poke', addr=0x270b0 + 2 * i, width=2, value=ship[i] & 0xffff)
                s('poke', addr=0x270b6 + 2 * i, width=2, value=0)
            regs = s('regs')
            g.set_controls(regs, [att[0] & 0xffff, att[1] & 0xffff, 0])
            ok, path, ext, _, st, why = g.run_to_tick(8000000)
            got = '$21654' in path
            ship_after = list(struct.unpack('>3h', rd(0x270b0, 6)))
            act_after = S.unpack_pool(rd(0x31d54 + 20 * idx, 20))[0]
            reaches_tail = nxt[8] not in (S.B_PATROL_CRUISE, S.B_WAIT_SEEDER, S.B_WAIT_PATROL, S.B_WAIT_CHASER)
            if c1:
                pred = reaches_tail and all(-0xc0 < S.s16(ship_after[i] - nxt[i]) <= 0xc0 for i in range(3))
            else:
                pred = reaches_tail and S.ship_hit(ship_after, nxt[:3])
            moved_ok = ship_after == ship and act_after[:3] == nxt[:3]
            ok2, path2, *_ = g.run_to_tick(8000000, stop_dead=True)
            dead = 'dead' in path2
            good = pred == got and dead == got and moved_ok
            tot[0] += good; tot[1] += 1; inside += got
            print(f'K={K} actor {idx} {S.KINDS[a[8]][:2]} -> {S.KINDS[nxt[8]][1]:8s} off {off}  model {pred!s:5s} '
                  f'$21654 {got!s:5s} dead next tick {dead!s:5s} placed {moved_ok} path {path} {"ok" if good else "MISMATCH"}')
        s('drop', id=fid)
finally:
    g.close()
print(f'ship box{" (control: -$c0 < d <= $c0)" if c1 else ""}: {tot[0]}/{tot[1]} trials agree; ship hit in {inside} of them')
