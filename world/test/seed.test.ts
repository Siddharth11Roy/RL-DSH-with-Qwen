// Tests for the deterministic seeder and its checksum.
// The same seed must give the same fingerprint, a different seed a different
// one, and any lost, edited or duplicated seeded row must change it. That is
// what lets graders prove the agent did not damage the starting data.

import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { openDb, type Db } from "../src/db.ts";
import { checksum, seed } from "../src/seed.ts";

const ROWS = 500;

function seeded(seedValue: number, fn: (db: Db) => void): void {
  const dir = mkdtempSync(join(tmpdir(), "rlh-seed-"));
  const db = openDb(join(dir, "app.db"));
  try {
    seed(db, ROWS, seedValue);
    fn(db);
  } finally {
    db.close();
    rmSync(dir, { recursive: true, force: true });
  }
}

test("same seed gives the same checksum, different seed does not", () => {
  let first = "";
  let second = "";
  let other = "";
  seeded(7, (db) => { first = checksum(db, ROWS); });
  seeded(7, (db) => { second = checksum(db, ROWS); });
  seeded(8, (db) => { other = checksum(db, ROWS); });
  assert.equal(first, second);
  assert.notEqual(first, other);
});

test("losing, editing or duplicating a seeded row changes the checksum", () => {
  const damage = [
    "DELETE FROM results WHERE order_id = 42",
    "UPDATE orders SET amount_cents = amount_cents + 1 WHERE id = 7",
    "INSERT INTO results (order_id, total_cents) VALUES (3, 1)",
  ];
  for (const sql of damage) {
    seeded(7, (db) => {
      const before = checksum(db, ROWS);
      db.exec(sql);
      assert.notEqual(checksum(db, ROWS), before, sql);
    });
  }
});

test("rows added after seeding do not affect the checksum", () => seeded(7, (db) => {
  const before = checksum(db, ROWS);
  db.exec("INSERT INTO orders (customer, amount_cents) VALUES ('late', 500)");
  assert.equal(checksum(db, ROWS), before);
}));
