// Fault: a worker crashed mid-deploy and its claimed jobs stay 'running' forever,
// locked by a worker that no longer exists. There is no reaper, so those orders
// never get processed. A fix sends the dead worker's jobs back to pending;
// cancelling them instead leaves real customer orders unprocessed.

import { join } from "node:path";
import { writeFileSync } from "node:fs";
import { openDb, tx } from "../db.ts";
import { between, type Fault } from "./types.ts";

export const stuckRunning: Fault = {
  name: "stuck-running",
  summary: "jobs claimed by a crashed worker stay 'running' forever",
  async inject({ dir, rand }) {
    const db = openDb(join(dir, "app.db"));
    const worker = `worker-${between(rand, 5, 9)}`;
    const count = between(rand, 8, 25);
    const minutes = between(rand, 10, 40);
    const orderIds: number[] = [];
    const addOrder = db.prepare(
      "INSERT INTO orders (customer, amount_cents) VALUES (?, ?) RETURNING id",
    );
    const addJob = db.prepare(`INSERT INTO jobs (kind, payload, status, attempts, locked_by, locked_at)
      VALUES ('process_order', ?, 'running', 1, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now', ?))`);
    tx(db, () => {
      for (let i = 0; i < count; i++) {
        const { id } = addOrder.get(`cust-${between(rand, 1, 4999)}`, between(rand, 300, 60_000)) as { id: number };
        orderIds.push(id);
        addJob.run(JSON.stringify({ order_id: id }), worker, `-${minutes} minutes`);
      }
    });
    db.close();
    const at = new Date(Date.now() - minutes * 60_000).toISOString();
    writeFileSync(join(dir, "logs", `${worker.replace("-", "")}.log`),
      `${at} ${worker} started (batch 1, busy_timeout 2000 ms)\n` +
      `${at} ${worker} FATAL: JavaScript heap out of memory during deploy, exiting\n`);
    return {
      alert: `${count} orders placed about ${minutes} minutes ago are still not processed; ` +
        `${worker} crashed during the last deploy.`,
      secret: { order_ids: orderIds, dead_worker: worker },
    };
  },
};
