import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssh import *
r = R(sscfg.SNAP_ATTRACT)
rom = bytearray()
a = 0xfc0000
while a < 0xfc0000 + 0x30000:
    rom += r.mem(a, 0x8000); a += 0x8000
r.close()
i = -1
while True:
    i = rom.find(bytes.fromhex('31415926'), i + 1)
    if i < 0: break
    print('magic at %x' % (0xfc0000 + i))
open(os.path.join(AGENT, 'tmp', 'rom.bin'), 'wb').write(rom)
