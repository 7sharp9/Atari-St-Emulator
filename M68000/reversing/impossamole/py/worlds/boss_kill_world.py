"""Drive a boss fight of any world from a boss-room snapshot with a live REPL and adaptive pokes.

    ATARI_NOTRACE=1 uv run python <this> <boss_room.snap> <out_end.snap> [max_pulses]

Generalises reversing/impossamole/py/boss_kill.py (which pokes `w bb74 12120300`, i.e. world index 3,
into $bb76 and gates on the Amazon animation $221f6): here the health poke keeps the snapshot's own
$bb76 and the shot is placed on the boss every pulse whatever its animation (the handler decides
whether the hit lands: the HP byte 103(A0) at $1a645 is what is logged). Everything except the
projectile position is natural: health is poked full (labelled), fire is a real pulse (kbd 80 held
20000 steps), projectile slot 16 ($1a9ac) is poked onto the boss slot 7's (x, y) so the contact test
$b71a finds it. Stops when $22803 != 1 (boss death sets $ff) or the boss slot is freed.
"""
import os, subprocess, sys
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')))
DISK = 'scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st'


class Repl:
    def __init__(self, snap):
        env = dict(os.environ, ATARI_NOTRACE='1')
        self.p = subprocess.Popen(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl',
                                   '--disk-a', DISK], cwd=ROOT, env=env, text=True, bufsize=1,
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.run('s 1')

    def run(self, *cmds):
        """Send commands then a sentinel `hits 0 fb98`; return the output lines before it."""
        for c in cmds:
            self.p.stdin.write(c + '\n')
        self.p.stdin.write('hits 0 fb98\n'); self.p.stdin.flush()
        out = []
        while True:
            l = self.p.stdout.readline()
            if not l:
                raise RuntimeError('repl closed')
            if l.startswith('  $00fb98'):
                return [x.rstrip() for x in out if not x.startswith(('enqueued', '---'))]
            out.append(l)

    def mem(self, addr, n):
        return bytes.fromhex(''.join(self.run(f'm {addr:x} {n}')[-1:]).replace(' ', ''))


def main():
    snap, out = sys.argv[1], sys.argv[2]
    maxp = int(sys.argv[3]) if len(sys.argv) > 3 else 300
    r = Repl(snap)
    world = r.mem(0xbb76, 1)[0]
    hp_poke = f'w bb74 1212{world:02x}00'   # health, max health, world index (unchanged), $bb77
    log = []
    for i in range(maxp):
        b = r.mem(0x1a5de, 108)
        x, y = int.from_bytes(b[2:4], 'big'), int.from_bytes(b[4:6], 'big')
        anim, hp = int.from_bytes(b[22:26], 'big'), b[103]
        flag = r.mem(0x22803, 1)[0]
        log.append((i, x, y, hex(anim), hp, flag))
        if i % 10 == 0:
            print(i, 'boss x,y', x, y, 'anim', hex(anim), 'hp', hp, 'busy', b[79], '$22803', flag, flush=True)
        if flag != 1:
            print('stop: boss slot', b[:2].hex(), '$22803', flag); break
        r.run(hp_poke, 'kbd ff', 'kbd 80', 's 20000', f'w 1a9ac {x:04x}{y:04x}', 's 30000', hp_poke,
              'kbd ff', 'kbd 00', 's 100000')
    print('final', log[-1])
    hps = [l[4] for l in log]
    print('hp sequence (distinct, in order):', [h for k, h in enumerate(hps) if k == 0 or h != hps[k - 1]])
    r.run('snap ' + out)
    r.p.stdin.write('q\n'); r.p.stdin.flush()


if __name__ == '__main__':
    main()
