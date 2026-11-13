# Items dropped into cells

Scripts behind the `$c194` item branch (`mapgen.md` "Sealed keys": a dropped FLAMBOS or BATTERY on a flame cell).
Run from `M68000/` with `uv run python -I reversing/captive/py/items/<script>`; outputs go to
`scratchpad/captive/items/`. The hand slot `404(A6)` is `[$80][type][b2][b3]`; the game prints b2 as weight and b3
as "N SHOTS".

| Script | What it does | Expected output |
|---|---|---|
| `itemdrop.py [snap]` | 12 arms from one snapshot, `scratchpad/captive/agents/curios/base30.snap` (every feature). Labelled pokes per arm: party x, y, facing (`26/28/30(A6)`) and the hand slot `404(A6)` = `$80 <type> $07 $11` (17 shots). One click per arm (`drop` pointer y 138 = cell ahead; `foot` y 155 = own cell; `throw` y 105), same budget, with hits on `$db7e $dbb2 $dbee $def0 $f3b4 $f7b0 $c0d6 $c0de $c0e6 $c194 $c1b0 $c1c6 $c1cc $c1e2 $c21e $dbd0`, write watches on the target and party cells, the object-list record, and (drop arms) a second click with an empty hand to pick the record up. Control items EXPLOSIVES `$1b` and ACID `$59` on `$26`; control cell `$20`; ACID on tile `$1e` | Drop on `$26` (50,15): FLAMBOS and BATTERY `$c1b0` 1, record byte 3 `$11` -> `$3c`, picked up as `$005a073c` / `$001a073c`, render "17 SHOTS" -> "60 SHOTS"; EXPLOSIVES and ACID `$c1b0` 0, byte stays `$11`; FLAMBOS and BATTERY on `$20` (49,14) `$c1b0` 0, `$11`. Tile `$26` -> `$27`, `$20` -> `$21`, `$1e` -> `$1f` (one write, pc `$c21e`) in every drop arm. ACID on `$1e` (14,10): `$c1c6` 1, byte 3 `$32`, picked up `$00590732`; FLAMBOS on `$1e` `$c1c6` 0, `$11`. `foot` and `throw` arms reach `$c194` (1) but land on the party cell (`$a1`), `$c1b0` 0 |

Writes `<arm>_before.png`, `<arm>_after.png` and (drop arms) `<arm>_picked.png`. Arms: `drop_{flambos,battery,explosives,acid}_26`,
`drop_{flambos,battery}_20`, `drop_{acid,flambos}_1e`, `foot_flambos_20`, `foot_flambos_26ahead`,
`throw_flambos_{26,20}`. `drop_flambos_26_{before,after,picked}.png` show the hand panel at 17 SHOTS, the item lying in
the flames, and 60 SHOTS after the pick-up.
