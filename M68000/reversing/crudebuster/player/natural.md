# Natural plays of levels 1 to 5

`lua/natbot.lua` plays a level from its start with the real inputs and writes only two things into RAM: the health cell (`CB_GOD=1`, `$80113 = $38` and the blink timer `$80136`) and, with `CB_TIMER=1`,
the level timer (`$80042` is set back to `$300` when it drops below `$100`; at 0 the player dies even in god mode: a stalled run ends at frame 19,814 to 19,845, `PLAYER 1 OUT` in `events.txt`).
The level byte is replaced at game start exactly like `lua/startlevel.lua`. Everything else is a button press. Levels 1 to 5 therefore have natural frames, natural spawns and natural boss deaths where the bot gets through; the earlier
bots (`lua/bot.lua`, `enemies1/lua/enemylog.lua`, `world/lua/census.lua`) walked, jabbed and stalled at the first lock, and `enemylog.lua` pokes a hit flag into enemies it cannot reach (`CB_ASSIST`).

## What the bot knows (and where each rule came from)

| rule | evidence |
|---|---|
| **Reach from the game's own boxes.** It jabs only when the first jab box (R 40, L 0, B -8, T -32, mirrored by the facing) overlaps the target's body box `$6b000[type][state]` + (x, y); otherwise it closes in. | the same hit test as `py/hitbox_gate.py` (397 tests, 71 hits, 0 disagreements); `infographic/py/overlay.py` predicts the hit flag in 4 of 4 captured frames |
| **Lock walls break under jabs.** Pool B types 24, 28, 29, 30 are solid, but standing against one and pressing b1 every 6 frames removes it: level 1 type 28 (the rubble wall at x 480) took three hits (its +5 counter 0, 1, 2, then the record is gone about 150 frames after the first jab). `world.md` section 4 and the open item (d) of `player.md` section 8 said punches only spark; they were measured on a short run. | `scratchpad` lab `lab3.lua` (CB_PLAN `right b1`, CB_PULSE 6), repeated in the natural runs: level 1 at frames 943 and 3448, level 3 at frame 3977, level 4 at 959 |
| **A wall tile stops a walking player.** Level 2 at x 2291 (`$8f3`, the end of the area) and level 4 on the lower floor at x 1779 (`$6f3`) halt the player 12 px short of a tile column (`$e800` at x `$900` and the page boundary `$700`; the terrain probe `$ebb0` looks 12 px ahead). The bot has a `hop` mode (b2 while holding right: peak 48 px, 1.75 px/frame for 32 frames) for it; **a jump over these tiles was not shown to work** (the final runs never got past them), so this row is read, not proven. | terrain attributes read with the `$60000` map (`$ebb0`: `((x>>8) + ((y & $ff00) >> 4)) * 4` into the level's page table, then word `((x & $f0) >> 4) + (y & $f0)`); stalls at x 2291 and 1779 in `nz_l2`, `nz_l4` |
| **Ladders and ledges accept a vertical press only at a few pixels of x.** The level 4 descent is a ladder column at x 1502 to 1506 (tile attributes `$0558 $0568 $0570 $0580`, y `$1e0` to `$260`): a plain down press at x 1502..1506 starts sub-action 7 and drops the player to y 544 and on to the lower floor (y 592 and 592+); 1501 gives sub-action 6 (a fall), 1497 to 1500 and 1507 to 1510 nothing. Pressing down with a horizontal direction (action 3 or 5) never enters it. The bot sweeps x in 2 px steps, 6 frames of the vertical press at each. | `lab4.lua` sweep on a saved level 4 state; natural finds: level 4 x 1502 (frame 8706), level 5 x 990 up (frame 9895) |
| **A prop is not needed for the first lock.** The garbage-can throw of `player.md` section 3 still works but is only the fallback. | as above |
| **Sub-action 7 is two different things.** In action 2 or 6 (left, right) it is the turn-around kick; in action 0 or 4 (up, down) it is the ladder climb. A check for "on a ladder" must test the action too. | the bot's first climb detector fired on every turn-around kick |
| **Targets are records that can act.** Pool A records in state 0 (not yet initialised) and records whose health did not change through 360 frames of fighting them are skipped (an unreachable or invulnerable partner, type 65 with health 127). | `ignoring type ...` lines of `events.txt` |

## Results

Run directories are under `scratchpad/crudebuster/` (`ANCHORS.md`). "Earlier version" means a state of `natbot.lua` between the edits below that was not kept (the file was edited in place, one behaviour per run, without commits;
the final version is the one in the tree, and it is **not monotonic**: some behaviours that helped a level at one point cost another level later).

| level | final version | best earlier version | what stops it |
|---|---|---|---|
| 0 | scroll `$502` (the armoured cyborg arena) by frame 4000, the rubble wall jabbed away at scroll `$2f4` (`ne_l0`, 6000 frames) | the assisted bot cleared it at frame 14882 (`enemies1.md`) | not run further |
| 1 | **cleared at frame 14262**, twice (`ng_l1` with the enemy log, `nh_l1` without: the same frame). 33 of 33 list A entries spawned in script order (`enemies1/py/census.py 1`; the assisted run saw 25 of 33). `$80040`: 80, 84 at 5072 (roller arena), 80 at 5998 (roller dead), 84 at 11773 (leader arena), 88 at 14006 (leader dead), 98 at 14262 (+256 frames, as in `enemies1.md` 6.2) | 12,799 in an earlier version | none |
| 2 | scroll `$802` | `$864`, the helicopter destroyed (a replay from a stall state shows the explosion at frame 14520 and the GO arrow afterwards) | the player halts at x 2291, 12 px before a `$e800` tile column at x `$900`; a jump over it is untested |
| 3 | scroll `$5d4` | past the boss at `$600` (type 12) to `$801` | final version: loops in the ladder search at x 500 to 535 for 5000 frames, later on a ledge. Earlier: the boss stands off screen beyond the lock edge and attacks at 59 px, out of jab reach; the bot backs away (`bait`) so that it walks in; at `$801` the bot ends on a ledge above the fight |
| 4 | the ladder at x 1502 found by the sweep at frame 13879, scroll `$664` on the lower floor, 75,850 points at 27,100 | same | halts at x 1779 in front of a wall tile; an enemy (type 53) waits on a lower level |
| 5 | scroll `$1c0` (a fight loop at x 641) | ladder up at x 990 found at frame 9895, the staircase to the final block (scroll `$e21`, 88,700 points at frame 45,000) | final version: stuck in the first fight; the final boss was never met |

Frame numbers are `L.frame()` of the run (machine time from boot; the level starts about frame 900 after the entrance).
## Reproduce

```
cd M68000/reversing/crudebuster
R=$(cd ../.. && pwd); N=1                                   # level 1..5
mkdir -p $R/scratchpad/crudebuster/nat$N
CB_TIMER=1 CB_ENEMYLOG=1 CB_DIR=$PWD/lua CB_RUN=$R/scratchpad/crudebuster/run_nat$N CB_OUT=$R/scratchpad/crudebuster/nat$N \
CB_LEVEL=$N CB_STOP=45000 CB_LOG=20 sh cbmame.sh run $PWD/player/lua/natbot.lua 1500
# outputs: nat.csv (every CB_LOG frames: position, action, hold, score, scroll, mode), events.txt (mode changes, LADDER, GRAB, STUCK dumps, LEVEL CLEARED, PLAYER 1 OUT),
# enemylog.txt (CB_ENEMYLOG=1: the format of enemies1/lua/enemylog.lua, input of enemies1/py/census.py), state nb_clear in the run dir at the level-cleared flag
```
The script path must be absolute (`cbmame.sh` changes into the run directory). `CB_SAVEAT="frame:name"`, `CB_SHOTS lo:hi:step`, `CB_CAPTURE=N` (RAM plus screenshot of a fight frame, input of `infographic/py/overlay.py`) and `CB_SAVESTALL=N`
(state and screenshot at the first N stalls) are the other options; the header of `natbot.lua` lists them all. In zsh write `"${f}:name"`, not `$f:name` (the `:name` is a history modifier).
