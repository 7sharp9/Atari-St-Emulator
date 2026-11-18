#!/usr/bin/env python3
"""Build the game-learning field map: README.md and field-map.canvas (Obsidian Canvas, a mind-map
layout) from the one table below. Run from anywhere: python3 build_map.py

Each paper row: (short name, year, venue, OpenAlex id, citations, basis, one line, applies_here)
  basis  A = the line is taken from the abstract OpenAlex returned
         F = the paper's full text was read
         T = the line restates the title only
         R = the line adds a detail recalled from memory, not checked against the paper
  citations are OpenAlex cited_by_count on the day in COUNTED.
"""
import json
import os

COUNTED = "2026-11-18"
HERE = os.path.dirname(os.path.abspath(__file__))

ROOT = ("Learning to play games",
        "A game is a Markov decision process: state, action, transition rule, reward. "
        "The research splits on where the transition rule comes from (an emulator, extracted code, "
        "or a learned network) and on how many game steps the learner may spend.")

BRANCHES = [
    ("Environments and evaluation",
     "How a game is wrapped for a learner (reset, step, observation, reward, done) and how results are compared.",
     "The emulator has the pieces (seeded starts, snapshots, RAM-derived reward) but no single env interface. "
     "The 2% weight-change noise measured on Virus is the problem the 'statistical precipice' paper names.",
     [
         ("Arcade Learning Environment", 2013, "JAIR", "W2150468603", 3605, "T",
          "Atari 2600 emulator packaged as an evaluation platform for general agents.", False),
         ("Revisiting the ALE", 2018, "JAIR", "W2754879180", 671, "T",
          "Evaluation protocols and open problems for agents on the ALE.", False),
         ("Gotta Learn Fast (Gym Retro)", 2018, "arXiv", "W2796979132", 204, "A",
          "Benchmark built on the Sonic the Hedgehog games, for transfer and few-shot learning.", False),
         ("Survey: deep RL in video games", 2019, "arXiv", "W2996726407", 320, "T",
          "Survey of deep reinforcement learning methods across video games.", False),
         ("Statistical precipice", 2021, "arXiv", "W3197485521", 1082, "A",
          "Point estimates over a few training runs ignore statistical uncertainty; argues for interval estimates.", True),
         ("Atari-5", 2022, "arXiv", "W4303449812", 33, "T",
          "Distils the 57-game suite down to five games.", False),
         ("OCAtari", 2023, "arXiv", "W4380993741", 43, "A",
          "Atari environments extended with object-centric state instead of pixels only.", True),
         ("Gymnasium", 2025, "NeurIPS", "W7172656275", 157, "T",
          "The standard reset/step interface for reinforcement learning environments.", True),
     ]),
    ("Model-free learning",
     "No model of the game: a policy or value function is learned from trial and error alone. Reliable, but costs the most game steps.",
     "At 4.4M emulated instructions/s (about 367 frames/s per core) the large-budget methods here are slow; "
     "BBF-class sample-efficient methods fit.",
     [
         ("DQN", 2015, "Nature", "W2145339207", 39470, "T",
          "Human-level control of Atari games from pixels with a deep Q-network.", False),
         ("PPO", 2017, "arXiv", "W2736601468", 38652, "T",
          "Proximal policy optimisation, the default policy-gradient method.", False),
         ("Rainbow", 2018, "AAAI", "W2761873684", 2712, "T",
          "Combines the separate DQN improvements into one agent.", False),
         ("IMPALA", 2018, "arXiv", "W2786036274", 1705, "T",
          "Distributed actor-learner architecture with importance weighting.", False),
         ("R2D2", 2018, "ICLR", "W2908064123", 635, "T",
          "Recurrent experience replay in distributed reinforcement learning.", False),
         ("Agent57", 2020, "arXiv", "W3013618273", 629, "A",
          "First deep RL agent above the standard human benchmark on all 57 Atari games.", False),
         ("BBF", 2023, "arXiv", "W4379087150", 165, "A",
          "Value-based agent, super-human on the Atari 100K benchmark by scaling the value network.", True),
         ("PQN (Simplifying deep TD)", 2024, "arXiv", "W4400517417", 58, "A",
          "Q-learning aimed at dropping the replay buffer and target networks; built for many parallel environments (R).", True),
         ("Discovered RL rule", 2025, "Nature", "W4415437559", 61, "A",
          "A machine-discovered reinforcement learning rule that outperforms hand-designed ones.", False),
     ]),
    ("Search with a model",
     "Plan ahead by tree search, using the true rules or a learned model of them.",
     "stserver's in-memory fork and restore is the primitive tree search needs; the exact Python tick, shot and seeder "
     "functions in virus/py/mpc are a true-rules model, which is what AlphaZero assumes.",
     [
         ("AlphaZero", 2018, "Science", "W2902907165", 7467, "T",
          "One self-play algorithm masters chess, shogi and Go, searching with the true rules.", True),
         ("MuZero", 2020, "Nature", "W2989847975", 3329, "T",
          "Masters Atari, Go, chess and shogi by planning with a learned model.", False),
         ("EfficientZero", 2021, "arXiv", "W3208460365", 193, "A",
          "Sample-efficient visual RL built on MuZero, aimed at human-level Atari from limited data.", True),
         ("EfficientZero V2", 2024, "arXiv", "W4392427796", 42, "A",
          "Extends EfficientZero to both discrete and continuous control.", False),
     ]),
    ("Learned world models",
     "A network learns to predict the game; the policy is trained or planned inside that prediction.",
     "The route when a game has not been reversed. TD-MPC2 is the published relative of the Virus MPC pilot "
     "(planning over a short horizon), with a learned model where ours is exact.",
     [
         ("World Models", 2018, "arXiv", "W2890208753", 1178, "T",
          "Recurrent world models with the policy found by evolution.", False),
         ("SimPLe", 2019, "arXiv", "W2920362155", 898, "T",
          "Model-based reinforcement learning for Atari.", False),
         ("DreamerV2", 2020, "arXiv", "W3091507139", 1064, "T",
          "Masters Atari with discrete world models.", False),
         ("IRIS", 2022, "arXiv", "W4294435908", 250, "T",
          "Transformers as sample-efficient world models.", False),
         ("STORM", 2023, "NeurIPS", "W7133196033", 177, "T",
          "Efficient stochastic transformer world models.", False),
         ("TD-MPC2", 2023, "arXiv", "W4387964172", 385, "A",
          "Trajectory optimisation in the latent space of a learned model; 104 tasks with one set of hyperparameters.", True),
         ("Delta-IRIS", 2024, "arXiv", "W4400141986", 28, "T",
          "Efficient world models with context-aware tokenisation.", False),
         ("DreamerV3", 2025, "Nature", "W4409147637", 2473, "A",
          "Third-generation Dreamer: one general algorithm across domains without per-domain tuning.", True),
         ("Dreamer 4", 2025, "arXiv", "W4415336982", 175, "A",
          "Trains agents by RL inside a fast, accurate world model; demonstrated in Minecraft.", False),
         ("Simulus", 2025, "arXiv", "W4407713845", 7, "T",
          "Combines improvements in sample-efficient world-model agents.", False),
     ]),
    ("Neural game engines",
     "A generative model replaces the game itself: frames out, actions in.",
     "The opposite of this repo's method. These approximate a game nobody has reversed; "
     "the reversed routines here are exact and gated against the emulator.",
     [
         ("Genie", 2024, "arXiv", "W4392182423", 1004, "T",
          "Generative interactive environments.", False),
         ("GameNGen", 2024, "arXiv", "W4402704721", 348, "A",
          "A diffusion model simulates DOOM interactively at 20 frames/s on one TPU.", False),
     ]),
    ("Exploration, imitation, privileged teachers",
     "Ways round the hard parts: return to saved states, copy a demonstrator, or let an agent that sees everything teach one that does not.",
     "Closest fit to the open Virus problem: the full-memory planner ends 7 of 8 held-out waves, the player-view pilot 0 of 8. "
     "That is the teacher and student of 'Learning by Cheating'; DAgger is the training loop.",
     [
         ("DAgger", 2010, "arXiv", "W1931877416", 2539, "T",
          "Reduces imitation learning to no-regret online learning (R: the learner's own states are relabelled by the expert).", True),
         ("Evolution Strategies", 2017, "arXiv", "W2596367596", 2158, "T",
          "Evolution strategies as a scalable alternative to reinforcement learning.", False),
         ("Go-Explore", 2019, "arXiv", "W2914261249", 509, "A",
          "Hard exploration (Montezuma's Revenge, Pitfall) by returning to saved states, then exploring (R).", True),
         ("First return, then explore", 2021, "Nature", "W3018036994", 558, "T",
          "The journal version of Go-Explore.", True),
         ("Learning by Cheating", 2019, "arXiv", "W2996998055", 379, "A",
          "Train a privileged agent on ground-truth state, then use it as teacher for a vision-only agent.", True),
         ("Decision Transformer", 2021, "arXiv", "W3212637808", 2593, "T",
          "Reinforcement learning recast as sequence modelling.", False),
         ("VPT", 2022, "NeurIPS", "W7133197435", 501, "T",
          "Learns to act by watching unlabelled online videos.", False),
     ]),
    ("Throughput: fast and parallel simulators",
     "Run the game thousands of times at once. Much recent progress is here, not in the learning rule.",
     "Decides the fast-simulator question. The handoff's planned F# port of the Virus tick is this branch; "
     "so would be N emulator instances stepped in one process.",
     [
         ("CuLE", 2019, "arXiv", "W2963949762", 3, "T",
          "GPU-accelerated Atari emulation for reinforcement learning.", True),
         ("Sample Factory", 2020, "arXiv", "W3035554437", 110, "A",
          "Single-machine asynchronous RL from pixels at 100,000 frames/s.", False),
         ("Brax", 2021, "arXiv", "W3172279798", 676, "T",
          "Differentiable rigid-body physics engine for large-scale simulation.", False),
         ("EnvPool", 2022, "NeurIPS", "W7133223694", 102, "A",
          "Parallel environment execution engine; environment stepping is often the slowest part of training.", True),
         ("Jumanji", 2023, "arXiv", "W4381252681", 82, "T",
          "Suite of scalable environments written in JAX.", False),
         ("Craftax", 2024, "arXiv", "W4392223126", 116, "A",
          "A fast benchmark, because existing open-ended ones are either too slow or too simple.", False),
         ("PufferLib", 2024, "arXiv", "W4399911985", 25, "T",
          "Compatibility layer between RL libraries and environments.", False),
         ("Pokemon Red via RL", 2025, "IEEE CoG", "W4413321770", 13, "A",
          "Deep RL completes the opening of a Game Boy role-playing game, up to Cerulean City.", True),
     ]),
    ("Successes at scale",
     "The headline results: a full commercial game beaten at expert level, each with very large compute.",
     "Context, not a plan: none of these budgets is available here.",
     [
         ("AlphaStar", 2019, "Nature", "W2982316857", 5527, "T",
          "Grandmaster level in StarCraft II with multi-agent reinforcement learning.", False),
         ("OpenAI Five", 2019, "arXiv", "W2996037775", 2843, "T",
          "Dota 2 with large-scale deep reinforcement learning.", False),
         ("GT Sophy", 2022, "Nature", "W4210870706", 664, "T",
          "Outraces champion Gran Turismo drivers.", False),
         ("DeepNash", 2022, "Science", "W4310705874", 388, "T",
          "Masters Stratego with model-free multi-agent reinforcement learning.", False),
     ]),
    ("Language-model agents",
     "A language model plays the game directly, choosing each move from a prompt.",
     "Not a fit for a fast-reaction game like Virus; the benchmarks here report the models still struggle in dynamic games.",
     [
         ("Gato", 2022, "TMLR", "W4307868887", 1009, "T",
          "One generalist network across games, control and language tasks.", False),
         ("SIMA", 2024, "arXiv", "W4394946817", 93, "T",
          "Instructable agents scaled across many simulated worlds.", False),
         ("Survey: LLM game agents", 2024, "arXiv", "W4393942320", 197, "T",
          "Survey of language-model-based game agents.", False),
         ("BALROG", 2024, "arXiv", "W4404649840", 133, "A",
          "Benchmark finding language and vision-language models still struggle in complex, dynamic games.", False),
         ("lmgame-Bench", 2025, "arXiv", "W4415145236", 56, "T",
          "Asks how good language models are at playing games.", False),
         ("SIMA 2", 2025, "arXiv", "W4417086995", 49, "T",
          "Generalist embodied agent for virtual worlds.", False),
         ("AutoHarness", 2026, "arXiv", "W7133750645", 99, "A",
          "A language model synthesises its own code harness to stop itself making illegal moves.", False),
     ]),
    ("Code world models",
     "The game's rules written as an executable program, which a classical planner (tree search, model-predictive control) "
     "then searches. The program is exact where it is right, fast, and readable, unlike a learned network.",
     "This is what reversing/<game>/py already holds. The field infers the program from play or from a rules text; "
     "this repo extracts it from the 68000 and gates it against the emulator. One paper does the same from a binary "
     "(Super Mario Odyssey, below).",
     []),
]

