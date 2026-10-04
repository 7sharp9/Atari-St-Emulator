"""Print the resource table ($e0c4 name/dest/length, $e084 unpacked sizes, $e040 cache slots) from the m1_win RAM image."""
import struct, sys, os
R = os.environ.get("M68000_ROOT") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ram = open(os.path.join(R, "scratchpad/pm123/win/m1_win.ram"), "rb").read()
L = lambda a: struct.unpack(">I", ram[a:a+4])[0]
W = lambda a: struct.unpack(">H", ram[a:a+2])[0]
def cstr(a):
    e = ram.index(b"\0", a); return ram[a:e].decode("latin1")
print("e03e cache flag", W(0xe03e), " 2c1ba cache ptr", hex(L(0x2c1ba)))
for i in range(16):
    nm = L(0xe0c4+12*i)
    print(i, "name@%x %r" % (nm, cstr(nm)), "dest %x" % L(0xe0c4+12*i+4), "filelen(+8) %x" % L(0xe0c4+12*i+8),
          "unpacked(e084) %x" % L(0xe084+4*i), "cache(e040) %x" % L(0xe040+4*i))
for a in (0xe290,0xe296,0x1bafc,0xe38a):
    print(hex(a), repr(ram[a:a+24]))
