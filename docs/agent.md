# The rlh agent

`rlh` is a small terminal agent. Each turn it asks a model for exactly one tool call, runs it
inside the episode folder, and feeds the result back, until the model calls `finish` or the
turn budget (12 by default) runs out. The same loop is used for teacher runs, baselines and RL.

## Tools

| Tool | What it does |
|---|---|
| `shell` | Runs a bash command in the episode folder (30 s timeout) |
| `sql` | Runs one SQL statement on `app.db` in autocommit mode, shows up to 50 rows |
| `logs` | Last N lines of a service log (`api`, `worker1`, `load`, `report`, ...) |
| `queue` | `stats`, `list [status]`, `show <id>`, `cancel <id>`, `requeue-dead` |
| `svc` | `status`, `start`/`stop <name>`, `restart <name or all>` (never the load generator) |
| `read_file` / `edit_file` | Read a file, or replace text that appears exactly once |
| `finish` | Ends the episode with a summary |

Every output is cut to 1,500 characters, keeping the head and the tail. Paths cannot leave the
episode folder, and anything mentioning the grader's `.secret` folder is refused.

## Turn rules

- One tool call per turn. Extra calls in the same reply are answered as skipped.
- A reply with no tool call, invalid JSON arguments or an unknown tool still uses up the turn.
- The episode ends on `finish`, at the turn budget, or on a backend error.

## Running it

With any OpenAI-compatible server (a teacher API, or Qwen served by vLLM):

```bash
export RLH_API_KEY=...
uv run rlh run wal-growth --seed 3 --model <model-name> --base-url <https://.../v1>
```

Without a model, replaying a reference solution:

```bash
uv run rlh run wal-growth --seed 3 --scripted examples/solutions/wal-growth.json
```

Each run prints every turn, every graded check and the reward, and saves the trajectory to
`runs/trajectories/<fault>-s<seed>-<time>.json`, with a summary line in `index.jsonl`.
The saved `messages` are in OpenAI chat format, ready for SFT and GRPO.

## Known gap

The `.secret` guard is a string check. A determined shell command (for example a glob) could
still read the grader's files on the same machine. Real isolation comes from running episodes
as a separate user inside WSL2, which is part of the reward-hacking audit in Phase 7.
