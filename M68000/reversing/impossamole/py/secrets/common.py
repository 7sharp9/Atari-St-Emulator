import os, sys, struct
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')))
sys.path.insert(0, ROOT + '/tools')
from disassemble import ram_from_snap
GAME = ROOT + '/scratchpad/impossamole/agents/unpoked/s11/seg11_shaft_exit.snap'
BOSS = ROOT + '/scratchpad/impossamole/agents/hop4/boss_room_real_settled.snap'
EXTR = ROOT + '/scratchpad/impossamole/extracted'
DISK = ROOT + '/scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st'
WORK = ROOT + '/scratchpad/impossamole/agents/secrets'
def ram(p=GAME): return ram_from_snap(p)
def rd(f): return open(f if f.startswith('/') else EXTR + '/' + f, 'rb').read()
