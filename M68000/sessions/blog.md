# Blog: handoff

Updated 2026-11-15 by the session that ended at commit `f6ac961`.

The blog workstream curates and extends posts for 7sharp9.dev from the game research. Each game is
reversed in its own workstream; this one reads their docs, checks the claims a post would rest on
(on real Hatari where the claim depends on our emulator), and feeds corrections back to the game
docs. A fix to a game doc is committed as that game's commit; the game's own handoff is not edited
here. Dave's direction (2026-11-11): posts explain algorithms the games use and their relevance
today, not emulator bug fixes. Dave (2026-11-12): one infographic per interesting algorithm, drawn from the proven
model, as post material (`IDEAS.md` entry 9). Dave (2026-11-15): the topic docs are compressed knowledge that game
sessions build up; they are not rewritten for newcomers. Clarity is applied where the knowledge is published
(figures, posts, README openings), by the rules in `reversing/WRITING.md`, every edit checked with
`tools/docguard.py`.

## Resume point

- Last commit of this workstream: `f6ac961` (clarity pass on all 25 infographics), after `d3b204a` (glossary,
  writing rules, README openings) and `016f784` (`tools/docguard.py`). Master was level with origin at resume.
- Infographics: Carrier Command PNGs in `M68000/scratchpad/carrier/infographics/` (gitignored; rebuild with
  `reversing/carriercommand/py/infographics/README.md`); every other figure's PNG/HTML is committed next to its
  game. Not yet copied into the blog repo. The rebuilt Lemmings page is only in
  `scratchpad/lemmings/info/inside_lemmings.html`; its published artifact still shows the old text.
- Blog repo `~/GitHub/7sharp9.github.io`: clean, level with its remote. The Midwinter post (`draft: true`) and Paint
  It Black (10 TODOs) wait on Dave's writing. `IDEAS.md` is tracked now (Dave's `2342008`).
- Uncommitted work left behind: none.

## Proven so far

- Clarity pass: 25 figures and 19 READMEs, `docguard` on every changed file; every loss is an intended removal
  (pass numbers, citations moved to Sources lines) or one of the corrections in `f6ac961`'s message. The six Design
  digests are byte-identical. `tools/tests/docguard_check.sh` 7/7.
- Carrier Command figures, each from emulator-confirmed data (`py/infographics/README.md`): BSP draw order 1264/1264
  (`render.md` 4); routing matrix 41/41 and 129/129, hops 14/14 twice (`economy.md` 3-4); span filler 2183/2183
  (`render.md` 5); octagonal distance 11.8% worst, picks 11/11 (`ai.md` 2); take-off 43/43 (`vehicles.md` 5); depack
  margin 219 (`packer.md`); arctangent error 27 units (`vehicles.md` 2).
- Midwinter post: F# port 70000/70000 cells, post-passes 10000/10000 (`terrain.md` 1, 6). Ski run cut on purpose
  (2026-11-11): nearly all of it was ours over smooth slope.
- Earlier: PowerMonger LLM commander no better than random (Haiku 8/30 vs placebo 7/30); Paint It Black's ~55
  claims checked; Populous swamp edge on Hatari 75.9% vs ours 70.0% (`populous/systems.md` 1.3).

## Running

Nothing running.

## Open, in priority order

1. **Carrier Command: which figures become a post or series** (Dave's call); then copy the chosen PNGs into
   `static/images/posts/carriercommand/` and draft with `dave-post`, unpacking each figure's section by
   `WRITING.md`. "Today's relevance" per figure needs a cited source before naming any modern use.
2. **Unsourced figure and README gaps** (each settled by reading the named section, or by Dave): BSP "clipping
   routine" (`render.md` 4), octdist "free island" (`economy.md` 1/3), PowerMonger state `$9` "invent" vs "decide
   now" (`strategy.md`), Captive universe object 13 vs 14 (`world.md` 1), Final Fight "state 2" (`player.md`),
   Populous "papal magnets" (`mechanics.md`); premises for Captain Blood and Archipelagos, genre words for Final
   Fight and Crude Buster.
3. **`gen_takeoff.py` has no cache**: add a JSON cache like `gen_span.py`'s `span_emu.json` so a text edit does not
   run `stserver`.
4. **Midwinter post and Paint It Black: Dave's writing**, then render-check every changed passage against its doc.
5. **Stale claims, not fixed:** `reversing/black_tiger/secrets.md:48` and `IDEAS.md` line 18 say the emulator does
   not keep the 6850's last byte (fixed in `5636dc5`); fix once Dave agrees.
6. **Untested effects** (carriercommand workstream if pursued): whether `$1817e`'s stray write changes the enemy's
   island choice; the octdist "3 of 11 picks change with true distance" counterfactual.
7. Diary text left in deep README sections (Super Sprint Timer B, A_013 pool, cadaver "Next steps", impossamole
   table rows); belongs to each game's next session.

## Known traps

- The local Hugo is v0.148.1; the site needs 0.162 or later, so `hugo --buildDrafts` fails.
- `docguard` reports a token's delta, not its meaning: a gained number in a new README opening is usually a fact
  copied from lower in the doc; check it is there before accepting.
- Three PowerMonger figures (`clock_stall`, `cmdai_decision`, `order_pipeline`) have no generator: the SVG is the
  source. PNGs: `rsvg-convert -b white -w 1800`.
- `gen_routing.py drive` takes about 5 minutes; `gen_takeoff.py` always drives `stserver` from `c_s30`.
- `gen_depack.py` panel F needs lz4, gzip, zstd and xz on PATH.
- In zsh, a multi-path `$VAR` passed to `git commit --` needs `${=VAR}` (CLAUDE.md "zsh").

## Waiting on Dave

- Which Carrier Command figures to publish, as one post or a series (Open 1).
- The gaps in Open 2, and whether to keep the two general-knowledge glosses (entropy coding, Bellman-Ford
  relaxation) flagged in the Carrier Command facts files.
- Crude Buster and Final Fight use "proven" for rule-against-game counts where `WRITING.md` would say observed;
  relabel or keep.
- Republish the Lemmings artifact from the rebuilt page; the Black Tiger stale-claim fix; upgrading Hugo.

## Next session

`/resume blog`. Ask Dave which Carrier Command figures go into a post, copy those PNGs into the blog repo and scaffold
it with `dave-post`, writing each section by `reversing/WRITING.md` and quoting numbers from the figure's
`.facts.md`. Run `tools/docguard.py` on any doc or figure touched. If Dave has written into the Midwinter post
instead, re-check every changed passage against `terrain.md`.
