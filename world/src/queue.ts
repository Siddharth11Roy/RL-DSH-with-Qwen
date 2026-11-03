// SQLite-backed job queue: the API enqueues, the worker claims and finishes.
// Jobs move pending -> running -> done, or back to pending on failure until
// MAX_ATTEMPTS, after which they land in the dead-letter state ('dead').
// claim() is one atomic UPDATE ... RETURNING, so two workers never share a job.

import type { Db } from "./db.ts";

export const MAX_ATTEMPTS = 3;
export const STATUSES = ["pending", "running", "done", "dead", "cancelled"] as const;
export type JobStatus = (typeof STATUSES)[number];

export interface Job {
  id: number;
  kind: string;
  payload: string;
  status: JobStatus;
  attempts: number;
}

const NOW = "strftime('%Y-%m-%dT%H:%M:%fZ', 'now')";

export function enqueue(db: Db, kind: string, payload: unknown): number {
  const sql = "INSERT INTO jobs (kind, payload) VALUES (?, ?) RETURNING id";
  const row = db.prepare(sql).get(kind, JSON.stringify(payload)) as { id: number };
  return row.id;
}

export function claim(db: Db, worker: string): Job | undefined {
  const sql = `UPDATE jobs
    SET status = 'running', attempts = attempts + 1, locked_by = ?, locked_at = ${NOW},
        updated_at = ${NOW}
    WHERE id = (SELECT id FROM jobs WHERE status = 'pending' ORDER BY id LIMIT 1)
    RETURNING id, kind, payload, status, attempts`;
  return db.prepare(sql).get(worker) as Job | undefined;
}

export function complete(db: Db, id: number): void {
  const sql = `UPDATE jobs SET status = 'done', locked_by = NULL, updated_at = ${NOW} WHERE id = ?`;
  db.prepare(sql).run(id);
}

export function fail(db: Db, id: number, error: string): JobStatus {
  const sql = `UPDATE jobs
    SET status = CASE WHEN attempts >= ? THEN 'dead' ELSE 'pending' END,
        last_error = ?, locked_by = NULL, updated_at = ${NOW}
    WHERE id = ? RETURNING status`;
  const row = db.prepare(sql).get(MAX_ATTEMPTS, error, id) as { status: JobStatus };
  return row.status;
}

export function cancel(db: Db, id: number): boolean {
  const sql = `UPDATE jobs SET status = 'cancelled', locked_by = NULL, updated_at = ${NOW}
    WHERE id = ? AND status IN ('pending', 'running')`;
  return Number(db.prepare(sql).run(id).changes) > 0;
}

export function requeueDead(db: Db): number {
  const sql = `UPDATE jobs SET status = 'pending', attempts = 0, last_error = NULL,
    updated_at = ${NOW} WHERE status = 'dead'`;
  return Number(db.prepare(sql).run().changes);
}

export function stats(db: Db): Record<JobStatus, number> {
  const counts = Object.fromEntries(STATUSES.map((s) => [s, 0])) as Record<JobStatus, number>;
  const rows = db.prepare("SELECT status, count(*) AS n FROM jobs GROUP BY status").all();
  for (const row of rows as { status: JobStatus; n: number }[]) counts[row.status] = row.n;
  return counts;
}
