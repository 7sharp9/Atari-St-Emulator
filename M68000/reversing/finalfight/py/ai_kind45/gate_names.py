"""gate_names.py <trace.bin.gz> <frame> <expected name>: the HUD enemy name is drawn as tile words $4400+ASCII, one per 128 bytes (the scroll-1 map is column-major: consecutive characters of a
row are $80 apart, each a code word then an attribute word), into the gfx RAM name row; search the dump drv.lua wrote (<trace>.gfx<frame>, gfx RAM $900000-$90ffff) for the
expected text. Prints OK/FAIL and the gfx offset. Names and their sources: $5b640/$5b6fc (ai.md)."""
import sys, os
trace, frame, name = sys.argv[1], int(sys.argv[2]), ' '.join(sys.argv[3:])
base = trace[:-3] if trace.endswith('.gz') else trace
d = open('%s.gfx%d' % (base, frame), 'rb').read()
want = [0x4400 | ord(c) for c in name]
w = lambda o: (d[o] << 8) | d[o + 1]
hit = [o for o in range(0, len(d) - 0x80 * len(want), 2) if all(w(o + 0x80 * i) == want[i] for i in range(len(want)))]
print('%s %-10s at frame +%d: %s' % ('OK  ' if hit else 'FAIL', name, frame, ('gfx $%x' % (0x900000 + hit[0])) if hit else 'name tiles not found'))
sys.exit(0 if hit else 1)