# Sub-branches, keyed by branch name: (name, what, for this repo, papers)
SUBS = {
    "Code world models": [
        ("Heritage: rules as programs",
         "Before language models: a game described in a small language, or a causal model searched for by program synthesis.",
         "The tick, shot and seeder functions are hand-written members of this family.",
         [
             ("VGDL", 2013, "IEEE CIG", "W2028208918", 264, "A",
              "PyVGDL: a high-level description language for 2D video games, parsed and played at once.", False),
             ("Schema Networks", 2017, "arXiv", "W2624780181", 258, "A",
              "Object-oriented generative physics simulator that reasons backward from goals through causes.", False),
             ("Theory-based RL (EMPA)", 2021, "arXiv", "W3183390056", 101, "T",
              "Human-level learning speed through theory-based modelling, exploration and planning.", False),
             ("AutumnSynth", 2023, "PACMPL", "W4315606137", 19, "A",
              "Synthesises reactive programs from observations of Atari-style grid worlds, adding hidden state where needed.", True),
         ]),
        ("A language model writes the model",
         "The model is generated as Python from interaction traces or a rules text, then checked against sampled transitions.",
         "The method to try on a game that has not been reversed: the emulator supplies unlimited exact transitions to check a candidate against.",
         [
             ("ByteSized32", 2023, "EMNLP", "W4389524188", 26, "A",
              "Language models generating text games as hundreds of lines of Python.", False),
             ("WorldCoder", 2024, "NeurIPS", "W4415796843", 172, "A",
              "Agent that writes a Python program as its world model from interaction, then plans with it.", True),
             ("Code world models + MCTS", 2024, "NeurIPS", "W4415797484", 94, "A",
              "A language model generates the world model as Python code, guided by tree search.", True),
             ("WALL-E", 2024, "arXiv", "W4403364427", 31, "A",
              "A few learned rules align a language model's predictions with one environment's dynamics.", False),
             ("CWM for general game playing", 2025, "arXiv", "W4414946777", 30, "A",
              "Rules and trajectories translated to Python (transition, legal moves, termination) for tree search, plus "
              "inference functions for hidden state; matches or beats Gemini 2.5 Pro on 9 of 10 games.", True),
             ("TheoryCoder (bilevel planning)", 2025, "TMLR", "W4409045958", 23, "A",
              "Theory-based RL with synthesised causal world models used as forward simulators.", False),
             ("Symbolic models, test-time scaling", 2025, "TMLR", "W4407309453", 18, "A",
              "Generates a PDDL world model so classical search can plan.", False),
             ("Finite Automata Extraction", 2026, "FDG", "W4414459514", 1, "A",
              "Learns a world model as programs in a small language from gameplay video.", False),
             ("OPINE-World", 2026, "arXiv", "W7167254436", 15, "A",
              "Extends WorldCoder-style modelling to cases where the symbols and the goal are unknown and changing.", False),
             ("Executable models for ARC-AGI-3", 2026, "AGI", "W7170085180", 20, "T",
              "Executable world models built by coding agents for the ARC-AGI-3 interactive games.", False),
             ("Mind-Studio", 2026, "arXiv", "W7164913627", 0, "A",
              "Synthesises complete pygame-style world models from state-action-next-state traces of partially observable games.", True),
             ("PatchWorld", 2026, "arXiv", "W7163062575", 8, "A",
              "Turns offline trajectories of a black-box text environment into an executable world model, without gradients.", False),
             ("Distilling CWM generation", 2026, "arXiv", "W7162401042", 5, "A",
              "Studies small language models generating game environments as code.", False),
             ("Coding agent as world brain", 2026, "arXiv", "W7204440733", 32, "A",
              "Separates how the world evolves (code) from how it is drawn (a visual model).", False),
         ]),
        ("Is the model right?",
         "How a synthesised model is accepted, and what a passing check does not show.",
         "The gates here are match counts on captured calls and frames (2,346 of 2,346 arrivals), the 'sampling gate' the 2026 paper "
         "warns about: a rule that fires rarely can be absent from the sample. Its remedy is to test on the states the planner "
         "visits, or by play; here that means gating a port on whole recorded games flown by the pilot. Reading the code "
         "instead of inferring it is the other defence, and the repo has it.",
         [
             ("Text2World", 2025, "ACL Findings", "W4412944538", 50, "A",
              "Benchmark for language-model generation of symbolic (PDDL) world models, built to fix indirect and noisy evaluation.", False),
             ("When a verified world model still loses", 2026, "arXiv", "W7169534322", 5, "A",
              "A model at 100% sampled transition accuracy still loses at play: the under-1% it gets wrong is the pivotal rule. "
              "More data did not fix it; adequacy should be measured on the search distribution or by play.", True),
         ]),
        ("From the binary",
         "The program is recovered from the shipped game instead of inferred from its behaviour.",
         "The direct precedent for this repo, and prior art for any post on it. Its simulator is the game's own code, "
         "decompiled to C++ on top of a community project and a release that shipped with symbols, then recompiled natively; "
         "here the code stays in the emulator and each routine gets a separate model. It has two checks. A function "
         "'matches' when recompiling it with the game's compiler gives the same machine code, a proof for every input that "
         "hand-written 68000 has no equivalent of; most functions are only 'functional', checked by watching behaviour. "
         "End to end, 13 scripted moves are replayed on console and simulator and the position compared: 8 agree, 5 drift. "
         "The callcap gates here compare all touched memory on thousands of calls, which is finer, but nothing here yet "
         "replays whole inputs through a composed port, the test that caught their drift. Speed: 84,000 to 144,000 "
         "frames/s compiled with optimisation, against 60 on the console, falling to 363 to 9,993 once observations are "
         "sent to Python.",
         [
             ("LLM4Decompile", 2024, "EMNLP", "W4404783570", 220, "A",
              "Open language models trained to decompile binary code, motivated by Ghidra output being hard to read and execute.", False),
             ("Super Mario Odyssey by decompilation", 2026, "IEEE CoG", "W7233756573", 0, "F",
              "The player-movement and collision code decompiled to C++ and recompiled natively as a simulator (no enemies, "
              "camera or damage); 8 of 13 scripted moves reproduce the console's positions; a PPO agent trained in it is "
              "moved back to the console on one stage.", True),
         ]),
        ("Adjacent: programs as policies and goals",
         "The same idea applied to the controller or the objective instead of the game.",
         "Virus's own autopilot is a programmatic policy, already documented in demo.md.",
         [
             ("PIRL", 2018, "arXiv", "W2796284132", 425, "A",
              "Policies represented in a domain-specific language, so they can be read and verified.", False),
             ("Code as Policies", 2023, "ICRA", "W4383097638", 2458, "A",
              "Code-writing language models repurposed to write robot policy code.", False),
             ("Goals as reward-producing programs", 2025, "Nat. Mach. Intell.", "W4407864826", 35, "T",
              "Goals represented as programs that produce reward.", False),
         ]),
    ],
}

