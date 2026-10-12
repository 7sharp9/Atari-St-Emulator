# Blog: handoff

Updated 2026-10-12 by the session that ended at commit `564f233`.

The blog workstream curates and extends posts for 7sharp9.dev from the game research. Each game is
reversed in its own workstream; this one reads their docs, checks the claims a post would rest on
(on real Hatari where the claim depends on our emulator), and feeds corrections back to the game
docs. A fix to a game doc is committed as that game's commit; the game's own handoff is not edited
here.

## Resume point

- Last commits of this workstream: `65eb65b` + `564f233` (Populous swamp edge re-measured, chart
  `reversing/populous/swamp_edge.svg`); before that `c0b9ad7`, `b9e5ab8`, `e9a9d6c`, `58cdd8c`,
  `2a392ac`, `d295189`.
- Blog repo: `~/GitHub/7sharp9.github.io` (Hugo, Blowfish theme). Post ideas live in `IDEAS.md` there.
- Working data: `M68000/scratchpad/pop/hatari_edges/` (five Hatari boots `run_b1..b5/` with
  `hatari.log` + `edges.csv`, ours in `ours/repro.csv`). Rebuild: `hatari_edges.py run 620 b<i>`
  per boot, `parse <log> <csv>`; `swamp208.py edges scratchpad/pop/repro.snap 3075 <csv>`.
- Uncommitted work left behind, all deliberate:
  - blog repo `IDEAS.md`: untracked and stays so (Dave's decision, 2026-10-12: keep the post
    notes private). This session updated the entry 3 swamp-edge note.
  - blog repo `ideas/` (Cadaver script spikes with `obj/` build output) and the uncommitted edits to
    `content/Programming/2026-09-22-paint-it-black.md`: another session's work; do not touch.

## Proven so far

- Populous swamp-monster entry edge (an uninitialised stack word `$3f418` written by interrupt
  handlers): south 4805/6333 = 75.9% on real Hatari over ten cold boots (73.8-78.7% per boot), 70.0%
  (2151/3075) on our emulator. Over the same frames 623..1292: ours 462/670 = 69.0%, below every
  Hatari boot, the shortfall going to `$fd50` (16.0 vs 11.9%) and `$fc` (13.1 vs 9.8%). Our run is
  deterministic, so one run is its whole spread. `systems.md` 1.3; chart by `hatari_edges.py chart`.
- Super Sprint walls and collision: planes 64000/64000 on all 8 tracks (`tracks/prove_all.py`),
  `$bda4` 1800/1800, `$14a4a` 450/450, whole car model 700/700 frames with 19 live wall bounces
  (`physics/test_trajectory.py 700 3`). Behaviour Track 1 only; crash path fuzz-only.
- PowerMonger `SPRITE40.DAT` symbol table: 1,639 DRI records, 1,196 unique entries, 1,099 names;
  uncracked original (2,895 fixups match, only `$b842` differs); 8 of our `.sym` names
  contradicted the label and the body sided with the label (`strategy.md` "Original names").
  Earlier misreadings for the post's scorecard: `git log -S` on the phrases, first in
  `cb82ebc`/`1dd47ac`.

## Open, in priority order

1. **Finish "Paint It Black"** before drafting another (IDEAS.md rule): hook choice and the
   personal paragraph are Dave's. Its uncommitted edits (99.7-99.99% figures, a TODO on weather
   and new sprite categories) belong to another session; ask before touching.
2. **IDEAS.md candidates** (file stays untracked): add the ranked ones Dave picks, each checked
   against its topic doc first: Cadaver depth bitsets ("Stand Back": 1060/1060, 90/90,
   `cadaver/graphics.md` 5k), packers across six games ("Under Pressure"), emulator performance
   74 s to 6.8 s ("Faster", re-measure before quoting), the DAC fold-in under entry 4 (diff the
   three games' 2048-byte `movep` tables first), the stale-register bug class (PowerMonger farmer
   search: merchants 222/281, 448/558; `economy.md` job pick), determinism ("Deja Vu"; overlaps the
   Populous note, pick one home).
3. **Super Sprint post gaps** (entry 5): live collision on more tracks with a joined player, or scope
   to Track 1; a sampler negative control; the staged-fill figure. The race-start crash
   (supersprint handoff item 1) blocks driving other tracks.
4. **PowerMonger symbol leftovers** (for the powermonger workstream unless the post needs them):
   five unclear labels (`$37c2`, `$11f78`, `$fe8e`, `$16892`, `$3c08`); the `g_mission_descriptor`
   `$5809c` claim; the `.sym` header's "backed by disassembly" for the 938 copied entries; a fifth
   bare `rts` at `$1ba70`.

## Known traps

- `IDEAS.md` is untracked; an agent that read it before an edit proposed a duplicate entry. Hand
  agents the current file state or tell them which entries exist.
- The Hatari binary is another session's build at
  `/private/tmp/claude-501/-Users-davethomas-GitHub-Atari-St-Emulator/b1339997-.../scratchpad/hatari-x86/src/hatari`
  (still there 2026-10-12); it can vanish. Rebuild per `DEVELOPING.md` "macOS" and set `HATARI`.
  One `hatari_edges.py run 620` boot takes a few minutes.
- A chart for the blog is shown as an `<img>`, so it cannot follow Blowfish's dark toggle: give the
  SVG its own opaque surface (as `swamp_edge.svg` does).
- README summaries are stronger than the topic docs in places (Super Sprint's "not within one",
  PowerMonger's counts): quote the topic doc, not the README, in a post.

## Next session

`/resume blog`. Ask Dave which post to work on: Paint It Black first per IDEAS.md, or entry 3
("God Only Knows", which now has its swamp-edge figure but needs the world generator ported to F#
first). Then add the IDEAS.md candidates Dave picks from Open 2, each checked against its topic doc.
