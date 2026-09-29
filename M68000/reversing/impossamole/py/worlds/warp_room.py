"""Poke the hero onto a room-exit trigger of the snapshot's world, run the transition, snapshot the new room.

    uv run python <this dir>/warp_room.py <in.snap> <out.snap> <trigger block> <dir 0=top|1=bottom> [--steps N]
                                            [--pre CMDS] [--post CMDS]

STAGING IS POKED (label it as such): the camera $227b6/limit $227b8, hero x/y ($1a574/$1a576), state $227f3 and
health ($bb74) are written so the exit checker $df4a fires exactly as README "The level is one tile map of connected
rooms" describes (state 3 + y >= $c8 = bottom exit, state 2 + y <= $fff0 = top exit; block =
(x - $20 + camera + 16) >> 5). The checker searches the world's whole record list, not only the current room's, so
any record can be triggered from any room. Camera is set to the trigger block's own room limit guess
(block*32 - 128 + 8), x follows from the block formula. Writes the REPL script next to <out.snap> (.repl) and runs
the DLL with ATARI_NOTRACE=1. Default 3,000,000 steps after the poke (the $1c3c8 fade takes several hundred
thousand steps, the spawner needs more when a boss record is in the new room).
"""
import os, struct, subprocess, sys
from pathlib import Path

ROOT = Path(os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))))
sys.path.insert(0, str(ROOT / 'tools'))
from pm_export import ram_from_snap  # noqa: E402

DISK = 'scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st'


def poke_script(ram, block, direction, steps, pre=(), post=()):
    cam = block * 32 - 120
    x = block * 32 + 24 - cam
    y = 0xd4 if direction == 1 else 0xffe8
    state = 3 if direction == 1 else 2
    lim = struct.unpack_from('>H', ram, 0x227b8)[0]
    b = bytes(ram[0x227f0:0x227f4])
    L = list(pre)
    L.append('w 227b6 %04x%04x' % (cam, cam))          # camera and limit (limit poked equal: no scroll clamp)
    L.append('w 1a574 %04x%04x' % (x, y & 0xffff))      # hero x, y
    L.append('w 227f0 %02x%02x%02x%02x' % (b[0], b[1], b[2], state))
    L.append('w bb74 %02x%02x%02x%02x' % (ram[0xbb75], ram[0xbb75], ram[0xbb76], ram[0xbb77]))  # health full
    L.append(f's {steps}')
    L += list(post)
    return L, (cam, x, y, state, lim)


def main():
    a = sys.argv[1:]
    src, dst, block, direction = a[0], a[1], int(a[2]), int(a[3])
    steps = int(a[a.index('--steps') + 1]) if '--steps' in a else 3000000
    post = a[a.index('--post') + 1].split(';') if '--post' in a else []
    ram = ram_from_snap(Path(src))
    L, info = poke_script(ram, block, direction, steps, post=post)
    L += [f'snap {dst}', 'm 227b4 6', 'm 1a574 4', 'm 227f3 1', 'quit']
    rp = Path(ROOT, dst).with_suffix('.repl')
    rp.write_text('\n'.join(L) + '\n')
    env = dict(os.environ, ATARI_NOTRACE='1')
    r = subprocess.run(['dotnet', 'exec', 'bin/Debug/net8.0/M68000.dll', 'resume', src, 'repl', '--disk-a', DISK],
                       stdin=open(rp), capture_output=True, text=True, cwd=ROOT, env=env)
    print('pokes (cam, x, y, state, old limit):', info)
    print(''.join(l + '\n' for l in (r.stdout + r.stderr).splitlines() if not l.startswith('enqueued'))[-600:])


if __name__ == '__main__':
    main()
