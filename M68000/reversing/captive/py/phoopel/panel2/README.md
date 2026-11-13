# Lock panel: draw slots, `$c420`, gold

Scripts behind the panel-draw, door-toggle and gold findings (`mapgen.md` "The panel in play", "Coded doors"). Run from `M68000/`
as `uv run python -I reversing/captive/py/phoopel/panel2/<script> ...`. Start snapshot `scratchpad/captive/phoopel/base13.snap`;
outputs go to `scratchpad/captive/phoopel/panel2/`. `common.py` holds the shared setup (repo root, stserver, lock list).

| script | what it proves | command | expected | labelled pokes |
|---|---|---|---|---|
| `list.py` | lock list with W's side, key/door kind, code and the tiles ahead of W | `list.py` | 24 locks | none |
| `scan.py <lock>` | D0 at `cmp.w #5,D0` (`$12a7e` kind 3, `$12a92` kind 2) is the front-wall slot of the panel: 6 = cell in front, 5/4/3 depth 2 left/centre/right, 2/1/0 depth 3; no `$12a20` call at depth 4+ | `scan.py 16`, `12`, `19` | `bhi` taken on 3/3 depth-1 cells, not on 14/14 farther; `NOCOVER=1` gives 0 calls of `$12a20` | party x, y, facing; W's tile bit 2 (cover) |
| `scene.py <lock> d,lat ...` | the pieces `$b230` draws per slot (far: plate `$1d6+D0` / `$1d0+D0` and `$1dd+D0`; near: plus label and segments, or 8 buttons) and renders; `STATE=hex` shows only the near side follows the switch state | `scene.py 16 1,0 2,0 3,0`; `STATE=ffff scene.py 16 1,0 2,0 3,0`; `scene.py 12 ...`; `STATE=ff scene.py 12 1,0 2,0` | state poke: 112 differing view pixels at depth 1, 0 at depth 2 and 3 (lock 16); 311 and 0 (lock 12) | party; cover bit; optional state word +4 |
| `figs.py` | builds `fig_kind3_depths.png` and `fig_kind2_depths.png` from the scene renders | `figs.py` after the two `scene.py` runs | two PNGs | none |
| `door.py <lock>` | `$c420` under a real lock click: slot claim, 4-frame counter, free; control 0 entries; reclose 2 entries | `door.py 17`, `door.py 9` | open: path `c420 c424 c468 c470 c476 c478 c490`, `$46` to `$56`, slot counter 0..3 then freed; control 0 entries | party x, y, facing; mouse clicks |
| `items.py <snap> [type]` | object-list parser (`$1bf3a`: x, y, word size, items type/word/flags) | `items.py scratchpad/captive/phoopel/base13.snap 19` | prize-cell GOLD words in [`$80`,`$47f`] (34), wall GOLD in [`$40`,`$13f`] (21) | none |
| `gold.py <x,y>` | live pickup of a lock-prize GOLD item into the hand `404(A6)` | `gold.py 21,3` | hand word 537 = listed word; the view reads "537 PIECES" | party x, y, facing |
| `gold_stack.py x,y ...` | GOLD word is the amount and `$e7d0` sums stacks (cap `$ffdc`) | `gold_stack.py 21,3 42,14 4,14` | hands/pockets 537, 1634, 2647; cap test hand 65500, pocket 88 | party; routine call of `$e7d0` on a scratch slot `$7f000`; cap test pokes hand and slot |
