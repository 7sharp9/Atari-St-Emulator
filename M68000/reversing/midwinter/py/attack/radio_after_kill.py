"""After drive_kill's fire arm stops in the radio message's key wait ($d0f4), render it, press a key and follow."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import gate_shot as gs, drive_kill as dk
OUT = os.path.join(gs.WORK, 'shot'); os.makedirs(OUT, exist_ok=True)
from stclient import StServer
s = StServer(gs.root)
s('load', snapshot=os.path.join(gs.WORK, 'd_ski.snap'), disk=os.path.join(gs.WORK, 'zuul067.st'))
fork = s('fork')['id']
n, ok, hits, before, after, end, unit = dk.arm(s, fork, True, 40)
print('stopped', end, 'pc', hex(s.reg('pc')))
s('render', path=os.path.join(OUT, 'radio_kill.png'))
s('kbd', bytes=[0x39]); s('run', max_steps=30000); s('kbd', bytes=[0xb9])
s('bp_set', addrs=[0x12a5e, 0x3b12, 0x4ede])
r = s('run', max_steps=20000000)
print('after key:', r['reason'], hex(s.reg('pc')), 'mode', s.read(0x24482, 2).hex(), '$12d76', s.read(0x12d76, 4).hex())
s('bp_clear', addrs=[0x12a5e, 0x3b12, 0x4ede])
s('run', max_steps=3000000)
s('render', path=os.path.join(OUT, 'radio_kill_after.png'))
s('shutdown')