NOT_FOUND = [
    "DIAMOND (diffusion world model, Atari 100K): no record by title; another indexed work's abstract names it.",
    "PoE-World (programmatic world models for Atari): no record by title.",
    "Genie 3: not searched as a paper; Genie (2024) is the indexed record.",
]


def url(wid):
    return "https://openalex.org/" + wid


def rows(out, papers):
    for short, year, venue, wid, cites, basis, line, applies in papers:
        mark = " *" if applies else ""
        out.append(f"| [{short}]({url(wid)}){mark} | {year} | {venue} | {cites:,} | {basis} | {line} |")
    out.append("")


def readme():
    out = []
    out.append("# Game learning: map of the field\n")
    out.append("A reading map of research on learning to play video games, grouped by direction, with what each direction "
               "means for this repo. The same tree is drawn in [field-map.canvas](field-map.canvas) (Obsidian Canvas; "
               "the repo root is the vault). Both files are generated by `build_map.py` from one table: edit that, not these.\n")
    out.append("Whether this emulator can be trusted as the judge of a game model is tested against a second emulator in "
               "[hatari_oracle.md](hatari_oracle.md): eight Virus routines run on Hatari's CPU from this emulator's state, "
               "24/24 calls equal in RAM and registers (`py/gate_hatari_callcap.sh`).\n")
    out.append("Papers were found through OpenAlex title and semantic searches. Citation counts are OpenAlex's on "
               f"{COUNTED}. The **basis** column says where each one-line description comes from: **A** the abstract "
               "OpenAlex returned, **F** the full text, **T** the title alone, **R** a detail recalled from memory and not checked "
               "against the paper (marked `(R)` in the line). Only the papers marked F were read in full.\n")
    out.append("## " + ROOT[0] + "\n")
    out.append(ROOT[1] + "\n")
    out.append("The tree:\n")
    for name, what, _, papers in BRANCHES:
        out.append(f"- **{name}**" + (": " + ", ".join(p[0] for p in papers) if papers else ""))
        for sname, _, _, spapers in SUBS.get(name, []):
            out.append(f"  - **{sname}**: " + ", ".join(p[0] for p in spapers))
    out.append("")
    for name, what, here, papers in BRANCHES:
        out.append(f"## {name}\n")
        out.append(what + "\n")
        out.append(f"**For this repo** (inferred, nothing built): {here}\n")
        if papers:
            out.append("| Paper | Year | Venue | Cited | Basis | What it is |")
            out.append("|---|---|---|---|---|---|")
        rows(out, papers)
        for sname, swhat, shere, spapers in SUBS.get(name, []):
            out.append(f"### {sname}\n")
            out.append(swhat + "\n")
            out.append(f"**For this repo** (inferred, nothing built): {shere}\n")
            out.append("| Paper | Year | Venue | Cited | Basis | What it is |")
            out.append("|---|---|---|---|---|---|")
            rows(out, spapers)
    out.append("`*` marks the papers that bear directly on a decision here.\n")
    out.append("## Not found in OpenAlex\n")
    for n in NOT_FOUND:
        out.append("- " + n)
    out.append("")
    return "\n".join(out)


