"""Check the fire handler's swipe against the tables (agents/boss, 104th pass): for each weapon 1-3, each facing and
both standing and jumping, fire a real pulse (kbd 80) and compare slot 16-19 ($1a9aa, stride 108) with what `$d3cc`
should write, then time the swipe's lifetime.

    uv run python reversing/impossamole/py/boss/swipe_check.py [--snap S]

Expected per case (all from the disassembly, README "Natural aim"): slot 16 type word 1, x = hero x + dx (+ mirror word
when $227f4 != 0), y = hero y + dy, radii (12, 13) = (w, h) of the weapon row, 30(A1) = $ff (the only slot
`$13a9c` tests), 104(A1) = $bb72; slots 17-19 carry 30(A1) = $10 (decoration, never tested) and no damage; the four
slots are cleared 6 frames after the shot ($227fd: 6 -> 0, `$d2a0`). Pokes (labelled): the weapon byte $bb72, and
health. Prints one line per case and a final `match N/M`.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from repl import Repl, slot, w, sw

FRAME = 24000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--snap', default='scratchpad/impossamole/pass99/boss_room.snap')
    a = ap.parse_args()
    ok = tot = 0
    for wpn in (1, 2, 3):
        t = None
        for face_key, face in ((0x08, 1), (0x04, 0)):
            for air in (False, True):
                r = Repl(a.snap)
                cur = r.mem(0xbb72, 4)
                r.run('w bb72 %02x%s' % (wpn, cur[1:].hex()), 'w bb74 12120300')
                row = r.mem(0xd4be + (wpn - 1) * 64, 8)
                dx, dy, rw, rh = sw(row, 2), sw(row, 4), row[6], row[7]
                mir = sw(r.mem(0xd57e + (wpn - 1) * 2, 2), 0)
                # walk a little so $227f4 takes the facing (right walk -> 1, left walk -> 0)
                r.run('kbd ff', f'kbd {face_key:02x}', 's 120000', 'kbd ff', 'kbd 00', 's 60000')
                if air:
                    r.run('kbd ff', 'kbd 01', 's 100000', 'kbd ff', 'kbd 00', 's 30000')
                r.run('kbd ff', 'kbd 80')
                out = r.run('bp d3cc 400000')          # stop at the shot spawner's entry: hero x/y at spawn time
                hero = r.mem(0x1a572, 108)
                hx, hy, face_live = sw(hero, 2), sw(hero, 4), r.mem(0x227f4, 1)[0]
                st = r.mem(0x227f3, 1)[0]
                r.run('s 3000')                        # past $d4bc (rts): the slots are written
                s16 = slot(r, 16)
                r.run('kbd ff', 'kbd 00')
                fd = r.mem(0x227fd, 1)[0]
                exp_x = hx + dx + (mir if face_live else 0)
                exp_y = hy + dy
                cases = {
                    'type=1': w(s16, 0) == 1,
                    'x': sw(s16, 2) == exp_x,
                    'y': sw(s16, 4) == exp_y,
                    'radii': (s16[12], s16[13]) == (rw, rh),
                    '30=ff': w(s16, 30) == 0xff,
                    'dmg=weapon': s16[104] == wpn,
                    'deco slots 17-19 30=$10': all(w(slot(r, n), 30) == 0x10 for n in (17, 18, 19)),
                }
                # lifetime: frames until slot 16 clears
                frames = None
                for i in range(1, 40):
                    r.run(f's {FRAME // 4}')
                    if w(slot(r, 16), 0) == 0:
                        frames = i / 4
                        break
                cases['lifetime 5-7 frames from the spawn'] = frames is not None and 5 <= frames <= 7
                cases['facing as walked'] = face_live == face
                n_ok = sum(cases.values())
                ok += n_ok; tot += len(cases)
                bad = [k for k, v in cases.items() if not v]
                print(f'weapon {wpn} face {face}/{face_live} air={air} st={st} hero=({hx},{hy}) slot16=({sw(s16,2)},{sw(s16,4)}) '
                      f'expected=({exp_x},{exp_y}) r={s16[12]},{s16[13]} dmg={s16[104]} fd_after_hold={fd} '
                      f'life~{frames} frames after hold; {n_ok}/{len(cases)}' + (f' FAIL {bad}' if bad else ''))
                r.close()
    print(f'match {ok}/{tot}')


if __name__ == '__main__':
    main()
