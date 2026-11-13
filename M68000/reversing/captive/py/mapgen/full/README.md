# `fed_MapGen` whole-generator port

Evidence for `reversing/captive/mapgen.md`, "The pipeline", "Shafts and reservations", "After the flow field" and
"Locks and keys". Run from `M68000/` with `uv run python -I reversing/captive/py/mapgen/full/<script>`. The repo root
is found by walking up to `tools/rdis.py` (or `M68000_ROOT`). Captures and constant inputs go to the gitignored
`scratchpad/captive/mapgen_full/` (below, D); the capture scripts need `scratchpad/captive/mg_ret.snap` and run the
shortcut call of `../gen.py` through `stserver`. The models build on `../stages/models.py` and `../digger/dig.py`.

Order: the shaft captures, then `mktemplate.py` (the chain gate checks its constructed start state against it), the
final captures and the placement dumps; the stage gates also read `../stages/`'s dumps (`stages/dumpall.py`).

| script | what it proves | command | expected output |
|---|---|---|---|
| `shafts/capture.py` | module block and D0-D7 at `$23ca4 $23ca8 $23cb0 $23cb4 $23ccc $23cd0`, plus the 50 bytes at `13712(A6)` | `shafts/capture.py d2_1_<b>.bin <b> <b+250> 1` for b = 0, 250, 500, 750; `shafts/capture.py d2_0_0.bin 0 100 0` | five files in `D/shafts/`, about 2 minutes per 250 seeds |
| `shafts/shafts.py gate` | ports of `$245e2` (shafts), `$263c2` (reservations), `$263fa` (room pass 2) | `shafts/shafts.py gate D/shafts/d2_1_{0,250,500,750}.bin`; `... gate D/shafts/d2_0_0.bin` | three lines `match 1000/1000`; three `match 100/100` |
| (control) | the gate discriminates | `--break dir`, `nodoor`, `nores`, `roomsize`, `nooverlap` on the 1000 | shafts 2/1000, 7/1000; reserve 499/1000, 502/1000 (roomsize); pass 2 11/1000 (roomsize), 770/1000 (nooverlap) |
| `shafts/shafts.py chain` (`shafts/chain.py`) | from (D0, D2) alone to `$23cd0` | `shafts/shafts.py chain <the four D2 = 1 files>`; `--break nores` on `d2_1_0.bin` | `built ... 1000/1000`, `chain to the digger return $23cb4 ... 1000/1000`, `... $23cd0 ... 1000/1000`; control `129/250` |
| `shafts/stats.py` | shaft, reservation and room-pass census | `shafts/shafts.py stats <the four D2 = 1 files>` | `shaft groups requested per base (G): {..., 5: 990}`; `placed 12988/35665; $fffd cells at $23cb0 157914`; `placed 17312/30360; new $23 cells 100625, of them on a cell reserved before the digger 27869` |
| `mktemplate.py` | writes `D/template_23ca4.bin` (the module block at `$23ca4` for D0 = 0, D2 = 1) and `D/fed_init.bin` (federation `$1bd3e`-`$1d9e8` of `mg_ret.snap`) | `mktemplate.py` | the template's non-zero runs outside the seed-dependent bytes: the constants (`12401 1 01`, `13209 1 3f`, `13625 1 c7`, ...) and the 15 output pointers (... `13741 3 01d942`) |
| `capture_final.py` | the module block and federation `$1bd3e`-`$1ea08` before and after the encoder and at the return, with D0, D5, D6 | `capture_final.py f_<d2>_<lo>.bin <d2> <lo> <hi>` for (1, 0, 100), (1, 300, 400), (0, 0, 100), (0, 300, 400) | four files in `D/final/`, about 1 minute each |
| `chain_run.py gate` | **the whole generator from (D0, D2)** equals the emulator's returned output | `chain_run.py gate D/final/f_*.bin` | `constructed template == captured template: True; constructed federation block == mg_ret.snap: True`; `... 400/400` (about 1 minute) |
| (control) | | `chain_run.py gate D/final/f_1_0.bin D/final/f_0_0.bin --break key_slack=0x4000` | `14/200` |
| `chain_run.py encoder` | the encoder `$23936` from the emulator's state at `$200ee` | `chain_run.py encoder D/final/f_*.bin`; control `... f_1_0.bin f_0_0.bin --break tile_default=33` | `400/400 (400 changed)`; `0/200` |
| `chain_run.py locks` (`lockcensus.py`) | the lock and key census: dig order, reachability, dependency order | `chain_run.py locks <d2> <lo> <hi>` for the four ranges | per range `bases: 100`, `dig: G0(K) <= G0(D)` = `with key`, `bypass: E reachable without D: 0`, `bases with a dependency cycle: 0`; summed over the four: locks 11723, with key 8617, keyBFS 8586, key on the door cell 31 |
| `chain_run.py run` | one base to a file (module, federation block, D0/D5/D6) | `chain_run.py run <d0> <d2> <out.bin>` | the file |
| `cgate.py`, `cmodels.py` | `$25722`, `$25c1e`, `$2676c`, `$25414`, `$26478`, `$264ac`, `$264c8`, `$268f8` each from the emulator's state before it | `cgate.py 0 40`; `cgate.py 0 0 --dumps D/pdumps --d0s 44,...,54,209,...,219` | 8 lines `exact 80/80` (`$2676c` 40/40); 8 lines `exact 44/44` (`$2676c` 22/22) |
| (control) | | `cgate.py 0 40 --stage <s> --break <k>=<v>` | `25722 key_slack=0x4000` 14/80, `keep_keyless=True` 29/80, `lock_dirmask=7` 2/80; `25c1e term_start=30` 0/80; `2676c vault_kind=5` 0/40; `25414 sw_walk=7` 2/80; `26478 n19=0x13` 7/80; `264ac item5f=1` 2/80; `264c8 item61=1` 2/80; `268f8 note_word=1` 78/80 |
| `pgate.py`, `pmodels.py` | the group writer `$25e10` through `$25d88`, `$2543a`, `$2419a`; the object list | `pgate.py 0 40`; `pgate.py 0 0 --dumps D/pdumps --d0s 44,...,54,209,...,219` | 3 lines `exact 80/80`; 3 lines `exact 44/44` |
| (control) | | `pgate.py 0 40 --stage <s> --break <k>=<v>` | `25d88 skill_add=1` 0/80, `hp_cap=0x8000` 51/80; `2543a guard_hpadd=0` 0/80; `2419a struct_walk=4` 3/80, `struct_start=6` 5/80 |
| `pdump.py` | stage dumps (as `stages/dumpall.py`) for any D0 list | `pdump.py <d2> 44 45 ... 54 209 ... 219` for d2 = 0, 1 | 44 files `D/pdumps/d<d2>_<d0>.bin` |
| `groups.py` | the difficulty-per-mission table from the emulator's final group lists | `groups.py` | six blocks; e.g. `D2=0 mission  1 (D0 0..10): groups/base 24..146 mean 96.6` |
| `perbase.py` | groups, members and free bytes per base | `perbase.py <d2> <d0> ...` | one line per base |
| `typetab.py` | the creature type table `$26040` and slot lists | `typetab.py` | 64 rows |
| `stagestats.py` | per-stage counters and the object census over chained bases | `stagestats.py 0 0 100` | `{13268: (509, 97, 10), 13270: (2922, 99, 32), ...}`; `objects by item type: {'0x19': 4989, ... '0x5c': 834, '0x5d': 1197, '0x5f': 99, '0x61': 489, '0x66': 2}` |
