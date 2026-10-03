"""scan_snaps.py: scan every Cadaver .snap under scratchpad/cadaver for live objects with a mover block / anim block (statically, from the saved RAM).
Output lines: path | level | room | id:mover-state[,cursor] for movers, id:anim-state for anims.  usage: scan_snaps.py OUT.tsv"""
import os, sys, glob
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..', '..')))
A5 = 0x18152
out = open(sys.argv[1], 'w')
for p in sorted(glob.glob(ROOT + '/scratchpad/cadaver/**/*.snap', recursive=True)):
    try:
        s = open(p, 'rb').read()
    except Exception: continue
    off = 5 + 19 * 4 + 2
    ram = s[off + 4:off + 4 + 0x100000]
    if len(ram) < 0x100000: continue
    u32 = lambda a: int.from_bytes(ram[a:a + 4], 'big'); u16 = lambda a: int.from_bytes(ram[a:a + 2], 'big')
    try:
        base = u32(A5 + 56); n = u16(A5 + 1152)
        if not (0x10000 < base < 0xf0000) or n > 200: continue
        lvl = ram[A5 + 2524]; room = u16(A5 + 1166)
        movers = []; anims = []; others = []
        for i in range(n):
            e = base + 70 * i
            if u16(e) >= 0x8000: continue
            ra = u32(e + 10); ta = u32(e + 6)
            if not (0x10000 < ra < 0xff000) or not (0x10000 < ta < 0xff000): continue
            rec = ram[ra:ra + 16]; tm = ram[ta:ta + 32]
            oid = int.from_bytes(rec[4:6], 'big')
            if rec[15] & 0x80: continue
            if tm[12] & 1 and rec[3] & 0x10 and rec[13] != rec[14]:
                m = ra + rec[13]; movers.append('%d:s%d,c%d,m%02x' % (oid, ram[m], ram[m + 1], rec[3]))
            if tm[12] & 4:
                an = ra + rec[14]; anims.append('%d:%02x/%02x/f%02x' % (oid, ram[an], ram[an + 3], rec[15]))
        out.write('%s\tL%d\tR%d\tM[%s]\tA[%s]\n' % (os.path.relpath(p, ROOT), lvl, room, ' '.join(movers), ' '.join(anims)))
    except Exception as ex:
        continue
out.close()