def canvas():
    LEAF_W, GAP = 460, 20
    BR_W = 420
    X_ROOT, X_BR, X_SUB, X_DEEP = 0, 640, 1260, 1880
    nodes, edges = [], []

    def height(text, width):
        lines = sum(1 + len(part) // max(1, (width - 40) // 8) for part in text.split("\n"))
        return 40 + 26 * lines

    def leaves(parent, papers, x, y):
        for short, year, venue, wid, cites, basis, line, applies in papers:
            nid = f"p{len(nodes)}"
            text = f"**{short}** ({year}, {venue})\n{line}\n[OpenAlex]({url(wid)}) · {cites:,} cites · basis {basis}"
            h = height(text, LEAF_W)
            node = {"id": nid, "type": "text", "x": x, "y": y, "width": LEAF_W, "height": h, "text": text}
            if applies:
                node["color"] = "4"
            nodes.append(node)
            edges.append({"id": "e" + nid, "fromNode": parent, "fromSide": "right", "toNode": nid, "toSide": "left"})
            y += h + GAP
        return y

    def parent_node(nid, text, x, top, bottom, colour, frm):
        h = height(text, BR_W)
        bottom = max(bottom, top + h + GAP)
        centre = (top + bottom - GAP) // 2
        nodes.append({"id": nid, "type": "text", "x": x, "y": centre - h // 2, "width": BR_W, "height": h,
                      "color": colour, "text": text})
        edges.append({"id": "e" + nid, "fromNode": frm, "fromSide": "right", "toNode": nid, "toSide": "left"})
        return bottom, centre

    y = 0
    centres = []
    for bi, (name, what, here, papers) in enumerate(BRANCHES):
        top = y
        y = leaves(f"b{bi}", papers, X_SUB, y)
        for si, (sname, swhat, shere, spapers) in enumerate(SUBS.get(name, [])):
            stop = y
            y = leaves(f"b{bi}s{si}", spapers, X_DEEP, y)
            y, _ = parent_node(f"b{bi}s{si}", f"### {sname}\n{swhat}\n\n**For this repo:** {shere}",
                               X_SUB, stop, y, "3", f"b{bi}")
            y += 40
        y, centre = parent_node(f"b{bi}", f"## {name}\n{what}\n\n**For this repo:** {here}", X_BR, top, y, "5", "root")
        centres.append(centre)
        y += 80
    mid = (centres[0] + centres[-1]) // 2
    nodes.append({"id": "root", "type": "text", "x": X_ROOT, "y": mid - 160, "width": 440, "height": 320, "color": "6",
                  "text": f"# {ROOT[0]}\n{ROOT[1]}"})
    nodes.append({"id": "legend", "type": "text", "x": X_ROOT, "y": mid + 200, "width": 440, "height": 240,
                  "text": "**Legend**\nGreen: bears directly on a decision in this repo.\n"
                          "Basis A: line from the abstract. F: full text read. T: title only. R: recalled, unchecked.\n"
                          f"Citations: OpenAlex, {COUNTED}.\nGenerated by build_map.py; see README.md."})
    return {"nodes": nodes, "edges": edges}


if __name__ == "__main__":
    with open(os.path.join(HERE, "README.md"), "w") as f:
        f.write(readme())
    with open(os.path.join(HERE, "field-map.canvas"), "w") as f:
        json.dump(canvas(), f, indent=1)
    n = sum(len(b[3]) for b in BRANCHES) + sum(len(x[3]) for v in SUBS.values() for x in v)
    print(f"{len(BRANCHES)} branches, {n} papers")
