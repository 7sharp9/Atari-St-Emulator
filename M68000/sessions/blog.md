# Blog: handoff

Updated 2026-10-31 by the session that ended at commit `41734eb` (no repo commits of this workstream).

The blog workstream curates and extends posts for 7sharp9.dev from the game research. Each game is
reversed in its own workstream; this one reads their docs, checks the claims a post would rest on
(on real Hatari where the claim depends on our emulator), and feeds corrections back to the game
docs. A fix to a game doc is committed as that game's commit; the game's own handoff is not edited
here.

## Resume point

- Last commits of this workstream: `65eb65b` + `564f233` (Populous swamp edge re-measured, chart
  `reversing/populous/swamp_edge.svg`).
- Blog repo: `~/GitHub/7sharp9.github.io` (Hugo, Blowfish theme). Post ideas live in `IDEAS.md` there.
  Paint It Black is `content/Programming/2026-09-22-paint-it-black.md`, still `draft: true`.
- Working data: `M68000/scratchpad/pop/hatari_edges/` (Populous swamp edge; rebuild recipe in
  `reversing/populous/systems.md` 1.3 and `py/systems/hatari_edges.py`).
- Uncommitted work left behind in the blog repo, all deliberate (nothing committed or pushed there
  without Dave's say):
  - `content/Programming/2026-09-22-paint-it-black.md`: the PowerMonger session's earlier figure
    updates (99.7-99.99% inline table) plus this session's fact-check fixes. This workstream now owns
    the file (the PowerMonger session was told; no reply yet).
  - `static/images/posts/powermonger/walk_cells.gif` (65 frames, 8 fps) and `walk_strips.gif`
    (9 frames, 2 fps), now live figures in the post. Rebuild: copy `reversing/powermonger/port` without
    `bin/obj` to a scratch dir, `cd stepper && dotnet run -c Release -- --export <dir> cell|strip`,
    then ffmpeg with `palettegen=max_colors=32 / paletteuse=dither=none`.
  - `IDEAS.md` untracked by Dave's decision (2026-10-12: post notes stay private); `ideas/` is the
    Cadaver session's.

## Proven so far

- Paint It Black: about 55 claims (counts, addresses, the six-capture table, every F# snippet) match
  `reversing/powermonger/port/SPEC.md`, `README.md`, `walkthrough/walkthrough.md` and the port source.
  Fixed: the headline 99.7-99.99% now carries the `pm78_settle` 94.6% caveat (README "inline scores"),
  the Godot section's sourceless "94-98%" replaced by `walkthrough.md`'s figure, the season fade is
  16 LCG steps per tick and about 9 pixels (SPEC.md "season" table), "one tick into summer" holds for
  `pm88_f1` only, and at yaw 12 cos is 0 rather than positive.
- Populous swamp-monster entry edge: south 75.9% on real Hatari over ten cold boots vs 70.0% ours
  (`populous/systems.md` 1.3; chart by `hatari_edges.py chart`).
- Super Sprint walls and collision, PowerMonger `SPRITE40.DAT` symbol table: see the post sources
  `supersprint/` (tracks/prove_all.py, physics/test_trajectory.py) and `powermonger/strategy.md`
  "Original names".

## Running

Nothing running.

## Open, in priority order

1. **Paint It Black: Dave's TODOs.** All that remains is his writing: the hook (A/B/C, line 11), the
   personal-context paragraph, five asides (zoom, the extra-row bug, the 43-47% phase bug, the 2689
   wasted pixels, what the stepper showed), the Godot verdict, "Where to next", and whether to weave
   in or cut the weather/new sprite categories TODO. Link [2] is fine to keep: the repo is public.
   Before publishing, check `walkthrough.md` on `origin/master` has the wording the post cites.
2. **IDEAS.md candidates** (file stays untracked): add the ones Dave picks, each checked against its
   topic doc first: Cadaver depth bitsets ("Stand Back"), packers across six games ("Under
   Pressure"), emulator performance ("Faster", re-measure before quoting), the DAC fold-in under
   entry 4, the stale-register bug class (PowerMonger farmer search), determinism ("Deja Vu").
3. **Entry 3, "God Only Knows"** (Populous): port the world generator to F# first (byte-identical on
   3 worlds against `reversing/populous/terrain.md`); the swamp-edge figure is ready.
4. **Super Sprint post gaps** (entry 5): live collision on more tracks or scope to Track 1; a sampler
   negative control; the staged-fill figure. Blocked by the race-start crash (supersprint handoff).
5. **PowerMonger symbol leftovers** (the PowerMonger workstream's unless the post needs them): five
   unclear labels (`$37c2`, `$11f78`, `$fe8e`, `$16892`, `$3c08`), `g_mission_descriptor` `$5809c`,
   the `.sym` header's "backed by disassembly" claim, a fifth bare `rts` at `$1ba70`.

## Known traps

- The local Hugo is v0.148.1; the site's modules need 0.162 or later, so `hugo --buildDrafts` fails on
  every page (`can't evaluate field Locale`). A render check needs a newer Hugo (a system change:
  Dave's call) or the GitHub Pages build.
- Posts inherit the walkthrough's wording, and the walkthrough is looser than SPEC.md and the port
  README (the fade's "16 pixels", "one tick into summer"). Check a post's figures against SPEC.md
  and README, not only the walkthrough. Wording fixes for `walkthrough.md` went to the PowerMonger
  session (lines 544, 579, the yaw sentence); it owns that file.
- `IDEAS.md` is untracked; hand agents its current state or they propose duplicate entries.
- Build the PowerMonger stepper from a copy, not in place: the PowerMonger session builds the same
  `obj/`.
- The Hatari binary used for Populous is another session's build under `/private/tmp/...`; it can
  vanish. Rebuild per `DEVELOPING.md` "macOS" and set `HATARI`.
- A chart shown as an `<img>` cannot follow Blowfish's dark toggle: give the SVG an opaque surface.
- README summaries can be stronger than the topic docs: quote the topic doc in a post.

## Waiting on Dave

- Paint It Black's hook and personal TODOs (Open 1); then whether to commit the post and GIFs in the
  blog repo, and when to publish.
- Upgrading Hugo locally so drafts can be render-checked.

## Next session

`/resume blog`. If Dave has filled the Paint It Black TODOs, re-check every changed passage against
SPEC.md and the port README, check `walkthrough.md` on `origin/master` for the cited wording, and ask
before committing in the blog repo. Otherwise ask Dave which IDEAS.md candidate (Open 2) to check next.
