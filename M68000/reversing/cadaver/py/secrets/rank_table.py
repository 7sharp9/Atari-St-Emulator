"""rank_table.py: the stats scroll ($00a29c, shown when a class-7 object is used) prints HEALTH n OF max, GOLD, XP, LEVEL, COMPLETE
(rooms entered * 25600 / (2510 - header word 5 of the overlay) >> 8, "OF 100") and a rank title picked at $00a38a-$00a3a0 from the
table at (A5)+176 ($078756): 20 records of 6 bytes [word string index][long XP threshold], title = first record whose threshold is
above the XP (PEASANT below 1000 ... GOD below 60000).  The table has no terminator: the bytes after it are the ASCII stamp
"881990" (+NUL), so XP >= 60000 reads record 20 = index $3838 = 14392 (decodes to "DOOR") and the real top title, string 83
"BITMAP BROTHER", is referenced by nothing.  Start gameplay_empire.snap: poke XP (1188+4 = 1192(A5)), patch `lea <class-7 template>,A2 /
jsr $00a29c` over the instruction at the PC, `bpc $00a3a0` = the `bsr $fd2c` that decodes the title, read D0.
    uv run python reversing/cadaver/py/secrets/rank_table.py"""
import re, struct, sys
sys.path.insert(0, 'tools'); sys.path.insert(0, 'reversing/cadaver/py'); sys.path.insert(0, __file__.rsplit('/', 1)[0])
from gfxview import load_ram, snapshot_regs
from room_object_census import resource_type, resolve
from name_strings import decode_index
from repl import *
ram, base = load_ram(SNAP); a5 = snapshot_regs(SNAP)[0]['a5']
t6 = resource_type(ram, base, a5, 6)
tmpl = next(resolve(ram, base, t6[0], t6[1], o) for o in range(1000) if (t := resolve(ram, base, t6[0], t6[1], o)) and ram[t + 22] == 7)
u32 = lambda a: struct.unpack_from('>I', ram, a)[0]
t168, t172, rk = u32(a5 + 168), u32(a5 + 172), u32(a5 + 176)
recs = [(struct.unpack_from('>H', ram, rk + 6 * i)[0], u32(rk + 6 * i + 2)) for i in range(20)]
def expect(xp):
    for idx, thr in recs:
        if xp < thr: return idx
    return 0x3838
def title_index(xp):
    r = Repl(); pc = r.pc()
    r.cmd(f'w {A5 + 1192:x} {xp:08x}')
    code = bytes.fromhex('45f9') + tmpl.to_bytes(4, 'big') + bytes.fromhex('4eb90000a29c4e71') + b'\0\0'
    for i in range(0, len(code), 4): r.cmd(f'w {pc + i:x} {code[i:i + 4].hex()}')
    out = r.cmd('bp a3a0 3000000')
    r.close()
    for l in out:
        m = re.search(r'D0[=: ]+\$?([0-9a-f]{8})', l)
        if m: return int(m.group(1), 16)
ok = 0; n = 0
for xp in (0, 999, 1000, 1999, 2000, 12345, 49999, 50000, 59999, 60000, 65000, 1000000):
    got = title_index(xp); e = expect(xp); n += 1; ok += got == e
    name = decode_index(ram, 0, t168, t172, got).split(b'\0')[0].decode('latin1') if got is not None else None
    print(f'xp {xp:8d}: title index {got} ({name}) expected {e} {"ok" if got == e else "MISMATCH"}')
print(f'{ok}/{n} match')
