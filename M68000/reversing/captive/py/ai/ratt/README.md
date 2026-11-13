# Captive: Ratt's note and the end-screen values 2 and -2

Scripts behind `reversing/captive/ai.md` "Door hints: the die and Ratt's message" and "Trill and leaving a base". Run from
`M68000/` with `uv run python -I reversing/captive/py/ai/ratt/<script>`. Each finds the repo root through `../cap.py` (walks up
to `tools/rdis.py`, or `M68000_ROOT`) and drives `stserver` through `tools/stclient.py`. A relative snapshot argument is
tried under `scratchpad/captive/` first. Outputs (snapshots with sidecars, renders) go under `scratchpad/captive/ratt/`
(`objs.OUT`). Start snapshots: `base1/land_mg.snap`, `base1/in_mg.snap`, `base1/outside.snap`, `base1/in.snap`
(`py/ai/natural_base.repl`), `phoopel/revisit/exited.snap` (`py/phoopel/revisit.py exit`),
`phoopel/finish_base1_blast_state2.snap` (`py/phoopel/finish13.py`).

Result: the item `$66` word 1 is placed by `$26946` (called only from `$23f64` in the compound builder `$23e80`, base D0 = 0
only) at the compound cell (21,20); the party takes it by clicking the floor. Value -2 follows the up icon on the landing pad
`$2e` after a base exit; value 2 is a final base left without Trill.

Run in this order (later rows read what earlier ones write under `scratchpad/captive/ratt/`):

| script | what it proves | command | expected output |
|---|---|---|---|
| `gen_hits.py` | the writers of item `$66` during a generator call: compound call (D2 = 2) hits `$26946` once via `$23f64`; base call (D2 = 0) hits `$268f8` and `$2695e`, never `$26946`; the watch shows the store at `$266e6` / `$26712` | `gen_hits.py base1/land_mg.snap 900000`; `gen_hits.py base1/in_mg.snap 3700000` | compound: `$23e80` 1, `$23f64` 1 (step 657,033), `$26946` 1, `$26682` 1, `$268f8` 0, `$2695e` 0; item `$66` at `$1bf3e` cell (21,20) bytes `66000180`. Base: `$26946` 0, `$2695e` 1, `$268f8` 1, `$26682` 3; items (19,2) word 2 and (30,1) word 0 |
| `gen_hits.py` (control) | the gate is D0 = 0 (`12408(A6)`, `$23f48`) | `gen_hits.py base1/land_mg.snap 1000000 1`, and `... 11` (hex `$11`) | labelled register pokes of D0: `$23e80` 1, `$23f64` 0, `$26946` 0, `$26682` 0, no `$66` item |
| `walk_to_note.py` | natural keypad walk from the compound start (23,18) to (21,19) facing S, the note cell ahead; writes `ratt/t1.snap` | `walk_to_note.py` (defaults `68,69,68,68,67 t1`) | positions (23,19), (23,19) face W, (22,19), (21,19), face S, ahead tile `$21` |
| `clicks.py` | the pickup: a click on the floor ahead puts the item in the hand and opens the description (`$6f8e`, `$702c`, `$138ae`) | `clicks.py ratt/t1.snap '130,144' w1` (render `w1.png`: "MESSAGE FROM RATT 12kg / TOP-LEFT, BOTTOM-LEFT, TOP-RIGHT, BOTTOM-RIGHT.") | hand `00000000` -> `00660001`, pile 1 -> 0, hits `$138ae` 1, `$702c` 1, `$6f8e` 1 |
| `scan_click.py` | the position control: only the floor spot picks the item up | `scan_click.py ratt/t1.snap 90 170 10 120 165 8` | hand changes at 7 points (x 110..170, y 144); other changes are the pile word only |
| `click_at.py` | one click with before/after hand and pile | `click_at.py ratt/t1.snap 130 144 pick` | hand `00660001` after |
| `clicks.py` (word 0) | word 0 at (30,1) of the base: take the `$1b` item first, drop it on the party's own cell (y >= 150), then take the note | `clicks.py base1/in.snap '90,144;130,156;90,144' w0` | hand `001b0000`, `00000000`, `00660000`; hits `$138ae` 1, `$702c` 1, `$6f8e` 2; text "YOU WILL NEED THIS TO DESTROY THE GENERATORS." |
| `minus2.py` | `14800` = -2 ("BASE HAS BEEN DESTROYED! / PRESS MOUSE TO CONTINUE") by play after a real exit: rebuild, door code TL, BL, TR, BR, 4 steps N, E onto the pad `$2e`, up icon (202,112); writes `ratt/m2_pre.snap`, `m2_screen.snap`, `m2_t01..24.png` | `minus2.py` (start `phoopel/revisit/exited.snap`, whose own state came from labelled pokes) | `$902e` 1, `$9064` 1, `$87a6` 1 (step 12,381,814), `$134b8` 1, `14800` -2, `$13624` 0 while the screen waits |
| `minus2.py control` | the `14880(A6)` flag (set by `$87de` at the exit) is the condition | `minus2.py control` (labelled poke `14880` = 0 before the icon) | `$902e` 1, `$9064` 1, `$87b6` 1, `$87a6` 0, `$134b8` 0, `14778` 1: straight to the ship |
| `keys_from.py` | puts the party on the pad: `ratt/m2_pre.snap` + key `68` | `keys_from.py ratt/m2_pre.snap 68 m2_on_pad` | party (23,18) facing E, tile under `$ae` |
| `scan_icons.py` | which icon runs `$902e` (action 24, up) | `scan_icons.py ratt/m2_on_pad.snap 902e 190 310 12 60 156 12` | HIT at (202,108), (214,108), (202,120), (214,120), count 1 each |
| `end_click.py` | the -2 screen ends on a click and the game returns to the ship map | `end_click.py ratt/m2_screen.snap 1500000 30000000 m2c x` | `$13624` 1, `14800` 0, `14778` 1, `$87b6` 1 within 3M steps after the click; render `m2c_8.png` "DOCKING COMPLETE" |
| `value2.py test` | `14800` = 2 ("TRILL HAS BEEN LEFT TO DIE. / DROID'S ARE TO BE WASTED"): a final base (13412 = 1, labelled poke; party onto the entrance, labelled poke) left at state 2 without the Trill event | `value2.py test` (start `phoopel/finish_base1_blast_state2.snap`) | `$87c0` 1, `$87d0` 1 (step 366,682), `$87d6` 1, `$882e` 1, `$134b8` 1 (474,788), `$8804` 0, `$8836` 0; a click at +10M gives `$13624` 1, `$5608` 1, `$8570` 1 (13.13M) |
| `value2.py control` | without the final-base flag the base is left normally | `value2.py control` | `$87d0` 0, `$882e` 0, `$134b8` 0, `$8836` 1, mode 1, 13412 = 2 after the rebuild |

`objs.py` is the shared helper (object-list reader `objlist`, `OUT`).
