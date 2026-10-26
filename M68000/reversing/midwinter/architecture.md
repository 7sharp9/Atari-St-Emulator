# Midwinter: architecture

Runtime addresses in the cracked build (`README.md`, "Packing"): game text `$800..$261a2`, data `$261a2..$2dd2e`,
A6 = `$2c376` (the globals base) throughout. Names are in `midwinter.sym`.

Every count below comes from a REPL script in `repl/`, run from `M68000/` as
`ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume <snap> repl --disk-a scratchpad/midwinter/zuul067.st < reversing/midwinter/repl/<script>`.
The snapshots are `drive.txt`'s (`d_title`, `d_options`, `d_team`, `d_decisions`, `d_ski`) plus four driven from them,
kept in `scratchpad/midwinter/agents/static/` (`s_click1` bio, `s_map`, `s_view` Decisions, `s_3d_6` goggle view);
the logs (`*.log`) are there too. The click scripts in `repl/` rebuild those four from `d_team.snap`. `tables/` holds
the 16 icon/action tables, the 47 indirect jump sites and the static file-load call list.

Frame rates are in emulator VBLs. The emulator raises the VBL every 12,000 instructions, not every 160,256 cycles,
so a count of frames per VBL is not the real ST's frame rate.

The whole-image listing (`tools/disassemble.py --snap d_team.snap --all 800 261a2`, 43506 lines, reaches `$2619e`)
loses instruction sync at `$10840`, `$1fa0a` and `$19ce2`; re-disassemble at the real entry before reading those.

## 1. Vectors (`py/vectors.py` on d_team.snap and d_title.snap: identical; MFP regs from `repl/vec.txt`)

| vector | target | role (from body) |
|---|---|---|
| $14 zero divide, $68 HBL | $64f4 | bare `rte` |
| $70 VBL | $61a8 | VBL handler (section 2) |
| $114 MFP timer C | $64f6 | `addq.l #1,$4ba` + clear ISRB bit 5: the 200 Hz system tick. TCDCR $51 (prescale /64), TCDR $c0: 2457600/64/192 = 200 Hz. 400 hits per 100 VBLs in every census |
| $118 MFP ACIA | $6400 | IKBD ISR: $f6..$ff headers; $f8-$fb mouse packet buffered at $2c31e, 3 bytes then `bsr $664a`; $ff joystick packet into $2c328 (+flag $2c32c); key make/break into key-state table $2c29a and last scancode $2c324 |
| $84 trap 1, $b4/$b8 trap 13/14, $28 line-A | TOS | unchanged |
| $88 trap 2 | $7fd84 | NOT a handler: the resident depacker uses $88 as a scratch pointer (`$648 move.l A0,$88.w`); $7fd84 = last depack source+4 |
| $108 MFP CTS, $124..$130 RS232 | TOS | enabled but not game code |

MFP: VR $48 (base $100, software EOI), IERA $1e (RS232 only), IERB $64 (CTS, timer C, ACIA). Timer A/B/D, FDC (GPIP5)
and the rest are disabled. Vectors $100,$104,$10c,$110,$11c,$120,$134..$13c and $c0..$fc hold non-pointer data
(something overwrote them; harmless because those channels are disabled; writer not identified).
Installed by `$67a8 install_vectors` (saves old $70/$118/$114, sets $62b8=2); undone by `$680a restore_vectors`.

## 2. VBL handler $61a8 and the pointer mode $62b8

`$61a8`: `addq.w #1,$637e` (frame counter), clear $2c31a (the flag `$6840 wait_vbl` spins on), copy 16 palette
words from pointer $24f24 to $ff8240 if non-zero then clear it, then `$69b8 sfx_driver`, `$65c0 vbl_mouse_joy_merge`,
`$652e keys_to_mouse`, a debug branch gated on `$2a14c == $acdc` (keys F1/F2; $2a14c is loaded from file 48.2,
inferred cheat/debug switch), `$6998 restore_pointer_bg` if $24fbc, then `jsr` through the longword table $62a0
indexed by the word $62b8.

