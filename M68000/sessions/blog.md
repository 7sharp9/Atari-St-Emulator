# Blog: handoff

Updated 2026-11-11 by the session that ended at commit `8a2138c`.

The blog workstream curates and extends posts for 7sharp9.dev from the game research. Each game is
reversed in its own workstream; this one reads their docs, checks the claims a post would rest on
(on real Hatari where the claim depends on our emulator), and feeds corrections back to the game
docs. A fix to a game doc is committed as that game's commit; the game's own handoff is not edited
here. Dave's direction (2026-11-11): posts explain algorithms the games use and their relevance
today, not emulator bug fixes.

## Resume point

- Last commit of this workstream: `8a2138c` (Midwinter `fs/` renders; the terrain port is `974d739`..`8a2138c`).
  Pushed up to `9e58e9e`; `c9071c1` and `8a2138c` are local only.
- Blog repo `~/GitHub/7sharp9.github.io`: `2fa425c` commits the Midwinter post
  `content/Programming/2026-11-11-mountains-of-the-moon.md` (`draft: true`) and its media in
  `static/images/posts/midwinter/` (levels, zoom, map, reveal.mp4, skier_vs_game). Not pushed.
- Working data: `M68000/scratchpad/midwinter/terrain/gate/` (gate snapshots; rebuild with
  `reversing/midwinter/py/terrain/gate_terrain.py`), renders in `M68000/scratchpad/midwinter/terrain/fs/`,
  every one rebuilt by a `reversing/midwinter/fs/terrain.fsx` command (header lists them). `d_ski.snap` for the
  skier still and the live checks.
- Uncommitted work left behind in the blog repo, all deliberate:
  - `content/Programming/2026-09-22-paint-it-black.md` and `static/images/posts/powermonger/walk_*.gif`:
    Paint It Black's fact-check fixes and figures, waiting on Dave's writing (rebuild recipe for the GIFs:
    previous handoff in git, `git show 41734eb:M68000/sessions/blog.md`).
  - `IDEAS.md` untracked by Dave's decision (post notes stay private); entry 8 is the Midwinter post. `ideas/`
    is the Cadaver session's.

## Proven so far

- Midwinter post: the F# port reproduces the game's generator 70000/70000 cells over 7 windows and the post-passes
  10000/10000 (`fs/terrain.fsx gate`; `--break` control 1126/70000); the domain model matches every interior cell
  except the south/east 64-cell edge band, 63002/64512 inside a 2-cell margin (`domain`); overlapping game windows
  agree inside 2 cells (`same`): `terrain.md` sections 1 and 6. Shift per level is 4,4,5,6,7 (section 2).
- Vertical scale 256 height units per cell from `$16d9c`, checked live; the ski view is double-buffered and drawn from
  the RAM camera; goggle palette `$157/$467/$777/$245`; our render of the snapshot's view is about 10 px high on the
  ridges, not explained by draw distance (`terrain.md` section 5; `skier`, `skier --far`).
- Decided with Dave: the post's visuals show the game's own content. The reveal (rise then orbit of the central
  peak, cold clear grade) is the one video; the levels figure carries the subdivision, the post's main point. The
  ski run was cut on purpose (2026-11-11): nearly all of it was ours (inferred metre scale, skier physics, line
  planning, snow grain) over 54 m cells of smooth slope; the code stays (`ski`, `skiline`) but the post does not use it.
- PowerMonger LLM commander: no better than a random proposer (Haiku 8/30 vs placebo 7/30, McNemar not significant);
  a heuristic follow-up was proposed as its own session card ("Commander: captain-exposure term in rollout score").
- Earlier: Paint It Black's ~55 claims checked; Populous swamp edge on Hatari 75.9% vs ours 70.0%
  (`populous/systems.md` 1.3).

## Running

Nothing running.

## Open, in priority order

1. **Midwinter post: Dave's writing.** Hook (A/B/C), the TODOs in each section, the real `terrain.fsx domain`
   output pasted in, the edge-band verdict, and the "today's relevance" paragraph (find a source before naming
   any game or engine). Hatari was not run: the generator is pure arithmetic, so the post says so rather than
   claims it. Then push the emulator repo (`c9071c1`, `8a2138c`) so links [3] and [4] resolve, and render-check.
2. **Paint It Black: Dave's TODOs** (hook, asides, Godot verdict, "Where to next"); then commit it and the GIFs.
3. **Stale claims seen, not fixed:** `IDEAS.md` entry 1 says Black Tiger is unfixed (fixed in `5636dc5`), and
   `reversing/black_tiger/secrets.md:48` says the same; fix both once Dave agrees.
4. **IDEAS.md candidates** (Cadaver depth bitsets, packers, determinism, Populous world generator "God Only
   Knows": port to F# byte-identical on 3 worlds against `populous/terrain.md`).
5. **Super Sprint post gaps** (blocked by the race-start crash, supersprint handoff).

## Known traps

- The local Hugo is v0.148.1; the site's modules need 0.162 or later, so `hugo --buildDrafts` fails. A render
  check needs a newer Hugo (Dave's call) or the GitHub Pages build.
- `dotnet fsi` compiles every `#load`ed file per command, so a compile error in `Drone.fsx` fails every
  `terrain.fsx` command, including `gate`; a render command that fails leaves its old output file in place.
- `Drone.fsx` names `row` locally (grid rows) and `Render.row` (images side by side): qualify the latter.
- The reveal and drone clips are judged from contact sheets in-session; motion faults (judder, shimmer) only show
  in playback: ask Dave to watch before calling a clip done.
- Posts inherit looser wording than the specs (PowerMonger walkthrough vs SPEC.md); quote the topic doc.
- `IDEAS.md` is untracked; hand agents its current state.

## Waiting on Dave

- The Midwinter and Paint It Black writing (Open 1, 2), and when to push the blog repo and publish.
- The Black Tiger stale-claim fixes (Open 3).
- The commander experiment card (start it or dismiss it).
- Upgrading Hugo locally.

## Next session

`/resume blog`. If Dave has written into the Midwinter post, re-check every changed passage against `terrain.md`
(sections 1, 2, 5, 6) and the `fs/` code, paste the real `terrain.fsx domain` output, and push the emulator repo
when he agrees so the post's links resolve. Otherwise ask which of Open 2-4 to take next.
