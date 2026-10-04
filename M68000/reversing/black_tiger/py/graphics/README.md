# py/graphics: Black Tiger graphics decoders and gates

Run from anywhere (`source M68000/.venv/bin/activate`). Paths: repo root from `__file__` (override
`M68000_ROOT`), inputs from `$BT_WORK` (default `M68000/scratchpad/black_tiger`), outputs under
`$BT_WORK/agents/graphics/` (`snaps/`, `boss/`, `screens/`, `shop/`, `png/`, `gates/`). `bt_common.py` holds the shared
helpers. The generators run the existing DLL through `drive.py` (`ATARI_NOTRACE=1`, no build). `mk_boss_snaps.py` and
`mk_screen_snaps.py` need the systems agent's `agents/systems/lvl1..7.snap` and `title_screen.snap`.

Order for a clean tree: generators, then atlases, then gates, then `proof_images.py`, `build_images.py`.

| script | what it does / proves | expected output | runtime |
|---|---|---|---|
| `mk_level_snaps.py` | one page-flip-entry snapshot per level `L<n>a.snap` (labelled poke: jump to `$c50e` with `$17846` = n) | `level n ok` x 8 | 3 s |
| `mk_input_snaps.py` | `atk0..7` (fire held), `walk0..9` (right held) from `play_start.snap` | `atk 8`, `walk 10` | 4 s |
| `mk_walk_snaps.py` | `W<n>_0..2`: three snapshots per level while walking right | 8 x `snapshots 3` | 4 s |
| `mk_boss_snaps.py [--right] [k..]` | boss snapshots `B<k>_<i>` (hero left of the boss) / `BR<k>_<i>` (hero right). LABELLED POKES: hero onto the exit cell, then beside the boss | `boss at (x, y) snapshots 8` per level | 20 s |
| `mk_screen_snaps.py` | intro (natural), ending (boss slot cleared: labelled poke), shop (hero onto the shop man: labelled poke) | `intro 4`, `ending 6`, `shop 1` | 5 s |
| `tiles.py atlas / level / check <snap> --draw` | tileset atlases, whole-level renders; tile render vs the draw buffer at the live scroll | `check`: 94.5..96.3% of the 40960 playfield pixels per snapshot (8 levels, 8 snapshots of L2a..) | 1 s per snapshot |
| `tiles_residual.py` | where the remaining pixels are (HUD rows + actor boxes) | `TOTAL differing 101104, outside masks 14742`; 3 of 51 snapshots have 0 outside | 60 s |
| `sprites_check.py` | every on-screen actor slid over the draw buffer (file banks, frame and frame-1, both facings, +-10 px) | `actors tested 97, exact 30` | 90 s |
| `hero_check.py` | which of the 23 BTMAN frames explains the hero rectangle | 4 snapshots at 100.0% (attack frames), rest 69-93% (flail drawn over) | 40 s |
| `boss_check.py` | boss and escort sprites with banks read from RAM (BTA/BTB loaded by the game) | `132 instances, exact 71` (table in `graphics.md` 5.4) | 15 s |
| `pics_check.py` | BTCLIPS / BTOBJ pictures found on live screens | 10 pictures at 100% (BTCLIPS 4,5,9,15,16,20; BTOBJ 1,3,5,16) | 40 s |
| `shop_check.py` | shop screen: palette `$172d6`, BTCLIPS 17 at (32,0), item icons | `icons total 1253/1253`, scene 17450/17920 outside the speech box | 3 s |
| `screens_check.py` | intro (BT001 + story text), ending (BT5 + 4 text pages) | `64000/64000`, 8/8 story lines, `10752/10752` x 5, text 6/6 3/3 3/3 2/2 | 20 s |
| `sprite_atlas.py`, `boss_atlas.py`, `weapons.py`, `pics_atlas.py` | bank/picture atlases in `png/` | atlases | 5 s |
| `sprites.py`, `ram_actors.py`, `pics.py`, `text.py`, `drive.py` | libraries (bank parser and frame decoder; RAM-bank actor matcher; picture collection reader; fn11 text renderer; REPL runner) | | |
| `proof_images.py`, `build_images.py` | side-by-side proof images; copy the committed images to `reversing/black_tiger/img/graphics/` as palette PNGs (asserts the quantisation is exact) | `TOTAL 1346 KB` | 20 s |
