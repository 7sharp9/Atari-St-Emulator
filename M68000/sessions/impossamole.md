# Impossamole: handoff

Updated 2026-09-28 by the session that ended at the 98th-pass commit (see `git log`).

## Resume point

- Last commit of this workstream: the 98th pass, "impossamole: 98th pass -- x=192 is the camera
  trigger, the crossbar item is collected" (`git log --oneline -3` for the hash).
- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image,
  `coldboot_census/` (from-cold-boot scripts and snapshots), `gameplay_explore/` (movement/hazard
  trials). See `scratchpad/ANCHORS.md` for the full indexed list. Real Hatari v2.6.1 at
  `~/Downloads/hatari-snapshot/Hatari.app`, source at `~/GitHub/hatari/`. TOS ROM at
  `M68000/TOS100UK.IMG`.
- Start from: `scratchpad/impossamole/gameplay_explore/pass98_item_try.snap` (item just collected,
  score `003200`, hero `x=114,y=144` idle-ish, **`1/18` health: one more hit kills**, camera
  `$227b6=$49e`). `pass90_wall_192.snap` (`2/18`, camera `$46c`) is the older, healthier resume
  point if a run needs to start over; `pass96_doublejump_v2.snap` (`2/18`, camera `$49e`) is where
  `reversing/impossamole/py/twintree_item_route.repl` starts.
  **Every `resume ... repl` needs `--disk-a "scratchpad/impossamole/impossamole cr replicants - emotion
  cr replicants.st"`** (path relative to `M68000/`) and `ATARI_NOTRACE=1`. The REPL stops at the first
  unknown line, so scripts cannot contain `#` comments. `snap <path>` writes relative to the dotnet
  process's working directory; give the full path.
- Uncommitted work left behind: none from this session. The pre-existing `M68000/sessions/README.md`
  whitespace-rewrap diff (predates this workstream, flagged unowned by several prior handoffs) is
  still there and still not this workstream's to fix. `.obsidian/` and `Cadaver/` at the repo root
  are also not this workstream's.

## Proven so far

See `reversing/impossamole/README.md`'s "Program classification", "Gameplay input" and "Past the
first screen" sections for full detail, match counts and exact addresses:

- **The program is hand-written 68000 assembly, not compiled C.** No decompile route — live
  `watch`/`bpc`/`callcap` plus `disassemble.py --all` is the only path.
- **The hazard/collision mechanism is proven end to end** (`$00b71a` proximity → `$00e80e` scan →
  `$00e82e` damage copy → `$00eb8c` apply → `$00ec50` death → `$b058` reload), and the object
  array's stride and base (108 bytes/entry, base `$1a2ea`, hero index 6 at `$1a572`).
- **A real, table-driven jump mechanism exists**: `$00c742` one-shot entry falling through into
  `$00cbbc`, the per-frame handler (a `$cd54` velocity table). Input holds must exceed the game's
  ~24,000-step poll cycle (30,000 works).
- **`x=192` is the camera-follow trigger, not a wall (98th pass; corrects the 90th-97th framing).**
  `$00c450` arms `$227f1` bit 3 when the hero's `x>192`; `$018f7e` then does `addq.w #2,$227b6`
  (the camera, the only writer) up to the level limit `$227b8=$1020`; `$00bb22`-`bb68` shifts every
  `30(A0)=$00ff` object left by the same delta, so the hero stays pinned on screen while the world
  moves. Ground-level walking never scrolls (`watch 227b6`, zero writes over 400,000 steps: the
  forward tile block stops the hero first). An up+right hop from `x=192` scrolls 8px (4 writes,
  `$46c`→`$474`). This resolves the old "is the emulator missing a scroll?" question: it isn't.
- **The twin-tree crossbar item is collected (98th pass, reproduced identically on a second run of
  `py/twintree_item_route.repl`)**: slot 0 (`$1a2ea`, `type=1`, `(138,88)`, radius 16/16) goes
  `type` 1→0 and the HUD score `000000`→`003200` during an up+left hop from the ledge step, hero
  `y<=104` at `|dx|=6`. A straight-up hop from the ground below peaks at `y=106` and misses (needs
  `y<=104`). The route costs one hit (`2/18`→`1/18`, slot 12's drift path on the walk left).
- Slot 12 (`$1a7fa`) is a small flying creature drifting `~-0.126px/step` x (93rd pass); slot 8
  (`$1a64a`) patrols the crossbar rest spot and eventually hits anything resting there (95th pass).
- The `$25000` tile-classification table, the HUD routine (`$00fdc4`), and the weapon/projectile
  system (`$00d37c`/`$00d3cc`, slots 16-19) are unchanged from prior passes — see the README.

## Open, in priority order

1. **Continue right past the item.** Chain up+right hops (`kbd ff`/`kbd 09`, 30,000-step hold, wait
   for `$227f3=0` idle) and `watch 227b6`: each hop scrolls ~8px, so what appears past `x`-world
   `$49e+` is unmapped Amazon content (screenshot with `snap_render.py` at each ~50px of camera).
   `1/18` health: run from `pass90_wall_192.snap` (`2/18`) via the route script if a death costs the
   snapshot. Is there a level-exit or another room behind the twin trees?
2. **Pin what the item is.** `bpc` on the write that sets slot 0's `type` to 0 (find it with
   `watch 1a2ea 2` during the up+left hop) to name the pickup handler, and check whether score was
   the only thing it changed (health did not). Whether `$00b71a` is the generic test or a dedicated
   pickup handler is inferred, not proven.
3. **Characterize slot 8's drift/patrol rate**, the way slot 12's was pinned in the 93rd pass.
4. **Find the projectile-vs-enemy damage path**, or confirm there isn't one in this build. A `callcap`
   on `$00d3cc` from a primed state, then a live `watch` on the projectile slot while stepping past
   a nearby enemy, would settle it.
5. Identify what tile categories `$1`/`$2`/`$3` mean precisely (raw ids only known to map to
   ladder-climbable at the up-check).
6. Whether Orient/Ice Land/Bermuda Triangle load correctly in this emulator, from a fresh cold boot.
7. Classify the twin-tree screen's full hazard cluster (slots 8/9/10/12 known, 8 and 12 confirmed to
   move) — check whether 9/10 also move.

## Known traps

All workstream-specific traps are in `reversing/impossamole/README.md`'s own "Known traps" section —
read it there. The general lesson of this session (a camera-pinned hero makes on-screen position
comparisons blind to progress; read the scroll counter) is folded into `CLAUDE.md`.

## Next session

Start with Open item 1: chain hops right from `pass98_item_try.snap` and watch `$227b6` to see what
the level holds past the twin trees. Then pin the item's pickup handler (item 2). Do not re-run the
old "cross `x=192`" input-timing trials: they are moot now that the scroll mechanism is known.
