# RL-DSH-with-Qwen

A small terminal coding agent, `rlh`, whose tool-calling policy is trained with reinforcement learning.
The agent's brain is Qwen with a LoRA adapter. It practises on a deliberately broken app
(SQLite in WAL mode behind a TypeScript job queue), and a grader scores every attempt.

## The pieces

| Part | What it is | Trained? |
|---|---|---|
| Policy | Qwen3 + LoRA adapter | Yes: SFT warm-up, then GRPO |
| Harness (`rlh`) | Our terminal agent: tool loop, tools, trajectory logging | No |
| Practice world | TypeScript API, job queue and worker on SQLite (WAL), with injected faults | No |
| Graders | Check the real end state of the app after each episode | No |
| DeepSeek Harness | Downloaded at a pinned commit, used to test whether the policy transfers | No |

## Layout

```
src/rlh/      the agent and its command line (Python)
world/        the practice app the agent learns to fix, and its faults (TypeScript)
src/rlh/graders/  scores an episode from outside its folder (Python)
configs/      default settings, sized for a 6 GB GPU
scripts/      fetch DeepSeek Harness, GPU smoke test
tests/        pytest suite
docs/         setup notes and write-ups
vendor/       third-party harnesses, git-ignored, fetched by script
runs/         episode folders and logs, git-ignored
```

## Quick start

```bash
uv sync
uv run rlh doctor
npm install
npm run smoke
uv run python scripts/fetch_dsh.py
```

Training runs inside WSL2 because vLLM does not support native Windows. See [docs/setup-wsl.md](docs/setup-wsl.md).

## Hardware

Developed on an RTX 3050 6 GB laptop GPU. The default policy is Qwen3-1.7B loaded in 4-bit,
with small GRPO groups and short episodes so everything fits in 6 GB.

## Roadmap

- [x] Phase 0: repo, tooling, pinned DeepSeek Harness, GPU check
- [x] Phase 1: practice world (API, queue, worker, load generator), see [world/README.md](world/README.md)
- [x] Phase 2: fault templates and graders (8 faults), see [docs/faults.md](docs/faults.md)
- [ ] Phase 3: the `rlh` agent loop and tools
- [ ] Phase 4: baselines before training
- [ ] Phase 5: SFT warm-up
- [ ] Phase 6: GRPO
- [ ] Phase 7: reward-hacking audit
- [ ] Phase 8: memory module (optional)
- [ ] Phase 9: transfer test inside DeepSeek Harness
- [ ] Phase 10: write-up

## License

MIT
