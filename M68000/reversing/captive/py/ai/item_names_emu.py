"""Control for item_names.py: run federation's own $675c (on a record whose byte 1 = type) and $70b8 under stserver.
Usage: item_names_emu.py <snap> <type_hex>..."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cap import R, StServer, snappath  # noqa: E402
s = StServer(R); s('load', snapshot=snappath(sys.argv[1]))
rec = s.reg('a7') - 0x400
for t in sys.argv[2:]:
    s('poke', addr=rec, width=4, value=int(t, 16) << 16)
    s.call(0x675c, a0=rec)
    d0 = s.reg('d0') & 0xffff
    s.call(0x70b8, d7=(d0 - 1) & 0xffff)
    a0 = s.reg('a0')
    raw = s.read(a0, 24)
    print(f'type ${t} -> $675c D0 ${d0:02x} -> $70b8 A0 ${a0:06x} {raw.split(bytes(1))[0].decode("latin1")!r}')
s.close()
