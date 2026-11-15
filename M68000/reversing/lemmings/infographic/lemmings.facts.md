# inside_lemmings: sources for the explanatory sentences added in the clarity pass

Page: `reversing/lemmings/infographic/template.html`, built by `gather.py` into `scratchpad/lemmings/info/inside_lemmings.html`
(the page holds the data of the runs; only wording was changed, so the run data in `data.json` were reused unchanged).
The page's earlier prose is sourced in the HTML comment at the top of `template.html`. Doc: `reversing/lemmings/mechanics.md` (M).

| sentence on the page | source |
|---|---|
| "it comes from reverse-engineering the game in an emulator" | the page's own next sentence ("We booted the original Atari ST disk in an emulator ... recorded what memory did"); `README.md` of this folder |
| "(the Atari ST is a home computer released in 1985)" | `reversing/GLOSSARY.md` "Atari ST" |
| tile "processor instructions (steps) per game tick, the game's unit of time (3 video frames)" | M "Basher and miner" (tick = 36,000 steps = 3 VBL); GLOSSARY.md "step", "tick" |
| tile "skills triggered in the emulator, most compared with a run without the click" | the old tile "skills driven in the emulator, most against a control" and the "control" term |
| key line (addresses; proven / observed / inferred) | clarity-pass conventions; the old terms row "driven / read". No claim on this page is labelled proven: no model-versus-game match count is quoted |
| terms "written by hand (poke)" | M header and "The other skills" preamble ("pokes are inputs"); the old "poke" term |
| terms "observed / inferred" for the old "driven / read" | the old definitions ("we made it happen in the emulator and saw the effect in memory" / "worked out from the game's disassembled code") |
| "plane 0 of the level image (the ST stores a picture as four bitplanes, one bit of each pixel's colour in each)" | GLOSSARY.md "bitplane, plane"; M "Collisions" (terrain bitmap is plane 0 at `$41806`, stride `$330`) |
| "falls (state bit 15)", "ledge hop (state bit 13)" | the old "falls (bit 15)", "ledge hop (bit 13)"; the state-word tiles below |
| "orange ticks have the ledge-hop bit (state bit 13) set" | the old "orange ticks have bit 13 set"; probe table row "a step 3 to 6 rows high" |
| "30 bytes into the game's block of variables for the pointer and skill panel" | the old "offset 30 in the game's mouse-and-panel block"; M "Skill assignment" (click struct `$26c04`) |
| "Plates that show a wall, pit or steel cells use terrain written into memory ... (see 'How this was checked')" | the page's own "How this was checked" paragraph ("Walls, pits and steel cells in the plates for climber, floater, basher and the steel tests were written into memory") moved up next to the plates; the original is kept |
| "written in / written under / changed" replacing "poked" in captions and plate set-up lines | the old captions; same facts, wording only |
| tags "observed" / "inferred" replacing "driven" / "read" | the old tags (14 driven, 1 read, plus the JavaScript plate chips) |

Hedges kept: "Still open: the object pictures, and the blocker's refusal test"; "Everything here was observed on the Atari ST version, level 1".
