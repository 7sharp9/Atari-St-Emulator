# Starglider flight: input, the flight model, energy and the silos

The AGAV is flown by a "stick" made of three running totals that the mouse and the keyboard both write: stick x,
stick y and throttle. Totals never re-centre, so the stick stays where it was left. Once per main-loop pass
`$12340` turns those totals into bank, pitch, climb and speed and moves the craft. The silos and the energy towers
are the only places that refill the shield, laser and energy. Addresses are runtime absolute; `N(A6)` is the global
block at `$5bf00`.

Proof scripts are in `py/flight/` (run from `M68000/` with `python3`; `run_all.sh` runs them all). The model of each
routine is in `models.py`; `fly.py` is a reusable driver that holds keys or moves the mouse for a number of passes and
reads back the named fields.

A main-loop pass takes about 48,000 steps (47,400 to 48,500 typically, 42,500 to 54,500 at the extremes), so four
VBLs. An input must be held at least one pass to register.

## 1. The IKBD handler

`$b62a` sets up input. It:
- installs the VBL handler `$ac2e` and the IKBD handler `$b7be` (vector `$118`);
- clears the key flags;
- sends the IKBD commands `$0B 01 01` (mouse threshold 1) and `$07 04` (mouse buttons reported as keys). As a result,
  the left button arrives as key `$74` and the right as `$75`.

The handler is a byte state machine that re-points `$118` after every byte.

**In the idle state (`$b7be`)**, a byte below `$f8` is a key:
- a make code sets `$c34e + code` to 1 and stores the code in `$c3de` (the last key, which `$f53a` reads and clears);
- a break code clears the flag.

**A byte of `$f8` or more** starts a mouse packet:
- Bit 1 (left button) sets `$c3d6` and the latch `$c3d8`.
- Bit 0 (right button) picks where the next two bytes go:
  - Right button up (`$b834`, `$b860`): dx to stick x `$c3ce`, dy to stick y `$c3d0`.
  - Right button down (`$b8a2`, `$b8cc`): dx to stick x, dy to the throttle `$c3d4`.

Joystick packets (`$fe`/`$ff`) are parsed as mouse packets. There is no joystick path, so a joystick would steer at
random. No reader of `$c3d6`/`$c3d8` was found; fire is read from the key flags.

**Proof.** `gate_isr.py`: 30 random IKBD byte streams (745 bytes) are fed with `kbd` while the main loop is replaced
by `bra *`. The flags, totals, buttons, `$c3de` and `$118` match the model on 30/30 streams. The broken control,
which routes the right-button dy to the wrong word, scores 0/30.

## 2. Controls

The mouse is the default stick:
- left and right change stick x;
- forward and back change stick y;
- vertical movement with the right button held changes the throttle (moving the mouse back slows the craft).

The keyboard steps the same totals once per pass. It latches like the mouse: after a bank key is released the craft
stays banked until the opposite key is pressed.

| action | keys | per pass |
|---|---|---|
| bank left / right | ← / →, X / C, user keys `728`/`729` | stick x −/+ `$20` |
| dive / climb | ↑ / ↓, `;` / `.`, user keys `730`/`731` | stick y −/+ `$20` |
| accelerate / decelerate | Space, user `732` / `/`, user `733` | throttle −/+ `$10` (accelerate wins) |
| fire laser | left button (`$74`), Return, Insert, keypad Enter | section 4 |

The user keys come from the DEFINE AGAV CONTROLS page (K on the title, `$ce46`). It stores one scancode per prompt in
the order 730, 731, 728, 729, 732, 733, then Y accepts, E returns to the title and any other key asks again. User
keys add to the fixed ones rather than replacing them, so defining X as bank right cancels X's fixed bank left.

**Letter commands.** `$d29a` reads ASCII from `$f53a`, upper-cased:

| key | effect | proof |
|---|---|---|
| F | toggles the cross-hair lock `705` | driven |
| L | launches a missile (`$d50e`, section 4) | driven |
| Q / S | sound off / on (`715`) | driven |
| Esc | abandons the game (`$ca20`) | driven |
| P | takes a missile while docked, up to 2 (`$d4e6`) | read only |
| I | the interrogate screen while docked (`$d5d0`, `frontend.md`) | read only |
| N, M | practice-mode commands (`$d4d8`, `$d4be`): N sets the pending score to BCD `$5000` (5000 points), so each N moves the level on every second press (`objects.md` section 5); M toggles `711` | N driven (`py/curios/level_from_score.py`), M read only |

