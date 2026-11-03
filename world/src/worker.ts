// Worker process of the practice app: drains the job queue and writes results.
// A process_order job reads its order, adds tax, inserts a results row and
// marks the job done, all in one transaction. Any error sends the job back for
// a retry (or to the dead-letter state). Settings come from config.json at start.
// Run as `node src/worker.ts <episode-dir> [id]`.

import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { errorMessage, openDb, tx } from "./db.ts";
import { claim, complete, fail, type Job } from "./queue.ts";
import { TAX_RATE } from "./seed.ts";
import { readConfig } from "./config.ts";

const dir = process.argv[2];
if (!dir) {
  console.error("usage: node src/worker.ts <episode-dir> [worker-id]");
  process.exit(2);
}

const workerId = process.argv[3] ?? `worker-${process.pid}`;
const config = readConfig(dir);
if (!Number.isInteger(config.worker_batch_size) || config.worker_batch_size < 1) {
  throw new Error(`invalid worker_batch_size ${config.worker_batch_size} in config.json`);
}
const db = openDb(join(dir, "app.db"), { busyTimeoutMs: config.busy_timeout_ms });
const getOrder = db.prepare("SELECT id, amount_cents FROM orders WHERE id = ?");
const addResult = db.prepare(
  "INSERT INTO results (order_id, job_id, total_cents) VALUES (?, ?, ?)",
);
const markOrder = db.prepare("UPDATE orders SET status = 'processed' WHERE id = ?");

function log(message: string): void {
  console.log(`${new Date().toISOString()} ${workerId} ${message}`);
}

function handle(job: Job): void {
  if (job.kind !== "process_order") throw new Error(`unknown job kind: ${job.kind}`);
  const { order_id: orderId } = JSON.parse(job.payload) as { order_id: number };
  const order = getOrder.get(orderId) as { id: number; amount_cents: number } | undefined;
  if (!order) throw new Error(`order ${orderId} not found`);
  tx(db, () => {
    addResult.run(order.id, job.id, Math.round(order.amount_cents * TAX_RATE));
    markOrder.run(order.id);
    complete(db, job.id);
  });
}

function runOne(): boolean {
  let job: Job | undefined;
  try {
    job = claim(db, workerId);
  } catch (err) {
    log(`claim failed: ${errorMessage(err)}`);
    return false;
  }
  if (!job) return false;
  try {
    handle(job);
  } catch (err) {
    const status = fail(db, job.id, errorMessage(err));
    log(`job ${job.id} failed, now ${status}: ${errorMessage(err)}`);
  }
  return true;
}

log(`started (batch ${config.worker_batch_size}, busy_timeout ${config.busy_timeout_ms} ms)`);
for (;;) {
  let worked = 0;
  for (let i = 0; i < config.worker_batch_size; i++) worked += runOne() ? 1 : 0;
  if (worked === 0) await sleep(config.worker_poll_ms);
}
