# Blog: handoff

Updated 2026-10-12 by the session that ended at commit `d295189`.

The blog workstream curates and extends posts for 7sharp9.dev from the game research. Each game is
reversed in its own workstream; this one reads their docs, checks the claims a post would rest on
(on real Hatari where the claim depends on our emulator), and feeds corrections back to the game
docs. A fix to a game doc is committed as that game's commit; the game's own handoff is not edited
here.

## Resume point

- Last commits of this workstream: `c0b9ad7` + `b9e5ab8` (Populous swamp edge on Hatari),
  `e9a9d6c` (Super Sprint README), `58cdd8c` + `2a392ac` (PowerMonger developer symbols),
  `d295189` (DEVELOPING.md, Hatari driving).
- Blog repo: `~/GitHub/7sharp9.github.io` (Hugo). Post ideas live in `IDEAS.md` there.
- Working data: session scratch dirs are under `/private/tmp/...` and do not survive; everything
  worth keeping is in the commits above.
- Uncommitted work left behind: blog repo `IDEAS.md` (new entries 5 and 6, a section note under
  entry 3). It has never been tracked in that repo, and committing it would publish the notes once
  the repo is pushed: Dave's decision. `content/Programming/2026-09-22-paint-it-black.md` has
  uncommitted edits that are not this session's: do not touch.

## Proven so far

- Populous swamp-monster entry edge (an uninitialised stack word `$3f418` written by interrupt
  handlers): south 2335/3075 = 75.9% on real Hatari over five cold boots, 69-70% on our emulator;
  same value family on both (`reversing/populous/py/systems/hatari_edges.py`, `swamp208.py edges`;
  `systems.md` 1.3).
- Super Sprint walls and collision: planes 64000/64000 on all 8 tracks (`tracks/prove_all.py`,
  re-run), `$bda4` 1800/1800, `$14a4a` 450/450, whole car model 700/700 frames with 19 live
  wall bounces (`physics/test_trajectory.py 700 3`, re-run). Behaviour Track 1 only; crash path
  fuzz-only. Race-start crash happens after the planes are built (agent run from `prep_kbd.snap`).
- PowerMonger `SPRITE40.DAT` symbol table: 1,639 DRI records, 1,196 unique entries, 1,099 names;
  uncracked original (2,895 fixups match, only `$b842` differs); 8 of our `.sym` names
  contradicted the label and the body sided with the label (`strategy.md` "Original names").
  The committed earlier misreadings for the post's scorecard: `git log -S` on the phrases, first
  in `cb82ebc`/`1dd47ac`; "neutral garrison" for `$18` was never committed.

## Open, in priority order

1. **Finish "Paint It Black"** before drafting another (IDEAS.md rule): hook choice and the
   personal paragraph are Dave's.
2. **Decide IDEAS.md tracking** (commit, or keep untracked/private), then add the ranked
   candidates not yet in it, as Dave chooses: Cadaver depth bitsets ("Stand Back": 96-bit
   behind-sets, 1060/1060, 90/90, `cadaver/graphics.md` 5k), packers across six games
   ("Under Pressure"), emulator performance 74 s to 6.8 s ("Faster", `DEVELOPING.md`
   "Performance"; re-measure before quoting), the DAC fold-in under entry 4 (diff the three
   games' 2048-byte `movep` tables first), the stale-register bug class as a companion to entry 1
   (PowerMonger farmer search: merchants 222/281, 448/558; `economy.md` job pick), determinism
   across the games ("Deja Vu"; overlaps the Populous note, pick one home).
3. **Super Sprint post gaps** (entry 5): live collision on 2-3 more tracks with a joined player
   (`drive_track.py`, then `test_samplers natural`, `test_trajectory`), or scope to Track 1; a
   sampler negative control (perturbed mask table); the staged-fill figure. The race-start crash
   (supersprint handoff item 1) blocks driving other tracks.
4. **PowerMonger symbol leftovers** (for the powermonger workstream unless the post needs them):
   five labels with unclear meaning (`$37c2`, `$11f78`, `$fe8e`, `$16892`, `$3c08`); the
   `g_mission_descriptor` comment's `$5809c` claim; the `.sym` header's "backed by disassembly"
   is not true of the 938 copied entries; a fifth bare `rts` at `$1ba70`.
5. **Swamp-edge section**: a bar chart of edge values, Hatari against ours, from the CSVs
   `hatari_edges.py parse` writes (re-run `hatari_edges.py run` first; the earlier logs were in
   scratch).

## Known traps

- `IDEAS.md` is untracked in the blog repo; an agent that read it before an edit proposed a
  duplicate entry. Hand agents the current file state or tell them which entries exist.
- The Hatari binary used was built by another session under its `/private/tmp/.../scratchpad/`;
  it can vanish. Rebuild per `DEVELOPING.md` "macOS" and set `HATARI`.
- Background agents left `tail -f` processes on their logs; check `ps` after each and kill only
  ones under this session's scratch path.
- README summaries are stronger than the topic docs in places (Super Sprint's "not within one",
  PowerMonger's counts): quote the topic doc, not the README, in a post.

## Next session

`/resume blog`. Ask Dave which post to work on (Paint It Black first, per IDEAS.md) and whether
IDEAS.md should be committed. Then add the chosen candidates from Open 2 to IDEAS.md, each checked
against its topic doc before it goes in, and close the gaps of the post Dave picks (Open 3 for
Super Sprint).
