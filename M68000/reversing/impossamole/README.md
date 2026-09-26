# impossamole — booted to its title screen through a Replicants crack menu

First pass. *Impossamole* — Gremlin Graphics / Core Design, 1990, an isometric platformer.
The copy in hand is a cracked scene release: a "Replicants"-badged boot menu leading into an
"E-Motion"/"R.AL" trained-and-packed version. No `\AUTO\` folder; the disk boots directly
(executable boot sector, checksum `$1234`) into the crack's own menu code, not straight into the
game.

## The disk image

**Commercial and not committed here.** To reproduce:

```
unzip "impossamole_emotion.zip"   # -> "impossamole cr replicants - emotion cr replicants.st"
#   impossamole_emotion.zip                                    (from the mac-st-sources Dropbox folder)
#   impossamole cr replicants - emotion cr replicants.st       sha256 f7e358080d17022f03c9d7b4c86e63998164597aea73f7e4f10aafcae9a9f6f5   (819200 bytes)
```

Standard 80-track double-sided FAT12 image (BPB: 512 bytes/sector, 2 sectors/cluster, 1 reserved
sector, 112 root-dir entries, 1600 total sectors, 10 sectors/track, 2 sides — `1*80*2*10*512 =
819200`). Root directory (28 files; the BPB's own claimed `nFATs=1` byte undercounts what's
actually mastered on the disk — the real root directory only resolves if a reader assumes 2 FAT
copies, i.e. trust the disk's physical layout over the BPB field when parsing it by hand):

| file | what |
|------|------|
| `EMOTION+.PRG` | 7094 bytes, magic `$601a` — a small GEMDOS loader, part of the crack menu |
| `MINDBOMB.PRG` | 19840 bytes, magic `$601a`, only file with `attr=$20` (archive) — the crack's own loader/menu binary |
| `E_MOTION` | 309398 bytes, no extension, starts `$6000` (`bra.w`) not `$601a` — not GEMDOS-loadable by name; raw code/data the crack loads directly, likely the "E-Motion" demo/utility behind the boot menu's F2 option |
| `CHARS11.DAT`, `SPRTS22.DAT`, `SPRTS33.DAT` | font + two sprite banks |
| `BRMUDA{22,33}.DAT`, `ICELND{22,33}.DAT`, `JUNGLE{22,33}.DAT`, `MINES{22,33}.DAT`, `ORIENT{22,33}.DAT` | per-level (Bermuda / Iceland / Jungle / Mines / Orient) data pairs — the game's 5 worlds |
| `SELECT44.DAT` | world-select screen data |
| `MDATA1.DCH`…`MDATA5.DCH`, `PICTURES.DCH` | more level/graphics data |
| `MST.IMG` | 56457 bytes, likely a Degas-family picture (title/loading art) |
| `E_MOTION.PC1`, `PRES_ST.PC1` | Degas PC1-compressed pictures — crack-intro art |
| `DISK.ID` | 4 bytes, `00 ff 00 ff` — a protection-check magic value the crack's loader reads back and compares (see below) |
| `DESKTOP.INF` | GEM desktop config; defines the "REPLICANTS" menu group, no auto-run entry |

## How it was run

```
ATARI_NOTRACE=1 ATARI_TRACE_GEMDOS=1 ATARI_TRACE_OS=1 \
  dotnet exec bin/Debug/net8.0/M68000.dll 800000 --disk-a "impossamole cr replicants - emotion cr replicants.st"
