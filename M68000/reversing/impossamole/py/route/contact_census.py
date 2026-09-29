"""Object-contact census for any replayable .repl: which object `A0` reaches `$e82e` (`move.b 104(A0),$227f6`), and where.

    uv run python reversing/impossamole/py/route/contact_census.py <start.snap> <a.repl> [<b.repl> ...]

Runs the .repl files back to back in one emulator process from `start.snap`, with every `s n` executed as `bp e82e n`
(+ `s 1` past each hit), as `hazard_census.py` does for the hop-3 route, but for arbitrary files and with the object's
handler pointer (record byte 86, e.g. `$01417c` chasing bee) so a contact is named by what it is, not only by its
animation. One line per contact; the totals join the handler to the animation entry and damage byte. Snapshots and
`q` in the files are skipped; pokes and `kbd` lines run as recorded. Start snapshot and .repl paths are relative to
`M68000/` (or absolute).
"""
import collections, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hazard_census import Repl, ROOT, OBJ0, STRIDE, s16, body


def main(start, files):
    r = Repl(start if os.path.isabs(start) else os.path.join(ROOT, start))
    total, events = 0, []
    for f in files:
        for c in body(f if os.path.isabs(f) else os.path.join(ROOT, f)):
            if not c.startswith('s '):
                r.run(c); continue
            left = int(c.split()[1])
            while left > 0:
                txt = '\n'.join(r.run(f'bp e82e {left}'))
                m = re.search(r'hit \(\d+/\d+\) after (\d+) step', txt)
                if not m:
                    total += left; break
                k = int(m.group(1))
                a0 = int(re.search(r'A0:([0-9a-f]{8})', txt).group(1), 16)
                obj = r.mem(a0, 108)
                hero = r.mem(0x1a572, 8); cam = int.from_bytes(r.mem(0x227b6, 2), 'big'); hp = r.mem(0xbb74, 1)[0]
                ev = dict(file=os.path.basename(f), t=total + k, slot=(a0 - OBJ0) // STRIDE, type=int.from_bytes(obj[0:2], 'big'),
                          x=s16(int.from_bytes(obj[2:4], 'big')), y=s16(int.from_bytes(obj[4:6], 'big')),
                          handler=int.from_bytes(obj[86:90], 'big'), anim=int.from_bytes(obj[22:26], 'big'), dmg=obj[104], hp=obj[103],
                          hx=int.from_bytes(hero[2:4], 'big'), hy=s16(int.from_bytes(hero[4:6], 'big')), hp_before=hp,
                          wx=int.from_bytes(hero[2:4], 'big') - 32 + cam)
                events.append(ev)
                print('  ' + ' '.join(f'{a}={b:#x}' if a in ('handler', 'anim') else f'{a}={b}' for a, b in ev.items()), flush=True)
                r.run('s 1')
                total += k + 1; left -= k + 1
    r.close()
    print(f'{total} steps, {len(events)} contacts')
    for (h, an, dm), v in collections.Counter((e['handler'], e['anim'], e['dmg']) for e in events).most_common():
        print(f'  x{v:<3} handler=${h:x} anim=${an:x} dmg={dm}')


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    main(sys.argv[1], sys.argv[2:])