**Proof.**
- `gate_controls.py`: 400 random key-flag arrays and user keys, callcap of `$d29a` including the launch path and the
  RNG, 400/400. The broken control, with a key step of `$12`, scores 88/100.
- `gate_letters.py` drives the letter commands: 6/6.
- `gate_definekeys.py` drives the define-keys page from `g_title`: A B Z X S D are read back exactly, 6/6. In flight
  the user keys Z and A then move stick x and stick y by −96 over 3 passes.

**Practice mode.** Pressing Del (`$7f`) and then typing J, S, space, A, R, G, entered twice, toggles the flag `717`.
It works only while the cross-hair lock is on and the throttle is 0 (`$d420`).
- With `717` set, every pass pins energy to `$55f0`, shield to `$9c40` (40,000) and laser to `$7530`
  (`$cbc8..$cbd4`). The largest single shield cost found is a mine's `$3a98` (15,000), so practice mode should be
  unkillable by hits (inferred; not driven), up to level 31: from level 32 a collision crashes the game, practice
  mode or not (`objects.md` section 4).
- With `717` set, G on the title opens the developer model viewer (`$dd7a`, `frontend.md` section 4). Without
  it, G starts the game like any other key.
- The pilot rating's CHEAT!?! grade does not detect this mode: it is the top grade by level and accuracy
  (`frontend.md` section 4).

`gate_cheat.py` drives the toggle: 2/2 (throttle 0 sets `717`; a control with throttle not 0 leaves it clear).

## 3. The flight step

`$12340` runs once per pass (called at `$caa4`).

**The state.**
- Position: words x `302`, y `304`, z `306(A6)`. x and z wrap at 65536; y is negative upward and starts at −48.
- Angles: pitch `314`, yaw `316` (0 faces +z) and roll `318`, with 4096 units per turn.
- The sine and cosine tables at `$1e8f8`/`$1f0f8` hold 16384·sin and 16384·cos.

**Each pass, in order:**

1. **Move.** `320/324 = (speed·sin yaw, speed·cos yaw) · 2 >> 16`; then x += `320` and z += `324`. At full speed
   that is about 240 units per pass. Skipped in missile view (`712`).
2. **Stick.**
   - Stick x is clamped to ±`$1f0` and roll = −(stick x >> 4), at most ±31.
   - Stick y is clamped to ±`$140`.
   - The climb rate is `570 = −(stick y >> 4)`, with a dead zone of ±`$30`.
3. **Throttle.**
   - The throttle is clamped to [−`$1df`, 0] and the speed `542` = −throttle, so 0 to 479.
   - While docked (`714`) the throttle is forced to −10, or to 0 once the craft is ready to launch.
4. **Turn and climb.** Unless docked, yaw −= roll (so a full bank turns about 2.7° per pass) and y += climb.
   Then roll += `640` and `640` decays by 2. `640` is a random bank kick that hits add.
5. **Height limits.**
   - At the ground (y ≥ −20), y is held at −20 and stick y gains 8.
   - At the ceiling (y < −1800), y is held at −1800 and stick y loses 8.
   - Pitch = stick y >> 1.
6. **Missile view.** With `712` set, a chase camera at `618..634` follows the missile instead, until the timer `630`
   runs out (`$f320`).
7. **Cross-hair.** `580/582` = (160, 68) plus (stick x >> 2, −stick y >> 3) in colour, fixed while the lock `705`
   is on.

**Proof.** `gate_integrator.py` runs 400 randomised states through `stserver` calls of `$12340` and compares the
whole block `$5bf00..+$1d00`, the stick words and `$c34e..$c3e0` with the model: 400/400. The branches are flying
202, docked 84, missile view 85 and both 29. The broken control, with the ceiling at `$f8f0`, scores 91/100.

