# Blog: handoff

Updated 2026-11-15 by the session that ended at commit `85e6c1b`.

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

## Resume point

- Last commit of this workstream: `85e6c1b` (Midwinter terrain gate declares its inputs). This session explored post
  candidates other than Carrier Command; nothing was chosen. Master is 11 commits ahead of origin, the blog repo 3
  (`add1f32`, `0486cc2`, `53a781e`, IDEAS.md only); neither pushed.
- Working data (repo scratchpad, gitignored): `scratchpad/captive/infographics/data/route.json` + `route.txt`
  (rebuild: `py/mapgen/full/route.py 0 100 -j 10 --json <file>`, about 15 min on 10 cores);
  `scratchpad/midwinter/mockup/` (`Terrain.fsx` modern model, `IslandIdioms.fsx`, `deep.fsx <height>`,
  `precision.fsx <level> <cells> <height>`, `compare.py`, `dronecmp.fsx`, PNGs); needs `scratchpad/midwinter/terrain/gate/`
  (from `py/terrain/gate_terrain.py`). Carrier PNGs as before (`py/infographics/README.md`).
- Blog repo: Midwinter post (`draft: true`) and Paint It Black (10 TODOs) wait on Dave's writing.
- Uncommitted work left behind: none (the mockups are scratchpad exploration, not cited by any doc except IDEAS.md).

## Proven so far

- Captive keys (`captive/mapgen.md` "Locks and keys", "Can such a base be finished?", "Routes"; figure
  `infographic_keys.png`, `py/infographics/keys.facts.md`): the sealed key is Captive 1.0's known bug
  (captive.atari.org Bugs, fixed in 1.2 by a walk-through wall); on our (1.0-behaving) model 38 of 1,100 bases in
  missions 1..100 unfinishable from the clipboards (not 27: a cascade through panels and clipboards behind sealed
  doors), 1,100 with codes read off the panels; dig-order plan 1.53x the A* walk (median, 1,057 bases). Model only;
  Phoopel is the only emulator-checked base.
- Midwinter roughness overflow (`midwinter/terrain.md` section 1, `fs/wraps.fsx`): from average height 3,471 the 16-bit
  roughness wraps, the highest ground is smoother; 107,439 of 2,560,000 finest cells. Of `mid`'s 16-bit behaviours
  three shape the island, two never fire.
- Midwinter modern model (`scratchpad/midwinter/mockup/Terrain.fsx`, `check_terrain.fsx`): equal to `Island.fsx` on
  every cell of every level; lazy tiles build 121 for the game's window. Exploration, not committed.
- Earlier: Carrier Command figures (`carriercommand/py/infographics/README.md`); Midwinter port 70000/70000;
  PowerMonger LLM commander 8/30 vs 7/30; Populous swamp edge 75.9% Hatari vs 70.0% ours.

## Running

Nothing running.

## Open, in priority order

1. **Choose the next post.** Candidates measured against the blog's shape: Midwinter (already drafted; possible new
   sections from the mockups: the roughness overflow, the modern model, subdividing past level 5 with wider arithmetic,
   `drone_compare.png`); Populous "God Only Knows" (fits best after Midwinter; prior-art check not done); Cadaver's
   script language as a computation expression (`IDEAS.md` 2; prior art unchecked); PowerMonger symbol table (a method
   post, no algorithm; no prior art found in three searches); Captive (weak: the bug is documented). Settle by Dave's
   choice after a prior-art read of each fan site (bugs and release pages included).
2. **Captive, if pursued:** emulator-check a sample of the 38 bases (at least 2 of the 11 cascade ones), as
   `py/phoopel/enter13.repl`; the strict `<` key rule in the model (expect 0 sealed, 0 unfinishable); whether the
   site's 4,380 matches our census (its range is unstated); this disk's version string (inferred 1.0).
3. **Carrier Command** (Dave: set aside 2026-11-15): series proposal, survey candidates and doc problems as in
   `e97590c`'s session file text (`git show e97590c:M68000/sessions/blog.md`).
4. Unsourced figure and README gaps (BSP "clipping routine", octdist "free island", PowerMonger state `$9`, Captive
   universe object 13 vs 14, Final Fight "state 2", Populous "papal magnets", premises for Captain Blood and
   Archipelagos).
5. `gen_takeoff.py` has no cache; stale emulator claims in `black_tiger/secrets.md:48` and `IDEAS.md` line 18 (fixed
   in `5636dc5`), fix once Dave agrees; diary text in deep README sections (each game's next session).

## Known traps

- A web-fetch agent briefed with a page cap reads only what it is pointed at: the captive.atari.org Bugs page was
  missed the first time. Name the bugs and release pages.
- `route.py`'s A* over every lock blew up (11 bases unfinished in 94 min); it is restricted to the needed locks, and a
  `Pool.map` that lost a worker hung with no output: it now streams with `imap_unordered` and saves rows before the
  summary.
- The local Hugo is v0.148.1; the site needs 0.162 or later, so `hugo --buildDrafts` fails.
- `docguard` reports a token's delta, not its meaning: a gained number in a new README opening is usually a fact
  copied from lower in the doc.
- Three PowerMonger figures have no generator (the SVG is the source); PNGs: `rsvg-convert -b white -w 1800`.
- `tools/gates.py run <game> -k <gate>` runs one gate; `run <game>/<gate>` fails.

## Waiting on Dave

- Which post next (Open 1).
- His Midwinter draft line 50 says "peaks are rougher than lowland"; true only to average height 3,470
  (`terrain.md` section 1). His text to change.
- Keep the Captive keys figure in its box-art style, or redo it in the house style; whether the Captive post is
  dropped.
- Carried: the Carrier Command series, the Open 4 gaps, "proven" vs "observed" in Crude Buster and Final Fight, the
  Lemmings artifact republish, the Black Tiger stale claim, upgrading Hugo.

## Next session

`/resume blog`. Ask Dave which post (Open 1). Before recommending one, read his latest posts' structure and the
candidate's fan sites (bugs and release pages too). For Midwinter, the mockups in `scratchpad/midwinter/mockup/` are
the starting point (re-run `check_terrain.fsx` first). For Populous, start with the prior-art check, then port the
generator to F# against `populous/terrain.md`.
