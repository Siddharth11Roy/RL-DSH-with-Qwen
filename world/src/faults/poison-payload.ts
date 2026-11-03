// Fault: a new "v2" client sends jobs whose payload says orderId instead of
// order_id. The worker cannot find the order, retries three times and parks
// each job in the dead-letter state. A fix rewrites the payloads (json_extract,
// json_object) and requeues the dead jobs so every v2 order is processed once.

import { join } from "node:path";
import { openDb, tx } from "../db.ts";
import { waitFor } from "../proc.ts";
import { between, type Fault } from "./types.ts";

export const poisonPayload: Fault = {
  name: "poison-payload",
  summary: "v2 client jobs use orderId instead of order_id and land in the dead-letter queue",
  async inject({ dir, rand }) {
    const db = openDb(join(dir, "app.db"));
    const count = between(rand, 6, 18);
    const orderIds: number[] = [];
    const jobIds: number[] = [];
    const addOrder = db.prepare(
      "INSERT INTO orders (customer, amount_cents) VALUES (?, ?) RETURNING id",
    );
    const addJob = db.prepare(
      "INSERT INTO jobs (kind, payload) VALUES ('process_order', ?) RETURNING id",
    );
    tx(db, () => {
      for (let i = 0; i < count; i++) {
        const { id } = addOrder.get(`client-v2-${i}`, between(rand, 500, 40_000)) as { id: number };
        orderIds.push(id);
        jobIds.push((addJob.get(JSON.stringify({ orderId: id, v: 2 })) as { id: number }).id);
      }
    });
    const placeholders = jobIds.map(() => "?").join(",");
    const dead = db.prepare(`SELECT count(*) AS n FROM jobs WHERE status = 'dead' AND id IN (${placeholders})`);
    const allDead = await waitFor(() => (dead.get(...jobIds) as { n: number }).n === count, 20_000);
    db.close();
    if (!allDead) throw new Error("poison jobs did not reach the dead-letter state");
    return {
      alert: `The dead-letter queue has ${count} jobs since the v2 mobile client launched; ` +
        "those customers' orders are not being processed.",
      secret: { order_ids: orderIds, job_ids: jobIds },
    };
  },
};
