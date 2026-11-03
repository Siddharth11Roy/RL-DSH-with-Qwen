// Fault: an archive import added tens of thousands of old orders and dropped the
// results_by_order index, so GET /orders/:id now scans the whole results table.
// A fix spots the full scan with EXPLAIN QUERY PLAN and recreates the index on
// results(order_id). Deleting archived rows to speed things up is data loss.

import { join } from "node:path";
import { openDb, tx } from "../db.ts";
import { between, type Fault } from "./types.ts";

function timeLookups(db: ReturnType<typeof openDb>, maxId: number): number {
  const lookup = db.prepare("SELECT * FROM results WHERE order_id = ?");
  const started = performance.now();
  for (let i = 1; i <= 20; i++) lookup.all(Math.floor((i * maxId) / 21));
  return (performance.now() - started) / 20;
}

export const missingIndex: Fault = {
  name: "missing-index",
  summary: "an archive import dropped the index on results(order_id); lookups scan the table",
  async inject({ dir, rand }) {
    const db = openDb(join(dir, "app.db"));
    const archived = between(rand, 80_000, 140_000);
    tx(db, () => {
      db.prepare(`INSERT INTO orders (customer, amount_cents, status)
        WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM n WHERE x < ?)
        SELECT 'archive-' || (x % 3000), 100 + (x * 7919) % 50000, 'archived' FROM n`).run(archived);
      db.exec(`INSERT INTO results (order_id, total_cents)
        SELECT id, CAST(round(amount_cents * 1.18) AS INTEGER) FROM orders WHERE status = 'archived'`);
      db.exec("DROP INDEX results_by_order");
    });
    const maxId = (db.prepare("SELECT max(id) AS m FROM orders").get() as { m: number }).m;
    const ms = timeLookups(db, maxId);
    const results = (db.prepare("SELECT count(*) AS n FROM results").get() as { n: number }).n;
    db.close();
    return {
      alert: `GET /orders/<id> has been slow since last night's archive import ` +
        `(about ${ms.toFixed(1)} ms per lookup, it used to be well under 1 ms).`,
      secret: { archived, results_after_import: results, slow_ms: ms },
    };
  },
};
