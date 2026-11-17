# Blog: handoff

Updated 2026-11-17 by the session that ended at commit `23dd01b` (master; the blog repo at `ea591df`).

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

**Dave (2026-11-16): he wants an ML / AI-engineering slant**, since that is his work from now on; posts need not
repeat what the blog did before but should meet its depth. He is open to games not yet reversed and to a long,
patient pipeline. **Archipelagos is no longer the next post**: Dave is not sold on it (an island from its number by
one stamp generator; the work stays in `reversing/archipelagos/`, proven, not ported).

## Resume point

- Last commit of this workstream: blog repo `ea591df` (IDEAS entries 1 emulator bugs and 4 sample player cut, by
  Dave's choice: the first is not an algorithm post, the second is standard ST technique). No emulator-repo commit
  this session. Master is 19 ahead of origin, the blog repo 4; neither pushed.
- Working data: as before (`scratchpad/archipelagos/`, Captive `scratchpad/captive/infographics/data/route.json`,
  Midwinter `scratchpad/midwinter/mockup/`).
- Uncommitted work left behind: none (`.vscode/settings.json` untracked, not this session's).

## Proven so far

Unchanged this session; pointers: Archipelagos generator (`reversing/archipelagos/README.md`, gate
`archipelagos/islands`); Captive keys (`captive/mapgen.md`); Midwinter roughness (`midwinter/terrain.md` 1) and port
70000/70000; PowerMonger LLM commander (`powermonger/commander/README.md`, "Land 2 as a rate": scripted 0/30, Haiku 0,
rollout 4, hybrid 8, random-proposer placebo 7, no search arms separable; Haiku's candidate best at 29% of decisions
against 15% random); Populous swamp edge 75.9% Hatari vs 70.0% ours.

## Running

Nothing from this session. Linked session "Start reversing Little Computer People"
(`local_51e994b0-1b8a-48ed-b4a8-b09e632483d7`) owns the `lcp` workstream; it committed `23dd01b`: the behaviour is a
fixed-priority cascade, not needs scoring, and Kroah's 2006 reverse engineering is prior art. That changes the
post angle assumed here ("needs-and-timer scheduler as generative agents, 1985"): read `reversing/lcp/README.md`
before pitching it.

## Open, in priority order

Ranking agreed from this session's review plus a Fable 5.2 second opinion (figures checked against the commander
README; Fable's "24 of 27 losses are the captain" is not in the doc, do not quote it).

1. **Finish Paint It Black** (hook and personal paragraph are Dave's), then **Mountains of the Moon** (line 50).
2. **"The placebo arm"**: first ML post, from the commander's measured land-2 results. Scope to state: memoryless,
   toolless LLM deciding every 20M, one land, 30 starts. Figures: win grid by start and arm, captain-death timeline.
   Optional extra arm: an LLM with memory of its last orders and outcomes.
3. **Cadaver's language** (IDEAS 2), then **the planner** (IDEAS 7): the F# post and its classical-AI sequel; a
   possible LLM agent against the planner's reachable sets.
4. **Virus flown by optimisation**: F# port of the proven flight tick (`virus/README.md`, flight 119/119), a
   TorchSharp float surrogate, planned controls replayed in the emulator against the demo autopilot (`demo.md`).
   Keeps the F#-port shape with an ML payload.
5. **"Graded by the authors"**: IDEAS 6 reframed as an LLM function-naming benchmark against the developer symbol
   table, arms by context (body, callers, decompile, runtime evidence). The repo is public and the docs quote many
   names: design a held-out set before running.
6. **PowerMonger world model**: forecaster plus captain-death hazard on the rollout logs; needs more than 30 starts.
7. **New games for the pipeline**: Laser Squad first (hidden units, line of sight; enemy AI undocumented per a
   Spectrum disassembly thread), Colossus Chess X (evaluation and what "learns" means; check the dump). Cut: The
   Sentinel (Moxon's documented source), Balance of Power (source released).
8. Cut or sidebar, keep out of the queue: Super Sprint (cut), Archipelagos, Populous generator, Bug2, causeway,
   Captive keys/digger/galaxy; the influence-map, utility, ecology, alliance and plain-language ideas in
   `reversing/ideas.md` (unbuilt, nothing to measure). Carrier routing and span filler stay as infographics.
9. Carried: Midwinter draft line 50, Captive emulator-check sampled bases, Carrier Command series, unsourced figures,
   `gen_takeoff.py` cache, Black Tiger stale claim.

## Known traps

- A web-fetch agent briefed with a page cap reads only what it is pointed at: name the bugs and release pages.
  MobyGames answers 403 and new.tcrf.net fails DNS for it; use another source.
- The local Hugo is v0.148.1; the site needs 0.162 or later, so `hugo --buildDrafts` fails.
- `docguard` reports a token's delta, not its meaning.
- Three PowerMonger figures have no generator (the SVG is the source); PNGs: `rsvg-convert -b white -w 1800`.
- `tools/gates.py run <game> -k <gate>` runs one gate; `run <game>/<gate>` fails.
- IDEAS.md entries are cited by number ("entry 2", "entry 9"): leave gaps when cutting, do not renumber.

## Waiting on Dave

- Whether to rewrite IDEAS.md around the Open ranking (the ML entries 2, 4, 5, 6 are not in it yet).
- Captain Blood prior art: AtariMania lists Kroah's Game Reverse Engineering Page as covering its interpreter and
  conversation system (search snippet only, unread); the `captainblood` workstream should read it before more
  `rules.md` work. Not written into that game's docs from here.
- His Midwinter draft line 50; keep or redo the Captive keys figure.
- Carried: the Carrier Command series, "proven" vs "observed" in Crude Buster and Final Fight, the Lemmings artifact
  republish, the Black Tiger stale claim, upgrading Hugo, pushing master and the blog repo.

## Next session

`/resume blog`. Ask Dave whether to finish Paint It Black now (its two TODOs are his) or start "The placebo arm":
read `powermonger/commander/README.md` "Policies against the game's AI", "Land 2 as a rate" and "Evaluation design",
then scaffold the post with the `dave-post` skill and draw the win grid from `scratchpad/cmd14/l2s30` and
`cmd15/l2s30`. Read `reversing/lcp/README.md` before pitching an LCP post.
