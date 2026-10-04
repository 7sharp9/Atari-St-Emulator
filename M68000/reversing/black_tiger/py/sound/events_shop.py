"""Shop purchases ($fa9c shop_buy_item) and the sound they request.  `callcap fa9c` for each of the
10 shop items with money 20000 (every purchase affordable) and with money 0 (refused), from
play_start.snap.  LABELLED POKES: $1eeda := $7fff7fff (lets the wait loop at $fc1c exit, as in
mechanics' gate_shop), money/keys $1f002, armour/potions $1f006, weapon $1f00a (word), poison
$17820, the stack argument at $1ee50.  The callcap memory delta shows $184ef (low byte of the
current-sound word $184ee) going 0 -> 7 when a purchase succeeds ($105d8 called with id 7).
Expected: 10/10 affordable purchases set 7, 0/10 refused ones do (the refusal path waits in a
text loop and does not return, `returned=False`).
"""
import os
import re

from btsnd_common import BT_WORK, OUT, Snap
from verify_psg import run_repl

sp = os.path.join(BT_WORK, "play_start.snap")
s = Snap(sp)
low = s.ram[0x1ee52:0x1ee54].hex()
lines = ["w 1eeda 7fff7fff"]
cases = []
for money in (20000, 0):
    for i in range(10):
        lines += ["w 1f002 %04x0000" % money, "w 1f006 00000000", "w 1f00a 0000%s" % s.ram[0x1f00c:0x1f00e].hex(),
                  "w 17820 0000%s" % s.ram[0x17822:0x17824].hex(), "w 1ee50 %04x%s" % (i, low), "callcap fa9c 4000000"]
        cases.append((money, i))
out, err = run_repl(sp, "\n".join(lines) + "\nq\n", "shop_sound")
blocks = re.split(r"(?=^--- callcap)", out, flags=re.M)[1:]
assert len(blocks) == len(cases)
got = {20000: 0, 0: 0}
for (money, i), b in zip(cases, blocks):
    m = re.findall(r"^mem \$0184ef \$00->\$07", b, re.M)
    got[money] += bool(m)
    print("money %5d item %d returned=%s sound-7-set=%s" % (money, i, "returned" in b.splitlines()[0], bool(m)))
print("affordable purchases that requested id 7: %d/10; refused: %d/10" % (got[20000], got[0]))
