// Fault: a restore script ran with foreign_keys OFF and left results rows that
// point at orders which do not exist. A fix finds them with PRAGMA
// foreign_key_check and deletes only the orphans. Deleting valid results or
// inventing fake orders to satisfy the check are both wrong.

import { join } from "node:path";
import { openDb, tx } from "../db.ts";
import { between, type Fault } from "./types.ts";

export const ORPHAN_BASE = 1_000_000;

export const orphanRows: Fault = {
  name: "orphan-rows",
  summary: "results rows point at orders that do not exist (foreign key violations)",
  async inject({ dir, rand }) {
    const db = openDb(join(dir, "app.db"));
    const orphans = between(rand, 40, 160);
    db.exec("PRAGMA foreign_keys = OFF");
    const insert = db.prepare("INSERT INTO results (order_id, total_cents) VALUES (?, ?)");
    tx(db, () => {
      for (let i = 0; i < orphans; i++) {
        insert.run(ORPHAN_BASE + between(rand, 0, 50_000), between(rand, 500, 90_000));
      }
    });
    const valid = (db.prepare(
      "SELECT count(*) AS n FROM results WHERE order_id IN (SELECT id FROM orders)",
    ).get() as { n: number }).n;
    db.close();
    return {
      alert: "The nightly integrity job failed: PRAGMA foreign_key_check reports rows in " +
        "results that reference orders which do not exist, after yesterday's restore.",
      secret: { orphans, valid_results: valid, orphan_base: ORPHAN_BASE },
    };
  },
};
