"""Live proof that hit points 254/255 make an enemy immune to shots (README "Spawn types", item a).

    ATARI_NOTRACE=1 uv run python immune_shot.py

`$013a9c` (the shot-vs-enemy test each handler calls, A0 = the enemy) on a contact with a live shot clears both objects'
contact links, marks a normal shot spent (`move.b #$ff,101(A1)` at `$013b0e`/`$013b04`), then
    $013b14: tst.b 103(A0)      ; enemy hit points
    $013b18: bmi  $013b3e       ; negative as a signed byte (bit 7 set: 254 and 255 both) -> skip the damage
    $013b20: sub.b D1,103(A0)   ; 104(A1) = shot damage = weapon index $bb72
so an enemy with hp >= $80 takes no damage and the shot is still consumed; the subtract, the invulnerability count
(`102(A0)`) and the death path `$013b4c` are never reached.

Per case: health poked full (labelled); one real fire pulse (`kbd 80` held one poll cycle) creates the shot in slot 16
(`$1a9aa`); its x,y (`$1a9ac`) is then POKED to the centre of the enemy's hit box (x + 8(A0), y + 10(A0)) (labelled: stands in for aiming, as in boss_kill.py). `hits`
counts `$013b14` (contact reached the hp test), `$013b20` (damage subtract) and `$013b4c` (death). Retries (max 4) when
no contact happened. Prints hit points before/after and the shot's 101 flag.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from replx import Repl

P = 'scratchpad/impossamole/'


def prep_child(r):
    """Type 109 (`$13cb4`): the shot test runs on the child block (slots 12-15), not the parent: run until it exists."""
    for _ in range(80):
        r.run('s 1', 'bp b4de 200000')
        if r.obj(12)['tw']:
            return 12
    raise RuntimeError('child never appeared')


def prep_emerge(slot):
    """Type 111 (`$15a38`): shots are only tested once the tentacle is up; poke the hero into its trigger box (labelled)."""
    def f(r):
        o = r.obj(slot)
        r.poke(0x1a574, (o['x'] & 0xffff).to_bytes(2, 'big') + (o['y'] & 0xffff).to_bytes(2, 'big'))
        for _ in range(80):
            r.run('s 1', 'bp b4de 200000')
            if r.obj(slot)['frame'] != 62 and r.obj(slot)['fidx'] >= 4:
                return slot
        raise RuntimeError('tentacle never emerged')
    return f


CASES = [  # snapshot, slot, label, prep(r) -> slot to shoot
    (P + 'pass99/warp_up112.snap', 8, 'type 114 bee, hp 1 (control)', None),
    (P + 'pass99/cyc0.snap', 8, 'type 112 plant, hp 4 (control)', None),
    (P + 'pass99/warp_up112.snap', 7, 'type 125 flier, hp 255', None),
    (P + 'pass99/cyc2.snap', 9, 'type 117 flier, hp 255', None),
    (P + 'agents/hop4/room299_poked.snap', 7, 'type 116 flier, hp 255', None),
    (P + 'gameplay_explore/ru_step8M.snap', 8, 'type 130 crocodile, hp 254', None),
    (P + 'pass103/live_c1.snap', 10, 'type 113 rock, hp 255', None),
    (P + 'pass103/live_c20.snap', 8, 'type 109 slab child block (parent hp 254, child 255)', prep_child),
    (P + 'pass99/cyc5.snap', 10, 'type 111 tentacle (emerged), hp 255', prep_emerge(10)),
    (P + 'pass103/room160.snap', 9, 'type 129 chameleon, hp 255', None),
]


def shot(r, slot, clear101=False):
    """Fire one shot and poke it onto the enemy in `slot`. Returns hits dict and hp/inv/dead before and after.
    clear101: also poke the shot's 101 byte back to 0 (a shot fired into a wall is spent at once, 101 = 1, and could
    never touch the enemy: labelled fallback)."""
    o0 = r.obj(slot)
    # fire only while the hero is idle or walking ($227f3 < 3), or the pulse does nothing
    for _ in range(6):
        if r.mem(0x227f3, 1)[0] < 3:
            break
        r.run('s 1', 'bp b4de 200000')
    r.run('w bb74 12120300', 'kbd ff', 'kbd 80', 's 30000', 'kbd ff', 'kbd 00', 's 2000')
    o = r.obj(slot)
    import struct
    off8, off10 = struct.unpack_from('>hh', o['raw'], 8)      # centre the shot's (zero-offset) box on the enemy's hit box
    r.run(f"w 1a9ac {(o['x'] + off8) & 0xffff:04x}{(o['y'] + off10) & 0xffff:04x}")
    if clear101:
        b = r.mem(0x1aa0c, 4)
        r.run(f"w 1aa0c {b[:3].hex()}00")
    out = r.run('hits 30000 13b14 13b20 13b4c')
    n = {l.split()[0]: int(l.split()[1]) for l in out}
    p = r.obj(16)
    o1 = r.obj(slot)
    return dict(hp0=o0['hp'], hp1=o1['hp'], inv=o1['inv'], dead=o1['dead'], hit=n['$013b14'], sub=n['$013b20'], die=n['$013b4c'],
                shot101=p['dead'], shot_dmg=p['dmg'])


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else ''
    for snap, slot, label, prep in CASES:
        if only not in label:
            continue
        with Repl(snap) as r:
            res = None
            if prep:
                slot = prep(r)
            for attempt in range(1, 7):
                res = shot(r, slot, clear101=attempt >= 3)
                if res['hit']:
                    break
                r.run('s 20000')
            print(f"{label:34s} {os.path.basename(snap):22s} slot {slot:2d} attempt {attempt}{' (101 poked to 0)' if attempt >= 3 else ''}: hp {res['hp0']} -> {res['hp1']}, "
                  f"$13b14 x{res['hit']}, $13b20 (subtract) x{res['sub']}, $13b4c (death) x{res['die']}, "
                  f"enemy 102={res['inv']} 101={res['dead']}, shot 101={res['shot101']:#04x} dmg {res['shot_dmg']}", flush=True)


if __name__ == '__main__':
    main()