$62b8 is the pointer mode; the same index also selects the mouse-motion handler from table $62ac (`$66aa`, reached
from `$664a mouse_packet` and every VBL via $65c0):

| $62b8 | VBL entry ($62a0) | motion entry ($62ac) | used by |
|---|---|---|---|
| 0 | $63f4: flag $24fbc, `$6852 draw_pointer` | $66ce: absolute pointer $24fa2/$24fa6 clamped to 0..310, 0..198 | title wait, options, team, bio, decisions |
| 1 | $6380: pointer cell (x/2-25, y/2-25 clamped 1..48/1..49 to $24fb2/$24fb6), then mode 0 draw | $6712: clamped 3..310, 3..197 | map screen ($15ce) |
| 2 | $675c: `rts` (no pointer) | $66c0: raw deltas summed into $24faa/$24fae | startup ($b84), 3D travel ($12514) |

Proof (100 VBLs, `repl/hits_all.txt` = `hits 1200000` on all 786 call targets + handlers):
d_team / d_options / s_click1 (mode 0): $61a8 $63f4 $66ce $6998 $69b8 $6e06 $65c0 $652e = 100 each.
s_map (mode 1): $6380 $6712 $675c(the shared rts at the end of $6712) = 100. s_3d_6 and d_title (mode 2): $675c $66c0 = 100.

Button state: $24fba = header & 3; left latched in $24fc0, right in $24fc2; $24fa0 = "button still held" (cleared by a
buttonless packet; every screen sets it to -1 after acting, and `$bcfe`/`$bd22` wait for it to clear first).

## 3. Program skeleton and main loops

Entry $800: `lea $2d446,A7 / lea $2c376,A6 / jsr $826 (init_screen_ptrs: screen bases from $70000.. into 0/4/8(A6),
work buffers $54000..$66000) / bsr $67a8 install_vectors / bra $b7e`. $81a/$81e (`bra $800`, `bsr $680a`, Pterm0) are
the exit path.

`$b7e main_start`: mode 2, init calls ($100e2, $1050e, $1ed6e, $10544, $a2b8 copy screen, $bd9a, $100c6, $308a,
`$101c6 title_screen`, `$d78e` file loads), defaults, `$c9e`, then `jsr $10840 options_screen`. The nominal top loop
`$c60: bsr $c6a (restart setup) / $c64: bsr $14ce / bra $c60` sits below that, but `options_screen` never returns:
it ends `jmp $2d74 team_screen`, and every screen afterwards is reached by `jmp`. The live stack bottom is the
return address $c58 of `jsr $10840` (stack dumps in `repl/bt2.txt`, `repl/stk1.txt`), so the game runs as a jmp-linked
screen graph one frame above the startup code.

There is no single per-frame main loop. Each menu screen is: set icon table 84(A6) (and/or rect table 80(A6)), draw,
`$bd9a` flip, `$bcfe wait_click_or_help_key` (spins on $24fba; scancode $23 calls $11916), `$bcaa hit_test_icons`
(32x32 icons, entries `id?,icon,x,y`) or `$bc4a hit_test_rects` (`x0,y0,x1,y1,flag`) -> index in 88(A6), then a
longword action table: bit 31 set = `jsr` and redisplay, clear = `jmp` to another screen. Idle menu screens run only
the VBL work (census: nothing but the 9 VBL/timer routines over 1.2M steps on d_team, d_options, d_title, s_click1).

Two screens have a real frame loop:

**Map screen** `$14ce map_screen` (loads numbers 28/29/27, files 38.2/39.2/37.2; mode 1; copies the height grid
$4a104 -> $60000 and subdivides it once to draw the map, `terrain.md` section 5). Loop at $1546:
`bsr $2122 / bsr $18e8 / jsr $bdec flip / bsr $6840 wait_vbl`, then click dispatch via rects $23fc8 -> table $24fc8
(`jmp`). `hits_s_map.log` (s_map.snap, 1.2M steps): once per VBL = 100: $1546 $18e8 $19bc $1b22 $1dba $2122 $217a
$2786 $6840 $bdec $df48; 200: $2258 $2272 $308a $867a $86f4 $a99c $a9aa $aa3e; 1300: $a36c $ab40.
"CLOSE MAP" (rect 3) is $1784: restore $62b8, `rts` (the map is entered by `jsr` from other screens).

**3D travel** `$12514 travel_3d_session` (saves $62b8, sets mode 2, init, `jsr $1498a`, teardown, restore $62b8).
`$1498a travel_3d_main`: setup, then loop `$14ac0: bsr $14e00 / test $14dfc,$12d76,$14dfe,$14ef6 / bra`.
`$14e00 travel_3d_frame` fan-out, in call order:

| addr | body (first lines) | hits / 1.2M |
|---|---|---|
| $14efc | `jsr $12ac6 read_key_ascii`; 'X' sets exit $14ef6, 'M' sets $14dfe, 'P' pauses (sets $6a32 sfx mute, waits) | 5 |
| $12e9c | `jsr` through pointer $12d5e (per-vehicle control handler), then $12f9e | 5 |
| $14fac | countdown $15118, `mulu/divu` on heading $12c98 | 5 |
| $129d2 | ten `jsr`s $aff2..$b4bc (instrument panel, inferred) | 5 |
| $1580e | screen-row fill from $171f4/$171f6 (sky/ground, inferred) | 5 |
| $19c7a | horizon offsets from $12c68/$12c6a | 5 |
| $1d77a | sine table $1c6bc indexed by heading $12c98, `muls` (view rotation, inferred) | 5 |
| $202c6, $200e8, $1ffe0, $1fa0a | object slots at $1ce02 / $1cdd6 / $1cdaa, gated on flags | 5 each |
| $20d52 run_object_slots | 4 slots of 44 bytes at $1cd7e, `jsr` handler at 40(A5) when 38(A5) > 0 | 5 |
| $1d0a0 | from $70010 table, `divs` by $12c5a | 5 |
| $18304 | landscape render calls $16d9c, $16cf6, $17f20, $170e6 on buffers $12ce6..$12cf2 | 5 |
| $19ce2 | draw list walk from $18bda (calls $1d5a6 per entry) | 5 |
| $1bbe6 apply_mask_overlay | AND/OR mask list $1bbde onto $1bbe2 (goggle frame from $74000, set at $125aa) | 5 |
| $14e98, $bd9a | message countdown $14ee4, triple-buffer flip | 5 |

Command: `repl/hits_3dframe.txt` on `s_3d_6.snap` -> `hits_3dframe.log`: 5 frames in 1.2M steps (one frame per about 20 emulator VBLs). Inner work per 1.2M: $19f20 1959, $19ed4 1959, $17fa0 1550, $1b0e4 1210, $17444 750, $17bf6 700,
$1d41e 605, $19d6a 501, $18bba 450, $12276/$1dd14/$1d5a6 27 (`hits_s_3d_6.log`, 186 routines non-zero).
`$122f0 checksum_check`: looks up A4 in a 30-entry table $123ac (start, end, sum), sums with $12276, and on a
mismatch loops forever cycling $ff8240: a code checksum (inferred protection; that table is one of the regions the crack rewrote, section 5).

## 4. Screen dispatch

