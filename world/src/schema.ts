// Table definitions for the practice app's SQLite database.
// orders are what customers place, jobs is the work queue the worker drains,
// and results holds one computed total per processed order. results has no
// unique key on purpose, so a job that runs twice leaves visible duplicates.

const NOW = "(strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))";

export const SCHEMA = `
CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY,
  customer TEXT NOT NULL,
  amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
  status TEXT NOT NULL DEFAULT 'new',
  created_at TEXT NOT NULL DEFAULT ${NOW}
);

CREATE TABLE IF NOT EXISTS jobs (
  id INTEGER PRIMARY KEY,
  kind TEXT NOT NULL,
  payload TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'running', 'done', 'dead', 'cancelled')),
  attempts INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  locked_by TEXT,
  locked_at TEXT,
  created_at TEXT NOT NULL DEFAULT ${NOW},
  updated_at TEXT NOT NULL DEFAULT ${NOW}
);

CREATE INDEX IF NOT EXISTS jobs_by_status ON jobs (status, id);

CREATE TABLE IF NOT EXISTS results (
  id INTEGER PRIMARY KEY,
  order_id INTEGER NOT NULL REFERENCES orders (id),
  job_id INTEGER REFERENCES jobs (id),
  total_cents INTEGER NOT NULL,
  processed_at TEXT NOT NULL DEFAULT ${NOW}
);

CREATE INDEX IF NOT EXISTS results_by_order ON results (order_id);
`;
