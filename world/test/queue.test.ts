// Tests for the job queue's state machine on a throwaway database.
// Covers claim order, that a claimed job is never handed out twice, retries
// returning a job to pending, the dead-letter cut-off after MAX_ATTEMPTS,
// requeueing dead jobs, cancelling and the per-status counts.

import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { initSchema, openDb, type Db } from "../src/db.ts";
import * as queue from "../src/queue.ts";

function withDb(fn: (db: Db) => void): void {
  const dir = mkdtempSync(join(tmpdir(), "rlh-queue-"));
  const db = openDb(join(dir, "app.db"));
  initSchema(db);
  try {
    fn(db);
  } finally {
    db.close();
    rmSync(dir, { recursive: true, force: true });
  }
}

test("claims jobs in order and never twice", () => withDb((db) => {
  const a = queue.enqueue(db, "process_order", { order_id: 1 });
  const b = queue.enqueue(db, "process_order", { order_id: 2 });
  assert.equal(queue.claim(db, "w1")?.id, a);
  assert.equal(queue.claim(db, "w2")?.id, b);
  assert.equal(queue.claim(db, "w1"), undefined);
}));

test("failed jobs retry, then land in the dead-letter state", () => withDb((db) => {
  const id = queue.enqueue(db, "process_order", { order_id: 1 });
  for (let attempt = 1; attempt < queue.MAX_ATTEMPTS; attempt++) {
    queue.claim(db, "w1");
    assert.equal(queue.fail(db, id, "boom"), "pending");
  }
  queue.claim(db, "w1");
  assert.equal(queue.fail(db, id, "boom"), "dead");
  assert.equal(queue.stats(db).dead, 1);
  assert.equal(queue.requeueDead(db), 1);
  assert.equal(queue.claim(db, "w1")?.attempts, 1);
}));

test("cancel stops pending and running jobs only", () => withDb((db) => {
  const id = queue.enqueue(db, "process_order", { order_id: 1 });
  queue.claim(db, "w1");
  assert.equal(queue.cancel(db, id), true);
  assert.equal(queue.cancel(db, id), false);
  queue.complete(db, queue.enqueue(db, "process_order", { order_id: 2 }));
  assert.deepEqual(queue.stats(db), { pending: 0, running: 0, done: 1, dead: 0, cancelled: 1 });
}));
