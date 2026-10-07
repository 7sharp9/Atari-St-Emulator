"""text_atlas.py <snap>: every primary message of the packed text table ($075876 offsets, $076046 stream, (A5)+168/172, decoded through
the 6-bit map at $005ac0 -- py/name_strings.py's decoder), index 0-389, one per line: the text up to its first NUL (the stream carries
several messages back to back; each index starts at its own).  Indices past 389 decode to a repeating `DOOR` pattern then zero padding
(mechanics.md section 8).  Also prints the assert strings ($0172c8-$017951, plain ASCII) and the plain-ASCII UI strings ($0062xx-$0067xx).
    uv run python reversing/cadaver/py/secrets/text_atlas.py [snap]"""
import struct, sys, re
sys.path.insert(0, 'tools'); sys.path.insert(0, 'reversing/cadaver/py')
from gfxview import load_ram, snapshot_regs
from name_strings import decode_index
snap = sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/cadaver/gameplay_empire.snap'
ram, base = load_ram(snap); a5 = snapshot_regs(snap)[0]['a5']
u32 = lambda a: struct.unpack_from('>I', ram, a)[0]
t168, t172 = u32(a5 + 168), u32(a5 + 172)
print('== packed table, index: primary message')
for i in range(390):
    s = decode_index(ram, 0, t168, t172, i).split(b'\0')[0].decode('latin1').replace('\r', ' / ')
    print('%3d %s' % (i, s))
print('\n== plain ASCII UI strings (English/French pairs: load/save/restore prompts) $006280-$0067a0')
for m in re.finditer(rb'[A-Z0-9 .,]{8,}', ram[0x6280:0x67b0]):
    print('$%06x %s' % (0x6280 + m.start(), m.group().decode()))
print('\n== assert strings $0172c8-$017951')
for m in re.finditer(rb'[ -~]{6,}', ram[0x172c8:0x17952]):
    print('$%06x %s' % (0x172c8 + m.start(), m.group().decode()))
print('\nother: $0117d0', ram[0x117d0:ram.index(b'\0', 0x117d0)].decode())