| screen | entry | how reached | icons -> actions |
|---|---|---|---|
| title "press any key" | $101c6 | `jsr` from $bc4 | waits for any scancode in $2c324, `addq.l #1,$4ba` each pass (PC $10234 in d_title.snap) |
| Game Options | $10840 | `jsr` from $c52 / $c96, `jmp` from $2e6e | icons $25094 -> $250d2 (6 x `jsr` toggles $10944..$10996); rect $250c6 (78,134..243,197) -> seed RNG from pointer ($d598), $bfc8, $ee30, copy options $24b7e.. -> $2c176.., $675e, `jmp $2d74` |
| The Team | $2d74 | options, bio, decisions | icons $23e10 -> $242f8; portrait rects $240f8 -> sets 96(A6) (current character), `jmp $30a0` |
| character bio | $30a0 | team portrait | icons $23e5c -> $24214: map `jsr $14ce`, face `jmp $310c`, team `jmp $2d74`, $3054, $3024, SOS `jmp $5784` |
| Decisions | $310c | bio face icon | icons $24534 -> $2422c: map `jsr $14ce`, bio `jmp $30a0`, team `jmp $2d74`, $3dd2 (snipe), $3d86 (ski), $5062 |
| map | $14ce | `jsr` from bio/decisions/other screens | rects $23fc8 -> $24fc8 (`jmp`, 23 entries) |
| 3D travel | $12514 | `$3d86` ($24482=2, $24f3c=4, `$12d76=$12d7a`) and `$3dd2` ($24482=0, `$12d76=$12e28`) | in-loop keys only |

Proven by driving: d_team -> portrait click -> bio (`repl/click1.txt`, s_click1.png); bio map icon -> map (`repl/click_map.txt`,
from s_run.snap; s_map.png); bio face icon -> Decisions (`repl/click_view.txt`, s_view.png); Decisions icon 4 -> $3d86 ->
$12514 (`repl/click_3d2.txt`: $bcaa 1, $31d0 1, $3d86 1, $3e38 1, $12514 1 in the 40000 steps after the click) -> goggle
3D view after ~30M steps (`repl/click_3d3.txt`, s_3d_6.png). All 16 icon/action tables are in `tables/action_tables.txt` (pairing
of a few `jsr`-screens to their tables is from the nearest preceding `lea`; the $31f6 row there is wrong, the correct
Decisions table above was read from s_view.snap). All `jmp (An)`/`jsr (An)` sites: `tables/dispatch_sites.txt` (47).
There is no single screen-state variable: the current screen is the code position; 108(A6) is the palette/pointer
index passed to `$bf0c set_palette_and_pointer`, not a screen number.

## 5. Disk loader (the cracked build)

The game loads with its own FDC code, no GEMDOS (`repl/loads_hits.txt` over the 4M steps after the ski click: TOS GEMDOS
$fc4cee 0 hits).

- Call convention: file number in 348(A6) (word), destination in 336(A6), `jsr $10cd2` -> `jmp $500`.
- `$500 res_load_numbered_file` (resident low RAM, below the load base): points $114/$70/$68 at an `rte` stub $5dc
  (555 hits during the loads: timer C and VBL are swallowed), builds the name "NN.2" at $5d6 from the number in
  348(A6), size from a 10-byte table entry -> $2db02. The longword $258a2 is the original loader's table pointer:
  when it is not $258a6 the number gets +10 and the entry comes from the table at $258a8. It is 0 on `cold20.snap`
  and $2590c on every milestone from `d_title` to `d_ski`, so every load during play opens number+10 (number $1b
  opens `37.2`: the name buffer $5d6 reads "37.2" at `$19962`, and the 10,000 bytes at $4a104 equal depacked 37.2). Calls
  `$10e1c fat_load_file`, then `$5ee`: if the destination starts `LSD!` it moves the data down 128 bytes and depacks in
  place with `$642 res_lsd_depack` (the backward bit-stream depacker; `cmpi.l #$4c534421,(A1)` at $5ee). It then
  depacks two fixed blobs, $77d70 -> $215e4 and $7fd80 -> $21be4, and restores the vectors.
