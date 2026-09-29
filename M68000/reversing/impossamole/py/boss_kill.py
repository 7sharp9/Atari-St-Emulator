"""Drive the Amazon boss fight from a snapshot with a live REPL and adaptive pokes (99th pass).

    ATARI_NOTRACE=1 uv run python reversing/impossamole/py/boss_kill.py <snap> [max_pulses]

Loop: keep health full (labelled poke), read the boss (slot 7, $1a5de: x=2, y=4, anim ptr 22, HP 103,
$1a645), fire a real pulse (kbd 80, alternating make/break), and while the boss is not in its shielded
idle animation ($221f6) move projectile slot 16 ($1a9ac) onto the boss's x,y so the contact test
($00b71a) finds it. Everything except the projectile position is natural; the position poke stands in
for aiming a real shot at the boss's spot. Stops when the boss slot goes inactive or $22803 != 1.
"""
import os, subprocess, sys
MROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
DISK = 'scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st'


class Repl:
    def __init__(self, snap):
        env = dict(os.environ, ATARI_NOTRACE='1')
        self.p = subprocess.Popen(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', snap, 'repl',
                                   '--disk-a', DISK], cwd=MROOT, env=env, text=True, bufsize=1,
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.run('s 1')

    def run(self, *cmds):
        """Send commands, then a sentinel `hits 0 fb98`; return the output lines before it."""
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
    snap = sys.argv[1]; maxp = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    r = Repl(snap)
    log = []
    for i in range(maxp):
        b = r.mem(0x1a5de, 108)
        x, y = int.from_bytes(b[2:4], 'big'), int.from_bytes(b[4:6], 'big')
        anim, hp = int.from_bytes(b[22:26], 'big'), b[103]
        flag = r.mem(0x22803, 1)[0]
        log.append((i, x, y, hex(anim), hp, flag))
        if i % 10 == 0:
            print(i, 'boss x,y', x, y, 'anim', hex(anim), 'hp', hp, '$22803', flag, flush=True)
        if b[1] == 0 and b[0] == 0 or flag != 1:
            print('stop: boss slot', b[:2].hex(), '$22803', flag); break
        poke = [] if anim == 0x221f6 else [f'w 1a9ac {x:04x}{y:04x}']
        r.run('w bb74 12120300', 'kbd ff', 'kbd 80', 's 20000', *poke, 's 30000', 'w bb74 12120300',
              'kbd ff', 'kbd 00', 's 100000')
    print('final', log[-1])
    r.run('snap ' + os.path.join(MROOT, 'scratchpad/impossamole/pass99/boss_kill_end.snap'))
    r.p.stdin.write('q\n'); r.p.stdin.flush()


if __name__ == '__main__':
    main()
