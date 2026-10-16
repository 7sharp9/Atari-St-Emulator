# Facts behind `economy.svg` (generator `py/build_economy.py`)

| flow | amount | evidence | source |
|---|---|---|---|
| lord record `$4e514`, 32 B: +6 food, +8 troops_field, +14 loyalty_pressure, +24..31 goods | | | economy.md section 1 struct |
| fisher mode `$60` (`$15ddc`, PC `$15e18`) | food +4 per trip | proven (fsm15 `$60`) | economy.md 1 flows; ai.md `$60` row |
| farmer mode `$16` (`$1507c`; `$1508a` Plough) | +2, +2 more with Plough; 0 of 5164 returns doubled | proven (fsm15) | economy.md 1 "Plough doubling" |
| mode `$42` -> `$600a` (`$603e`), no flag bit 6 | food -2; food <= 2 -> `$3c08`, delivery lost | proven (gate_orders) | economy.md 1 flows, 2a |
| mode `$7c` pulse `$163b8` | -1 per parked man per pulse | proven (heartbeat block) | economy.md 1 flows; ai.md `$7c` census note |
| order `$06` mode `$1a` (`$150f2`) | food >> shift to 36(group); loyalty +16 >> shift; live 22 -> 11 | proven (fsm15 `$1a`) + live | economy.md 1 flows |
| order `$12` `$3bc0` | 36(group) >> shift to the town; loyalty -8 own side; live 22 -> 147 | live (Corroborated in the doc) | economy.md 1 flows |
| trade `$63f4` (order `$1c`, mode `$78`) | sell at 2 x price, buy back in `$650a` order; food spent -> lord food; loyalty -8 own / +8 other | proven (gate_orders 4684/4684) | economy.md 2c |
| mode `$2a` join (`$1b2a`; `$152d4`) | troops_field -1 | proven (fsm15 `$2a`) | ai.md `$2a` note; economy.md struct comment |
| `$1b8c` -> `$1c04` leave; `$37c2` `$382a` | +1; -1 | proven (teardown block 1847/1847) | economy.md 1 flows |
| order `$04` `$1c96` | -1 / +1 pairs, live 6 pairs for 6 men | live | economy.md 1 flows |
| revolt `$25d6` `$2644` | -1 on the old lord, captain with no group | proven (diff_revolt) | economy.md 1 flows |
| pigeon landing `$42be` | +1, 6 of 6 | live | economy.md 1 "Pigeon landing" |
| KILL tail `$567e` | -1, an ungrouped man | proven (combat block, KILL branches) | economy.md 1 "Pigeon landing"; ai.md `$5590` outcomes |
| gatherers `$5cde` -> `$3e/$40/$6a` -> `$42` -> `$600a` -> `$60dc` | goods +1, throttle ~8100 ticks | proven (gate_orders `$600a` 4491/4491, `$60dc` 741/741) | economy.md 2a |
| merchants `$159de` (`$57fec` mod 6) / `$159a4`, nearly always the home lord | k5_s4 over 100M: 10 decrements at `$159f0`, 8 increments at `$159ba`; 1 of 10 `bpc` pickups took lord 8's Plough via the stale A0 at `$15b54` and banked it at lord 7 (`py/merch_moves.py`) | live (the routines proven, fsm15 `$52`/`$54`) | economy.md 2b "Live (`k5_s4`)" |
| order `$10` mode `$6e` `$61f8` -> `$6352`/`$638c` | goods >> shift | proven (gate_orders 8599/8599) | economy.md 2c |
| exchange `$160f8` (modes `$8e`, `$90`) | weapon back, best bow/sword/pike taken, farmer Plough; lord >= 8 misdirected | proven (gate_equip 385/385, 201 states) | economy.md 2c |
| order `$18` drop equipment `$39d4` D7=2 | carried >> shift | code read | strategy.md orders table |
| loyalty on the first pulse after a park: hungry (troops_field x 4 >= food) +2, fed -1; >= 600 `$550e`, reset 300; 27 natural `$550e` calls = 10 heartbeat (`$158cc`) + 17 conquest (`$539a`/`$53f6`) | | proven (heartbeat block; diff_revolt 1778/1778) | economy.md 3 "Natural count", 6 "The hunger revolt" |
| mission 1: both enemy lords built at 608, first winter pulse (+200M..+240M from `m1_s0`) revolts them to their own side, loyalty 300 | | live | economy.md 3 (`lpm1.out`, `py/lpsum.py`) |
| a man in `$7e` pulses but never on the first-pulse edge | | live (one deserter traced) | ai.md `$7e` dwell note |
| shift = posture - 2 (`$30fe`) | | | economy.md 1 flows, 2c |
| `$7c` park needs `$57fd0 == 0`, entered from `$16`, `$4e`, `$5e` | | proven (heartbeat block) | economy.md 3a |

## Notes

- Order `$06` loyalty: `loyalty_pressure` 0 -> 16 at posture 2 and 0 -> 8 at posture 3 (economy.md 1, `$150f2` row; 3a). The
  figure shows the formula `+16 >> shift` only.
- The KILL tail `$567e` takes the man off the home lord's `troops_field` (ai.md `$5590` outcomes, economy.md 1 "Pigeon landing").
- `+6` of the lord record is food; `powermonger.sym` still names it `troops_reserve` (entries `$163b8`, `$15042`), as does
  the pm_fsm_ref `h_mode7c` note ("`troops_field*4`: ==0 -> epilogue / >= reserve -> +2 / < reserve -> -1"). The figure
  omits the `== 0` exit.
- Order `$12` (`$3bc0`) is shown as live (one run, town 22 -> 147).