- `$10e1c` FAT12 loader: `$10e40` reads the boot sector (logical 0) and parses the BPB into $215e4..$215f0,
  `$10ebe` makes an upper-case 8.3 name at $21612, `$10f1a` scans the root directory, then follows the 12-bit FAT
  ($21a1e) cluster by cluster, copying 1 KB clusters from the sector buffer $2161e to the destination.
  `$11066 fdc_read_sectors` (logical sector -> track/side/sector via $215e4/$215e6, side select via YM port A
  $11184/$1119e/$111b6), `$110ba fdc_read_sector` (DMA address $ff8609/b/d, command $80, poll GPIP5 at $fa01,
  retries), `$11128 fdc_seek` (command $13).
- Census (`loads_hits.log`): $500 4, $10e1c 4, $10e40 4, $10f1a 4, $11066 27, $110ba 82, $11128 5, $5ee 4, $642 12.
- Breakpoint log (`repl/loads_ski.txt` -> `loads_ski.log`) on the ski click, number in 348(A6) -> 336(A6) at each
  `$500`, with the file it opens: 34 (44.2) -> $4f1e0 (from $d910), 35 (45.2) -> $53254 ($d946), 37 (47.2) -> $7a000
  ($1bc6c), 27 (37.2) -> $4a104 ($19cc8). At `$19962` the RAM at $4f1e0, $53254 and $4a104 equals depacked 44.2, 45.2
  and 37.2 byte for byte; $7a000 has been overwritten by then (47.2 there is inferred).
- Static map from the listing (`tables/loadcalls.txt`, which also lists numbers; add 10 for the file opened in play):
  47 -> [$2c35e] (=$404c4), 30 -> $4f1e0, 31/33 -> packed after it, 28 -> $4f1e0, 27 -> $4a104 (the island's
  50 x 50 height grid, which the map screen copies to $60000 at $15d6 and subdivides: `terrain.md`), 29,
  34 -> $4f1e0, 35, 42 -> $4f1e0, 45 -> $404c4, 49 -> 8(A6) (a screen buffer), 48 -> $2a14c,
  06 -> $3167c, 03 -> $4c878, 01/02/04/05 computed, plus five computed numbers ($da92, $daba, $1b9d8, $1ba40,
  $1bc66). The two runtime rows with a static number (34, 27) match. Loads made before the pointer switches open the
  plain number: $4c878 holds 03.2 whole, and 01/04/05.2 sit whole at $4d530/$4d6c8/$4dd98
  (`tools/find_files_in_ram.py` on the `$19962` snapshot).

The loader is a crack patch, not Rainbird's. The depacked file `unpacked/1.1` (`mw_1_1_at800.img` = 1.1's text
placed at $800) differs from RAM in 2512 bytes (comparison against d_team.snap), and the main blocks are code:
- $10cd2: the file holds the original load routine (`movem.l / move.w $62b8,-(A7)`); RAM has `jmp $500`.
- $10e1d..$111ce: the original reads a 10-byte-per-file sector table at $258a2 (start, count, size) with its own track
  loader. RAM holds the FAT12 loader above.
- $11c7e..$11e06, $ffb8.., $1001a.., $1033a..: patched routines that select a drive through YM port A
  (`move.l #$0e000500,$8800.w`) and touch $8606.w; callers $ffc2, $10024, $1004c, $102ec, $1033c. Role not decoded
  (inferred: save-disk or protection path).
- $12391..$12513: the checksum table used by `$122f0`, rewritten to match the patched code (inferred).
The patcher is not identified (inferred: PACT.PRG after it loads 1.1). The remaining diff blocks in the data area
($23738.., $240fb.., $24f41.., ...) are live variables.

## Open

- The writer of the junk MFP vectors $100..$13c, and which code clears the 80(A6)/84(A6) tables.
- Roles of the map loop's per-frame routines ($18e8, $2122, $1b22 ...) and of the 3D inner routines ($19f20, $17fa0, $1b0e4).
- The computed file numbers (01, 02, 04, 05.2 and the five unnamed calls) need a `bp 500` log in the screens that use them.
- Decisions icons 3 ($3dd2) and 5 ($5062) and the bio SOS icon were not driven.
