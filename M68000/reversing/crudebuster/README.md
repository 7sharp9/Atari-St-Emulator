# Crude Buster (Data East, 1990), reverse-engineering workspace

Second arcade subject (after Final Fight). Target set: MAME `cbuster` (World FX), from the merged zip `cbuster.zip` (Dropbox `Daves/MAME games/`), copied to `~/mame-roms/cbuster.zip`;
it also holds the clones `cbusterw`, `cbusterj`, `twocrude` (US) and `twocrudea`. `mame -verifyroms cbuster` reports "good". MAME 0.289 is the emulator and oracle. Hardware: 68000 + HuC6280,
two DECO tilemap chips, DECO sprite chip, YM2203 + YM2151 + 2 OKI6295 (`architecture.md`). The 68000 program is encrypted in the ROM files and decrypted by MAME at load: all addresses here are of the
decrypted image.

## Files

| file | content |
|---|---|
| `architecture.md` | memory map, boot, vectors, protection, frame/VBL structure, game flow, object pools, level scripts, flags |
| `cbmame.sh` | headless MAME wrapper (`script` = with debugger for Lua, `run` = no debugger; `CB_SET`, `CB_RUN`, `CB_ROMS`) |
| `lua/lib.lua`, `lua/drive.lua` | helpers and the input-plan driver (`CB_PLAN`, `CB_SHOTS`, `CB_DUMP`, `CB_SAVE`, `CB_LOAD`) |
| `lua/dumprom.lua` | dumps the decrypted program, the HuC6280 code and the ioport names for all five sets |
| `lua/framelog.lua`, `flaglog.lua`, `spawnlog.lua`, `protlog.lua` | per-frame logs used by the gates |
| `lua/startlevel.lua` | starts any level 0-5 (`CB_LEVEL`): replaces the level byte written at game start (`$146e`); proven by a screenshot of each level at frame 1000 |
| `lua/plans/play1.lua`, `walk1.lua` | coin 600, start 700; walk right and punch |
| `py/kernel/` | `gates.sh` and the gate scripts of `architecture.md` |

Setup (not committed): `~/mame-roms/cbuster.zip`; dumps with
`for s in cbuster cbusterj cbusterw twocrude twocrudea; do CB_SET=$s CB_OUT=<M68000>/scratchpad/crudebuster/rom cbmame.sh script lua/dumprom.lua 20; done`.
Driver sources used (curl from the `mame0289` tag into `scratchpad/crudebuster/src/`): `mame/dataeast/cbuster.cpp`, `deco16ic.cpp/.h`, `mame/shared/decospr.cpp/.h`, `devices/cpu/h6280/h6280.cpp`, `6280dasm.cpp`.
Attract cycle seen on a cold boot with no input: story crawl, title, two-player demo, best scores, repeat (about 9,500 frames).

## Notes

- Forcing the level-cleared flag (`$80040` bit 4) by poke hangs at the next stage card; start the level you want with `startlevel.lua` instead.
- `tools/rdis.py` does not follow the longword state tables inside the type handlers; scan the linear listing (`tools/disassemble.py --rom <img> --base 0 --all 0 2d000`) before claiming a writer or caller.
- Input names for `lua/lib.lua`: ports `:P1_P2` (`P1 Up`, `P1 Button 1`, `1 Player Start`, ...), `:COINS` (`Coin 1`); levels are read once per frame, hold several frames.
