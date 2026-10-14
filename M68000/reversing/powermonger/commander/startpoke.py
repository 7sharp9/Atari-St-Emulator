"""startpoke.py <snap> <out snap> <k> [tick|rng]: <snap> with one source of the game's chance shifted by k, nothing else.

tick (default): the per-tick counter `$57fec` (`_season_`, 0..511) += k, wrapping at 512. The commander AI and combat
take their chance from its low bits only (`& 1` health recovery, `& 3` campaign sub-mode, `($57fec + phase) & 2` the
kill/rout roll; strategy.md "the tick-counter trick"), so this re-rolls them. It is a word: the longword `w` poke
rewrites `$57fec..$57fef` with `$57fee` read back unchanged. A negative result too, for the game's own AI: from
`pm142/rand1.snap` with k = 1..5, an unpoked side-3 run matches k = 0 at all 136 decisions for even k; for odd k the
observation differs at 26 of them from 70M but the totals at only one (675M), and the land ends at 678M against
676M (`scratchpad/cmd12/ticktest`).

rng: the LCG seed `$2df84` advanced k draws (seed := seed * $bb40e62d mod 2^32, `$12c9a`). A negative result kept
for the record: from `pm142/rand1.snap` with k = 1 and 2, an unpoked side-3 run (`loop.py --policy none --no-take`)
gives the same observation hash as k = 0 at all 60 decisions to 300M, and both runs hold the seed rand1 + 236
draws at 300M, so something in play puts the seed back on rand1's sequence (`scratchpad/cmd12/rngtest`).

An offset start (seeds.sh's default) does not perturb an unpoked run either: the game's AI then plays one trajectory
shifted in time (README "Policies against the game's AI")."""
import sys
from loop import Emu, ROOT

snap, out, k = sys.argv[1], sys.argv[2], int(sys.argv[3])
mode = sys.argv[4] if len(sys.argv) > 4 else 'tick'
e = Emu(ROOT / snap, str(ROOT / out) + '.err')
if mode == 'rng':
    A = 0x2df84
    s0 = s = int.from_bytes(e.mem(A, 4), 'big')
    for _ in range(k):
        s = (s or 0xbc614e) * 0xbb40e62d & 0xffffffff
else:
    A = 0x57fec
    s0 = int.from_bytes(e.mem(A, 4), 'big')
    s = ((((s0 >> 16) + k) % 512) << 16) | (s0 & 0xffff)
e.send(f'w {A:x} {s:08x}')
assert int.from_bytes(e.mem(A, 4), 'big') == s
e.save(ROOT / out)
e.close()
print(f'{out}: {mode} ${A:x} ${s0:08x} -> ${s:08x}')
