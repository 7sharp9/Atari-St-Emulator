# Blog: handoff

Updated 2026-11-16 by the session that ended at commit `b0301ef`.

The blog workstream curates and extends posts for 7sharp9.dev from the game research. Each game is
reversed in its own workstream; this one reads their docs, checks the claims a post would rest on
(on real Hatari where the claim depends on our emulator), and feeds corrections back to the game
docs. A fix to a game doc is committed as that game's commit; the game's own handoff is not edited
here. Dave's direction (2026-11-11): posts explain algorithms the games use and their relevance
today, not emulator bug fixes. Dave (2026-11-12): one infographic per interesting algorithm, drawn from the proven
model, as post material (`IDEAS.md` entry 9). Dave (2026-11-15): the topic docs are compressed knowledge that game
sessions build up; they are not rewritten for newcomers. Clarity is applied where the knowledge is published
(figures, posts, README openings), by the rules in `reversing/WRITING.md`, every edit checked with
`tools/docguard.py`. The post shape that fits the blog: a game's algorithm ported to idiomatic F#, proven against the
game, ending in a visual the game could not make (the Midwinter and Paint It Black drafts).

**Dave (2026-11-16): the next post is Archipelagos' island generator**, chosen over Midwinter, Populous, Cadaver,
PowerMonger, Captive, Super Sprint and Captain Blood; he asked for the picture islands to be modelled before the port.

## Resume point

- Last commit of this workstream: `b0301ef` (Archipelagos census checked live, from the session
  [arch-census-live]; `ff0d2d6` picture islands and `df6ece1` model census before it). Master is 4 ahead of origin
  (with `af8afaa`, CLAUDE.md), the blog repo 3 (`add1f32`, `0486cc2`, `53a781e`, IDEAS.md only); neither pushed.
- Working data (repo scratchpad, gitignored): `scratchpad/archipelagos/` (`tmb58.st`, `n0`/`n2`/`m2` snapshots,
  `isl/`, `gen/`, `pic/`, `census/census.json`, `census_live/`); rebuild recipes in `scratchpad/ANCHORS.md`
  (Archipelagos row) and `reversing/archipelagos/README.md` "Running it". The census: `py/census.py` (6 min, 10 cores).
- Earlier data as before: Captive `scratchpad/captive/infographics/data/route.json`; Midwinter mockups
  `scratchpad/midwinter/mockup/`.
- Uncommitted work left behind: none.

## Proven so far

- Archipelagos generator (`reversing/archipelagos/README.md`, "The island generator", "Picture islands", "Island
  number", "Over all island numbers"; gate `archipelagos/islands`, 2/2 PASS 136 s):
  - Islands 5, 10, ..., 100 are 128 x 128 one-bit pictures from the disk (game track T = cylinder T side 1);
    65536/65536 on 15, 25, 85, buffer 2048/2048 (`py/gate_pictures.py`). The other 80 of the first hundred are
    hand-set parameter blocks for the same stamp generator (21/21 words on 6 and 99). Figure `picture_islands.png`.
  - Model census N = 1..9,999 (`py/census.py`), checked live on 42 islands, all 65536/65536 (`py/gate_census_live.py`):
    no builder write outside the map (11/11 worst cases; the edge-forced control writes outside, then double bus
    faults); 64 parameter sets above 100 (low-byte draws, N and N+64 share 20/21 words, maps differ); land and
    pieces flat after island 100 (about 7,300 land cells, 27 pieces).
- Earlier: Captive keys (`captive/mapgen.md`, `infographic_keys.png`); Midwinter roughness overflow
  (`midwinter/terrain.md` section 1); Carrier Command figures; Midwinter port 70000/70000; PowerMonger LLM commander
  8/30 vs 7/30; Populous swamp edge 75.9% Hatari vs 70.0% ours.

## Running

Nothing running. The session [arch-census-live] (`local_04c61e87-32f8-414a-a140-7e619ff29eec`) is idle with its
work committed; archive it on Dave's yes.

## Open, in priority order

1. **Archipelagos post: the F# port.** Port `py/island_model.py` (procedural path and picture path) and
   `py/island_params.py` to idiomatic F# (an island as a function of N plus the disk). Gate: 65536/65536 on the
   committed captures (`isl/`, `gen/`, `pic/`, `census_live/`) and the BUG=1 control lower. The out-of-map
   offsets need no emulation (none reachable, README census), but say so in the port.
2. **Post figures:** an atlas of islands (a sheet of many N, the visual the game cannot make), a stamp-by-stamp build
   strip, `picture_islands.png`, and N vs N+64 side by side. Generate from the F# port.
3. **Prior art, rest of it:** Pera Putnik's ST archive page (`atari.8bitchip.info/ASTGA/A/archipel.php`), the Hall of
   Light entry, and whether the 16Bit Pocket Power disk's "commented assembler source" (Atarimania trivia) has been
   published. MobyGames (403) and TCRF (DNS) could not be read by the web-fetch agent; MobyGames' "first 100
   hand-designed" is known only from a search snippet.
4. **Not established, limit what the post may claim:** the 9,999 cap is not read from code; how a played map screen
   sets N; the 3D land view (the map is a 2D mask); who the portrait on island 55 is.
5. Carried: Midwinter (draft line 50 vs `terrain.md` section 1), Captive (emulator-check sampled bases), Carrier
   Command series (set aside, `git show e97590c:M68000/sessions/blog.md`), the unsourced figure and README gaps,
   `gen_takeoff.py` cache, Black Tiger stale claim.

## Known traps

- A web-fetch agent briefed with a page cap reads only what it is pointed at: name the bugs and release pages.
  MobyGames answers 403 and new.tcrf.net fails DNS for it; use another source.
- The local Hugo is v0.148.1; the site needs 0.162 or later, so `hugo --buildDrafts` fails.
- `docguard` reports a token's delta, not its meaning.
- Three PowerMonger figures have no generator (the SVG is the source); PNGs: `rsvg-convert -b white -w 1800`.
- `tools/gates.py run <game> -k <gate>` runs one gate; `run <game>/<gate>` fails.
- `census.py`'s worker pool is forked before the summary: state for the workers goes in function arguments, not
  `os.environ` set afterwards.

## Waiting on Dave

- His Midwinter draft line 50 ("peaks are rougher than lowland"); true only to average height 3,470.
- Keep or redo the Captive keys figure; whether the Captive post is dropped.
- Carried: the Carrier Command series, "proven" vs "observed" in Crude Buster and Final Fight, the Lemmings artifact
  republish, the Black Tiger stale claim, upgrading Hugo, pushing master and the blog repo.

## Next session

`/resume blog`. Archipelagos post, Open 1: read `reversing/archipelagos/README.md` "The island generator" through
"Over all island numbers" and `py/island_model.py`, then port to F# (an `.fsx` under `reversing/archipelagos/fs/` as
Midwinter's `fs/` does) gated 65536/65536 on the committed captures. Then the atlas figure (Open 2) and the
remaining prior-art pages (Open 3) before drafting with the `dave-post` skill.
