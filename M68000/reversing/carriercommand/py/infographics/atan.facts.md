# atan.svg: facts and sources

Figure: `gen_atan.py` writes `scratchpad/carrier/infographics/atan.svg` (PNG: `rsvg-convert -z 2 atan.svg -o atan.png`).
Every curve is computed from the port `py/units/atan_port.py`, which matched `callcap $aae6` on all 529 cases of
`py/units/atan_grid.py`; the table is read from `c_s30.snap` by the port. Doc: `vehicles.md` section 2.

| fact in the figure | source |
|---|---|
| `$aae6` is atan2(dx, dz), 0 along +z, 65536 to the turn; inputs halved until both fit a word (`$aae2`) | vehicles.md 2 |
| fold to one octant, r = min/max in Q15 by `divs`, `(r << 8) / T[r >> 8]` by `divu`, then `<< 4` | vehicles.md 2; port `_h` |
| unfold by `$4000 - a`, `$8000 - a` and negation | port `_g`, `_f`, `atan2` |
| about twenty callers, autopilot and missile guidance | vehicles.md 2 |
| 128 factors at `$3864`, 12823 .. 16356 | read by the port from the snapshot; printed by `gen_atan.py` |
| curve `4096 pi r / atan(r)` at each entry's midpoint; stored values within -18.6 / +5.1 of it (entries 1..127) | computed here; the doc's -45/+28 is against its own fit |
| worst error 27.0 units (0.148 degrees) at radius 30000, the same in all eight octants | computed from the port over 65536 angles |
| table alone (before the shift) at most 13.7 units; the shift truncates to a multiple of 16 | computed; multiple of 16 checked over 9,000+ inputs |
| dx = -32768 gives `$a000` (dz < 0), `$8000` (dz = 0), `$e000` (dz > 0) | port, sweep of dz; the same values are in the grid |
| dz = -32768 gives `$6000`, `$a000`, `$c000` | grid cases, port |
| 27 of the 529 grid cases carry this error, each matched in the emulator | `atan_grid.py` values; error over 100 units counted from the port |

### Prose added for readers new to the game (lead, captions, "How we know")

| claim | source |
|---|---|
| real-time strategy and vehicle game; the player's carrier and the enemy's compete for a 64-island archipelago; 3D | README.md opening paragraph; render.md (the 3D engine) |
| angle units 1/65536 of a turn, `$4000` = 90 degrees, 0 along +z; 1 unit = 0.0055 degrees; 4096 headings, 0.088 degrees each | vehicles.md 2; arithmetic printed by the figure (360/65536) |
| T is the panel B table; Q15 = fraction times 32768; divs/divu are the 68000 divides | vehicles.md 2 (Q15, `divs`); general knowledge of the 68000 |
| the panel B formula is a fit, inferred | vehicles.md 2 "(inferred by fitting ...)" |
| the factor runs 12823 to 16356 | printed by `gen_atan.py` |
| the sawtooth grows toward 45 degrees where panel B's curve is steepest | reading of the computed curves on this figure (not a doc claim) |
| CORDIC described as the usual shift-and-add rotation method | general knowledge, generic |
| `neg.w` of -32768 is -32768; 27/529 grid cases; the emulator returned the pinned values (the port matched 529/529) | vehicles.md 2 |
| callcap: the emulator restores a snapshot, calls the routine with chosen inputs and records its outputs | DEVELOPING.md "Other tools" (`pm_fsm_diff.py`, `capture_hits.py` rows); vehicles.md proof table ("every run resumes `c_s30.snap` with pokes") |
| `c_s30`: Strategy game, carrier at Vulcan | README.md snapshot table |
| within 0.15 degrees over 200,000 random inputs | vehicles.md 2 |
| proven = emulator observation with a count; inferred = read from code only | ai.md opening ("Proof labels"), which vehicles.md adopts |

## Flags

- The -32768 error is up to 45 degrees off the axes and 90 only on them, and dz = -32768 triggers it as well as
  dx; `vehicles.md` 2 and the README digest state it that way.
- "The other seven repeat it": the per-octant worst error is 27.0 in each; the curves are mirror images by the
  unfold, not checked point by point.
