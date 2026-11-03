# Practice world

A small order-processing app the `rlh` agent learns to fix. Every episode runs in its own folder
with its own SQLite database, processes and port, so many episodes can run side by side.

```
load generator ──► API (POST /orders) ──► jobs table ──► worker ──► results
   ledger.jsonl        api.port              SQLite in WAL mode (app.db + app.db-wal)
```

## Files

| File | Role |
|---|---|
| `src/schema.ts`, `src/db.ts` | Tables and the shared connection settings (WAL, busy timeout) |
| `src/queue.ts` | Job queue: claim, complete, retry, dead-letter, cancel |
| `src/seed.ts` | Deterministic starting data and its SHA-256 fingerprint |
| `src/api.ts` | `POST /orders`, `GET /health`, `GET /stats` |
| `src/worker.ts` | Drains the queue and writes results |
| `src/load.ts` | Steady order traffic; records every acknowledged order |
| `src/proc.ts`, `src/episode.ts` | Start and stop an episode's processes as whole trees |
| `src/episode-cli.ts` | `create`, `start`, `stop`, `status` |
| `src/queue-cli.ts` | Operator view of the queue; becomes the agent's `queue` tool |

## Episode folder

```
runs/<name>/          what the agent can see and change
  app.db, app.db-wal  the database
  logs/               api.log, worker1.log, load.log
  ledger.jsonl        every order the API acknowledged
  load.json           load counters and heartbeat
  episode.json        rows and seed used
runs/<name>.secret/   graders only
  checksum.json       fingerprint of the seeded data
```

## Commands

```bash
uv run rlh world create demo --rows 2000 --seed 3
uv run rlh world start demo --rate 25
uv run rlh world status demo
node --disable-warning=ExperimentalWarning world/src/queue-cli.ts runs/demo list
uv run rlh world stop demo
npm run test:world
```

## Performance note

On Windows each new Node process takes about 1.5 s to start (mostly antivirus scanning),
so starting six episodes at once takes about 20 s. Training runs in WSL2, where process start-up
is much cheaper, and later phases reuse warm episodes instead of restarting them.