`fly.py` gives the same-snapshot, same-budget input table (`$STARGLIDER_WORK/flight/fly_table.txt`), each row against
a no-input control:
- ← for 4 passes: stick x −128, roll +8, yaw −108.
- ↓ for 4 passes: stick y +128, pitch +64, y −48 → −146.
- Space for 4 passes: throttle −20 → −84, speed 20 → 84.
- Mouse dx +20: stick x +20.
- Right button with dy −30: speed 20 → 50.

Shield and hit-count differences in every row are the enemies firing on the moving craft, not the inputs.

## 4. Energy, shield, laser and missiles

| word | what | cost or fill |
|---|---|---|
| `606` energy | full `$ffff` | −`(speed >> 4) & $1ff` per pass (`$cbda`); +`$190` per pass at a refuel hub |
| `608` shield | full `$ffff` | −`$12c` per pass while scraping the ground (y ≥ −20, moving, not docked or refuelling, `$cc02`); enemy hits (`objects.md` section 4); refilled at a silo |
| `650` laser | full `$ffff` | −`$100` per shot; refilled while docked |
| `632` missiles | 1 at the start, at most 2 | P in a silo adds one |

- **Running out.** Energy underflow ends the game with "POWER DRAINAGE TOO GREAT!" (`300 = 1`). Shield underflow
  ends it with "SHIELD DEPLETED, AGAV DESTROYED!" (`300 = 2`).
- **Laser, `$131f8`.** It fires when the laser has energy, the craft is not docked and a fire key is down. Each shot
  counts `176` (shots fired), sets a 4-pass cooldown `644` and costs `$100`. What a shot hits is in `objects.md`
  section 4.
- **Missile, L.** It needs a missile, no dock, no missile already in flight, and `658` = 0. It costs a missile, sets
  the missile-view flags `712/713`, copies the craft position to `618..622` and starts the timer `630 = $ff`. While
  `712` is set, enemy fire and rams do no damage.
- **The rating counters** are `176` shots, `184` hits, `192` silo dockings and `196` hits on the AGAV, shown on the
  pilot rating page (`$13596`).

**Proof.**
- `gate_energy.py`: drain 59/59 over speeds 0, 15, 16, 20, 100, 300 and 479; refuel 16/16; ground scrape 6/6; both
  game-over codes 2/2.
- `gate_laser.py`: 7/7 (each fire key, the floor, no fire at zero energy, and a control).
- `gate_messages.py` breaks on the text printer `$bcba` with the expected string in A1, and a control prints none:
  7/7. The call sites are POWER `$cd0e`, SHIELD `$cd2c`, REFUELLING `$fcfa`, DOCKING `$fbae`, LAUNCHING `$101da` and
  MISSILE VIEW `$fe1c`.

## 5. Silos: docking and launch

A silo is object type 6. Flying into one with the right heading docks; `$13138` tests
`(silo heading + yaw) & $fff` outside [`$154`, `$eac`). Docking:
- sets the shield to `$ffff`, counts a docking in `192` and sets `714`;
- places the craft in the silo;
- swaps the scene for the docking-bay records (`objects.md` section 1).

While docked (`$101a8`):
- The throttle is forced to −10 until the craft is within 200 units of the silo's z, then to 0.
- The laser refills by `$190` per pass. When it would overflow, `658 = $1e` marks the craft ready and the docking
  sample plays.
- "DOCKING, PRESS I FOR INTERROGATE" is printed until then.
- The docked screen offers "Press SPACE BAR to launch, or I to Interrogate computer".

**Launch.** Accelerate with `658 = $1e` (`$d3c6`): `714` is cleared, the throttle is set to −320, two RNG draws are
made, the craft is placed at y = −48 and x + 2000, and "LAUNCHING FROM SILO" is shown while `658` counts down. The
throttle eases by 5 per pass meanwhile.

A new game (`$e586`) starts at x = z = `$8020`, y = −48, with everything full, throttle −20, one missile, level 1.

**Proof.** `gate_energy.py` and `gate_messages.py` drive a poked silo entry (craft at object 26), the docking, and the
launch with Space.

## Open

- The enemy damage routines are gated in `objects.md`. The tables `$15a26`/`$15a62`/`$15a9e` are named there.
- No reader of the left-button latch `$c3d8` was found by an absolute-address scan; an A6- or `$c34e`-relative reader
  would escape that scan.
