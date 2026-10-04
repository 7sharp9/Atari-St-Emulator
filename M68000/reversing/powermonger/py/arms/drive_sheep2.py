"""drive_sheep2.py <snap> <cx> <cy> <out.cmds> <chunks> <chunk_steps> <A3hex> <leadhex>   (PowerMonger 148th, agent A)
Like drive_sheep.py (sword icon, minimap click on cell (cx, cy)), then <chunks> windows of `hits` over the mode chain with the
group's state / objective class (204) / target (24) / the lead's modes + cell printed after each (A3 = $51538 + the selected group
offset; lead = its record, both read from the start snapshot)."""
import sys
snap, cx, cy, out, chunks, cs, A3, lead = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], int(sys.argv[5]), int(sys.argv[6]), int(sys.argv[7], 16), int(sys.argv[8], 16)
HOME = ["mouse move -400 -400", "s 300000", "mouse move 0 0", "s 300000"]
def move(dx, dy): return [f"mouse move {dx} {dy}", "s 300000", "mouse move 0 0", "s 300000"]
A = "6b38 6c32 4a7a 4b80 4bc8 4dae 1518a 4d40 4d9a 4f68 152f8 50da 5100 153cc 1547e 15518 15302 5778 56a6 4cb8 37c2"
c = ["disk scratchpad/powermonger.st"] + HOME + move(243, 190)
c += ["mouse down l", "mouse move 0 0", "s 300000", "mouse up l", "mouse move 0 0", "s 300000", "m 57fd4 2"]
c += move(cx - 243, cy + 6 - 190)
c += ["mouse down l", "mouse move 0 0", "s 300000", "mouse up l", "mouse move 0 0"]
def dump(tag):
    return [f"m {A3:x} 2", f"m {A3+24:x} 2", f"m {A3+204:x} 2", f"m {A3+216:x} 2", f"m {lead+8:x} 4", f"m {lead+30:x} 2"]
for i in range(chunks):
    c += [f"hits {cs} {A}"] + dump(f"chunk{i}") + ["snap " + out.replace('.cmds', f'_c{i}.snap')]
c += ["snap " + out.replace('.cmds', '_end.snap'), "q"]
open(out, 'w').write('\n'.join(c) + '\n')
