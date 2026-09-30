"""After a race ends the game picks the next track from -8542(A4) and runs $be40 again without the wheel.
Run from race_T.snap until $be40 is hit a second time and read its track argument (4(A7) at entry) and -1748(A4)."""
import sys; sys.path.insert(0,'.')
from tkcommon import *
T = int(sys.argv[1])
r = Repl2(out('snaps', 'race_%d.snap' % T))
o, reg = r.cmd2('bpc be40 1 26000000')             # race runs ~22M steps; then WINNER'S CIRCLE waits for fire
for k in range(40):
    if reg['PC'] == 0xbe40: break
    r.cmd('kbd fe 80'); r.cmd('s 100000'); r.cmd('kbd fe 00')
    o, reg = r.cmd2('bpc be40 1 3000000')
sp = reg['A7']; trk = int.from_bytes(r.mem(sp + 4, 2), 'big')
race = int.from_bytes(r.mem(A4 - 1748, 2), 'big')
print('track %d -> next $be40 entry: PC=%x track arg=%d race counter -1748(A4)=%d  (table -8542(A4)[%d] = %d)' % (
    T, reg['PC'], trk, race, T, int.from_bytes(r.mem(A4 - 8542 + 2 * T, 2), 'big')))
r.close()
