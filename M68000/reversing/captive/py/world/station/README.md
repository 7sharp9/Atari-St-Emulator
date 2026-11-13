# Captive `py/world/station/`: landing on the space station (the final base)

Scripts behind `../../../world.md` section 1 ("Final target") and the final base's first minutes. Run from `M68000/`.
Each finds the repo root by walking up to `tools/rdis.py` (or `M68000_ROOT`) and writes under
`scratchpad/captive/station/`. Start snapshot: `scratchpad/captive/mission1.snap` (the map screen, no sidecar: the
scripts pass `scratchpad/captive/tmb097.st` as the disk), except the `natural` control arms, which start from
`scratchpad/captive/base1/site.snap`. All use `tools/stclient.py` (stserver; `server/bin/Debug/net8.0/stserver.dll`).

Common pointer drive: three `mouse move -127 -127` pin the pointer at the top left, then 1:1. Station dot at zoom 8
(slot 0, `13566(A6)` entry `e600 e600`): pixel (78,85); ORBIT icon (204,76); LAND icon (252,75).

**Traps:**
- One `mouse move` is clamped to +-127 per axis. A move to x = 204 in one call lands at 127 and the ORBIT click
  registers nothing (0 hits on `$2f5a0`, ship state stays 0). The scripts' `goto()` splits the move.
- stserver watches survive `restore`: a later arm's `watch_events` lists earlier arms' watches too. `station.py` removes
  its watch per arm (`watch_remove`); read events by watch id.

| script | what it proves | command | expected output |
|---|---|---|---|
| `station.py` | Landing on slot 0 writes request 4 only when the exit count `14794(A6)` is above 9. Three arms from `mission1.snap`, same clicks and 25M-step budget (select, ORBIT, wait `14858` = 6, LAND), differing only in the **labelled poke** `ww 14794(A6)` = 0, 9, 10 made after the selection click | `uv run python -I reversing/captive/py/world/station/station.py` (about 1 min; also writes `station.log`, `arm{0,9,10}_after.png`) | selection `14782` = `14856` = 0, cursor (6656,6656), ship 6 in all arms. Hits (`$2f5f4`, `$2f66e`, `$2f676`, `$2f4f0`, `$885e`, `$b5c2`): 0 and 9: 1, 1, 0, 1, 0, 0, no write to `14788`, mode stays 1 (map screen "DOCKING COMPLETE"); 10: 1, 1, 1, 0, 1, 1, writes 4 from `$2f676` then 0 from `$885e`, `32(A6)` = 10, mode 3; stop at `$b5c2`: D0 = 10, D1 = 0, D2 = 1 |
| `death.py` | Why the final base ends in "DROID'S HAVE FAILED": arm 10 replayed, state logged in 1M-step chunks with `hits` on the hit/death path and write watches on `14800`, `410`, `13410`. Same labelled poke `14794(A6)` = 10. `natural` = control (target 1 of `base1/site.snap`) | `uv run python -I reversing/captive/py/world/station/death.py > scratchpad/captive/station/death_fin.log 2>&1` (about 1 min; `natural` for the control; `trace` as the argument for first-reach stops and the group list, about 100 s) | party (53,0) facing 2 in mode 3 (no compound, `13410` = 0); `$f884` 1, 5, 14 and `$9a9a` 5, 11 and `$e6dc` 1, 3 in the 8-9M and 9-10M chunks after the generator; `$876a` once, `14800` = 1 written at `$876a` (absolute step 346,762,314), `$134b8` once. `trace`: group `$1d33a` (54,0), type `$1d`, +5 = `$19`, attacks through `$10e4a` (A0 = `$1d342`) -> `$f4b0` -> `$f584`/`$f80a` -> `$f884` -> `$9a9a` -> `$e6dc`. `natural`: none of those 5 addresses hit in 40M steps, `410` = 4 |
| `fdc.py` | The final base's "LOADING ..." view is the game's own load phase, not a stuck loader: the game OS's trap #9 calls (`$206`/`$16c`), the FDC trace, PC samples and renders from the LAND click, final arm and `natural` control | `ATARI_TRACE_FDC=1 TOTAL=60000000 uv run python -I reversing/captive/py/world/station/fdc.py > scratchpad/captive/station/fdc_fin.log 2>&1` (add `natural` for the control; `RENDER=3,6,13` picks render steps in millions) | final: 310 `FDC read` lines after the click, 0 not `OK`, no repeated failing command; module loads (`fn 28`) `$1f7b0`, `$2f3d0`, `$275c0`, `$3eff0`, `$1f7b0` x2, load ends (`fn 32`) +12.10M after the click; base corridor view at 13M and 14M; `410` 3 at +14.6M, 1 at +15.1M, 0 at +15.35M with `14800` = 1. Natural: 280 reads, 0 not `OK`, `fn 32` at +10.27M, base view, no deaths through 60M |

The death is real (the loader completes and the view appears before the group at the entrance kills the droids); a
party moved away from (53,0), and why the generator puts that group beside the final base's entrance, are not tested.
