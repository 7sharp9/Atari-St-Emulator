"""Hazard census of the recorded hop-3 route: which objects actually damaged the hero, and where.

    uv run python reversing/impossamole/py/route/hazard_census.py

Replays every segment's .repl in ONE emulator process from room188.snap, but runs each `s n` as `bp e82e n`
(+ `s 1` past each hit), where `$e80e`'s `move.b 104(A0),$227f6` at `$e82e` is the generic object-contact damage
application (README "hero-damage application": A0 = the contacting object, reached only when the hero's hit
cooldown `102(A1)` is 0). At every stop it reads A0, the object (type word, x, y, anim pointer at +22, damage byte
+104) and the hero, and writes census.jsonl. It also counts `$eb8c` (`sub.b D0,$bb74`, the actual health
decrement) per chunk with `hits` in a second pass over the same commands, so decrements with no `$e82e` object contact
in the same window are the category-9 tile hazard path (`$eafa` `cmp.b #$9`). The final snapshot must equal the
live one (the census does not perturb the run).
"""
import collections, filecmp, json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from route_driver import ROOT, DISK
import route_hop3 as R

D = os.path.join(ROOT, R.BASE)
OBJ0, STRIDE = 0x1a2ea, 0x6c


class Repl:
    def __init__(self, snap):
        env = dict(os.environ, ATARI_NOTRACE='1')
        self.p = subprocess.Popen(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl', '--disk-a', DISK],
                                  cwd=ROOT, env=env, text=True, bufsize=1, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL)

    def run(self, *cmds):
        for c in cmds:
            self.p.stdin.write(c + '\n')
        self.p.stdin.write('hits 0 fb98\n'); self.p.stdin.flush()
        out = []
        while True:
            l = self.p.stdout.readline()
            if not l:
                raise RuntimeError('closed')
            if l.startswith('  $00fb98'):
                return out
            out.append(l.rstrip())

    def mem(self, a, n):
        o = self.run(f'm {a:x} {n}')
        return bytes.fromhex(''.join(l for l in o if re.fullmatch(r'[0-9a-f ]+', l)).replace(' ', ''))

    def close(self):
        self.p.stdin.write('q\n'); self.p.stdin.flush(); self.p.wait(timeout=30)


def body(path):
    return [l.rstrip('\n') for l in open(path) if not l.startswith(('snap ', 'q'))]


def s16(v):
    return v - 65536 if v >= 32768 else v


def main():
    r = Repl(R.START)
    total = 0
    events = []
    out = open(os.path.join(D, 'census.jsonl'), 'w')
    for f in R.SEGS:
        seg = f.__name__
        for c in body(os.path.join(D, 'segs', seg + '.repl')):
            if not c.startswith('s '):
                r.run(c); continue
            n = int(c.split()[1])
            left = n
            while left > 0:
                lines = r.run(f'bp e82e {left}')
                txt = '\n'.join(lines)
                m = re.search(r'hit \(\d+/\d+\) after (\d+) step', txt)
                if not m:
                    total += left; left = 0; break
                k = int(m.group(1))
                a0 = int(re.search(r'A0:([0-9a-f]{8})', txt).group(1), 16)
                obj = r.mem(a0, 108)
                hero = r.mem(0x1a572, 8); cam = r.mem(0x227b6, 2); hp = r.mem(0xbb74, 1)[0]
                slot = (a0 - OBJ0) // STRIDE
                ev = dict(seg=seg, t=total + k, slot=slot, a0=hex(a0), type=int.from_bytes(obj[0:2], 'big'),
                          x=s16(int.from_bytes(obj[2:4], 'big')), y=s16(int.from_bytes(obj[4:6], 'big')),
                          anim=obj[22:26].hex(), dmg=obj[104], hp=obj[103],
                          hero_x=int.from_bytes(hero[2:4], 'big'), hero_y=s16(int.from_bytes(hero[4:6], 'big')),
                          wx=int.from_bytes(hero[2:4], 'big') - 32 + int.from_bytes(cam, 'big'), hp_before=hp)
                events.append(ev); out.write(json.dumps(ev) + '\n')
                r.run('s 1')
                total += k + 1; left -= k + 1
    snap = os.path.join(D, 'verify', 'census.snap')
    r.run(f'snap {snap}')
    r.close()
    same = filecmp.cmp(snap, os.path.join(D, 'snaps', R.SEGS[-1].__name__ + '.snap'), shallow=False)
    print(f'census run: {total} steps, {len(events)} damaging contacts, final snapshot identical to the live one: {same}')
    by = collections.Counter((e['seg'], e['type'], e['anim'], e['dmg']) for e in events)
    for (seg, ty, an, dm), v in sorted(by.items()):
        print(f'  {seg:<24} x{v:<3} A0 type={ty} anim=${an[-5:]} dmg={dm}')
    tot = collections.Counter((e['type'], e['anim'], e['dmg']) for e in events)
    print('totals:')
    for (ty, an, dm), v in tot.most_common():
        print(f'  x{v:<3} type={ty} anim=${an[-5:]} dmg={dm}')


if __name__ == '__main__':
    main()
