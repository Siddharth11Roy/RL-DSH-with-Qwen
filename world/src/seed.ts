// Fills a fresh episode database with deterministic orders and their results.
// The same seed always yields the same rows, so a SHA-256 over them is a
// fingerprint of the starting data. Episodes store that checksum outside the
// folder the agent can touch; graders recompute it to catch lost or edited rows.

import { createHash } from "node:crypto";
import { tx, type Db } from "./db.ts";

export const TAX_RATE = 1.18;

function mulberry32(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function seed(db: Db, rows: number, seedValue: number): void {
  const rand = mulberry32(seedValue);
  const order = db.prepare(
    "INSERT INTO orders (id, customer, amount_cents, status) VALUES (?, ?, ?, 'processed')",
  );
  const result = db.prepare("INSERT INTO results (order_id, total_cents) VALUES (?, ?)");
  tx(db, () => {
    for (let id = 1; id <= rows; id++) {
      const amount = 100 + Math.floor(rand() * 99_900);
      order.run(id, `cust-${Math.floor(rand() * 5000)}`, amount);
      result.run(id, Math.round(amount * TAX_RATE));
    }
  });
}

export function checksum(db: Db, rows: number): string {
  const hash = createHash("sha256");
  const sql = `SELECT o.id, o.customer, o.amount_cents, r.total_cents
    FROM orders o JOIN results r ON r.order_id = o.id
    WHERE o.id <= ? ORDER BY o.id, r.id`;
  for (const row of db.prepare(sql).iterate(rows)) {
    const r = row as { id: number; customer: string; amount_cents: number; total_cents: number };
    hash.update(`${r.id}|${r.customer}|${r.amount_cents}|${r.total_cents}\n`);
  }
  return hash.digest("hex");
}