```

The boot sector prints a Replicants banner (`Cconws`) with a `=`-by-`=` loading-bar animation
(one `Bconout` per disk block probed, `Bconstat` polled for an abort key between each), then blocks
on `Crawcin`/`Bconin` at step 724388 — the boot menu itself:

```
========================================
=       THE REPLICANTS PRESENTS        =
=---------------------------------------
=  PRESS F1 FOR IMPOSSAMOLE+++          =
=--------------------------------------=
=  PRESS F2 FOR E-MOTION+(EXIT DESKTOP)=
=--------------------------------------=
=     THE REPLICANTS RULES FOREVER     =
========================================
```

**F1** (scancode `$3B` make / `$BB` break) selects the game and lands on a second, trainer, menu
(`trainer_menu.png`):

```
THE REPLICANTS PRESENTS
IMPOSSAMOLE+++
CRACKED TRAINED 'N' PACKED BY R.AL
PRESS 'T' FOR TRAINER
UNLMT LIVE, MONEY & AMMO
NGS TO: AVB & THOR, ZAE, MCA, HOWDY,...
```

Any other key (tried: Space, `$39`/`$B9`) skips the trainer and proceeds — past this point the loader
switches from its own banner code to real GEMDOS file I/O (`Fopen`/`Fread`/`Fclose`, funcs
`$3d`/`$3f`/`$3e`) to pull in the game's data files, and ~20–30M steps later reaches the real title
screen (`title_logo.png`): the IMPOSSAMOLE logo, Gremlin Graphics' hero character, and the "Core
Design" / "Gremlin" publisher logos. No instruction wall, no crash, both crack-menu keypresses and
the game's own GEMDOS-driven loading path work end to end.

**Keyboard discipline** followed the pattern from prior games (Super Sprint, Cadaver): each key is
two separate `kbd` REPL calls (make, then break) with a real `s <n>` step count between them, not
one `kbd <make> <break>` call — see CLAUDE.md.

## Open item: title screen sits in what looks like a VBL-gated wait

Past the title screen the PC settles into a tight loop at `$1ab90`:

```
$01ab90: move.b $1a2e9.l,D1      ; wait until frame-counter byte >= $39 (57)
$01ab96: cmp.b  $1ab88.l,D1
$01ab9c: blt    $1ab90
$01aba0: cmp.b  $1a2e9.l,D0
$01aba6: beq    $1ab90
$01abaa: clr.b  $1a2e9.l
$01abb0: rts
```

Two snapshots 30M steps apart (`$1ab90` then `$1aba0`, both inside this loop) both read `$1a2e9 =
$00` — the counter this loop is waiting on is not advancing at all across 30M steps (~3.75M real
CPU-seconds' worth at this project's ~8MHz model, far more than the ~57 VBL ticks the loop needs if
VBLs were reaching it). Two explanations to check next session, in order:

1. `$1a2e9` isn't actually VBL-driven — find its real writer (the `$1abdc`/`$1abc2` routines nearby
   also touch it and `$1a2e8`, and look like a semaphore/handshake, not a raw interrupt counter;
   `find_ram_callers.py`/a `watch $1a2e9` over a fresh run from `after_retry3.snap` settles this).
2. The game's own VBL handler is installed but genuinely not being invoked yet at this point (e.g.
   gated behind something else this loop's sibling branch checks — `$1abdc` polls `$1c4bf` for
   value `$1d` twice, which smells like a handshake with an interrupt-driven producer).

**Trap that cost time reaching this point, not yet worth a CLAUDE.md-wide entry but worth flagging
for future games:** `resume <snap> repl` does **not** reattach a disk image mounted with
`--disk-a` on an earlier cold-boot run — `diskA` lives outside `MmuSnapshot` (see `MMU.fs`
`tryReadSector`'s doc comment on `dmaSectorCount`, the same "not in MmuSnapshot" note applies to the
disk mount itself). Forgetting `--disk-a` on a `resume ... repl` silently drops every floppy read
from that point on (`ATARI_TRACE_FDC=1` shows `-> no data` for every request, indistinguishable at
a glance from a real protection/geometry failure) — cost a live pass on this workstream a wrong
"the emulator can't read sector 11" diagnosis before the missing flag was spotted. **Always pass
`--disk-a` on every `resume ... repl` invocation for a disk-booted game, not just the first cold
boot.**

## Files

| file | what |
|------|------|
| `README.md` | this file |
| `trainer_menu.png` | crack trainer-menu screen, reached via F1 from the boot menu |
| `title_logo.png` | the real game's title screen, reached by skipping the trainer |

## Not yet exercised

Everything past the title screen: world-select menu, actual isometric gameplay, sprite/tile
formats, level data (`MDATA*.DCH`, `BRMUDA*.DAT` etc.), and control flow / CFG extraction — blocked
on the open item above.
