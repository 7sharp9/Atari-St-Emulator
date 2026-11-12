# Blog: handoff

Updated 2026-11-12 by the session that ended at commit `a2afe3c`.

The blog workstream curates and extends posts for 7sharp9.dev from the game research. Each game is
reversed in its own workstream; this one reads their docs, checks the claims a post would rest on
(on real Hatari where the claim depends on our emulator), and feeds corrections back to the game
docs. A fix to a game doc is committed as that game's commit; the game's own handoff is not edited
here. Dave's direction (2026-11-11): posts explain algorithms the games use and their relevance
today, not emulator bug fixes. Dave (2026-11-12): one infographic per interesting algorithm, drawn from the proven
model, as post material (`IDEAS.md` entry 9).

## Resume point

- Last commit of this workstream: `a2afe3c` (Carrier Command's seven infographics and the doc corrections they
  forced; the arctangent one is `379df7e`). Master is 21 commits ahead of origin with this handoff: not pushed.
- Infographics: generators and fact sheets in `M68000/reversing/carriercommand/py/infographics/` (README table:
  script, doc section, evidence each re-runs); PNGs in `M68000/scratchpad/carrier/infographics/` (gitignored;
  rebuild with the README's commands). Not yet copied into the blog repo.
- Blog repo `~/GitHub/7sharp9.github.io`: `2fa425c` holds the Midwinter post draft (`draft: true`), not pushed.
  Midwinter working data: `M68000/scratchpad/midwinter/terrain/` (rebuild: `reversing/midwinter/fs/terrain.fsx`
  header).
- Uncommitted work left behind in the blog repo, all deliberate:
  - `content/Programming/2026-09-22-paint-it-black.md` and `static/images/posts/powermonger/walk_*.gif`: Paint
    It Black's fact-check fixes and figures, waiting on Dave's writing (GIF recipe:
    `git show 41734eb:M68000/sessions/blog.md`).
  - `IDEAS.md` untracked by Dave's decision (post notes stay private); entry 9 now lists all seven Carrier
    Command figures. `ideas/` is the Cadaver session's.

## Proven so far

- Carrier Command figures, each from emulator-confirmed data (`py/infographics/README.md`): BSP draw order matches
  the game 1264/1264 draws of 6 models (`render.md` 4); routing matrix 41/41 and 129/129 dumps, hops 14/14 twice
  under poked ownership (`economy.md` 3-4); span filler 2183/2183 rows over all 64 codes (`render.md` 5);
  octagonal distance 11.8% worst, picks 11/11 (`ai.md` 2); take-off 43 ticks, 43/43 (`vehicles.md` 5); depack
  binding margin 219 (`packer.md`); arctangent error 27 units = 13.7 table + 16 truncation (`vehicles.md` 2).
- Doc corrections those forced, all in `a2afe3c`/`379df7e`: the -32768 atan bug (up to 45 degrees, either input),
  take-off 43 ticks, depack margin and start gap, 11 distinct AI decisions, octagon inlined in four places, two
  inferred game bugs (`$1817e` stray matrix write, `$22150` pool-1 cap store).
- Midwinter post: F# port 70000/70000 cells, post-passes 10000/10000 (`terrain.md` 1, 6). Ski run cut on purpose
  (2026-11-11): nearly all of it was ours over smooth slope.
- Earlier: PowerMonger LLM commander no better than random (Haiku 8/30 vs placebo 7/30); Paint It Black's ~55
  claims checked; Populous swamp edge on Hatari 75.9% vs ours 70.0% (`populous/systems.md` 1.3).

## Running

Nothing running.

## Open, in priority order

1. **Carrier Command: which figures become a post or series** (Dave's call); then copy the chosen PNGs into
   `static/images/posts/carriercommand/` and draft with the `dave-post` skill. "Today's relevance" per figure
   (distance-vector routing, BSP, self-modifying code) needs a cited source before naming any modern use.
2. **Midwinter post: Dave's writing** (hook, TODOs, paste the real `terrain.fsx domain` output), then render-check.
3. **Paint It Black: Dave's TODOs**; then commit it and the GIFs.
4. **Stale claims seen, not fixed:** `IDEAS.md` entry 1 and `reversing/black_tiger/secrets.md:48` say Black Tiger
   is unfixed (fixed in `5636dc5`); fix once Dave agrees.
5. **Untested effects:** whether the `$1817e` stray write changes the enemy's island choice (`ai/nat2` corpus,
   score.py with and without the 500), and the octdist "3 of 11 picks change with true distance" counterfactual,
   which is computed, not run in the game. Both belong to the carriercommand workstream if pursued.
6. IDEAS.md candidates (Cadaver depth bitsets, Populous world generator); Super Sprint post gaps (blocked).

## Known traps

- The local Hugo is v0.148.1; the site needs 0.162 or later, so `hugo --buildDrafts` fails.
- Infographic agents' facts files can name fewer writers than a raw scan finds (BSP's `$9de`: 2 named, 4 real);
  re-scan any negative before it goes into a doc.
- `gen_routing.py drive` takes about 5 minutes; plain `gen_routing.py` redraws from `routing_drive/` logs.
- `gen_depack.py` panel F needs lz4, gzip, zstd and xz on PATH; sizes are measured on stdin.
- Clips and motion (Midwinter reveal) are judged from contact sheets here; ask Dave to watch before calling one done.
- `IDEAS.md` is untracked; hand agents its current state.

## Waiting on Dave

- Which Carrier Command figures to publish, and as one post or a series (Open 1).
- Push master (21 ahead) and when to push the blog repo.
- The Midwinter and Paint It Black writing; the Black Tiger stale-claim fixes.
- The carriercommand session file still lists "3D drawing order" as open; its next resume should drop it
  (`render.md` 4 settles it for the far path).
- Upgrading Hugo locally.

## Next session

`/resume blog`. Ask Dave which Carrier Command figures go into a post; copy those PNGs into the blog repo and
scaffold the post with `dave-post`, quoting each figure's numbers from its `.facts.md` and topic-doc section.
If Dave has written into the Midwinter post instead, re-check every changed passage against `terrain.md`.
