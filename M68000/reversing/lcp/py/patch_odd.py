"""Make the run disk: give \\LCP\\LCP.PRG an even DATA size so TOS 1.00 Pexec does not take an address error
(README, "Provenance"). usage: patch_odd.py <tmbird03.st> <tmbird03_even.st>"""
import sys, struct
src, dst = sys.argv[1], sys.argv[2]
d = bytearray(open(src,'rb').read())
hdr = bytes.fromhex('601a000003280000cc71')
i = d.find(hdr); assert i >= 0 and d.find(hdr, i+1) < 0, i
print('header at', hex(i))
d[i+6:i+10] = struct.pack('>I', 0xcc72)
end = i + 53177
print('slack byte', d[end:end+4].hex())
d[end] = 0
# directory entry: name LCP     PRG, size field at +28
ent = d.find(b'LCP     PRG')
while ent >= 0:
    size = struct.unpack('<I', d[ent+28:ent+32])[0]
    print('dirent', hex(ent), size)
    if size == 53177:
        d[ent+28:ent+32] = struct.pack('<I', 53178)
    ent = d.find(b'LCP     PRG', ent+1)
open(dst,'wb').write(d)
