// End-to-end test: six episodes run side by side on one machine.
// Each gets its own folder, port and processes. After a few seconds of load
// we stop them all and check that every acknowledged order is in the database,
// the seeded data is untouched, and no process from any episode is left running.

import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { openDb } from "../src/db.ts";
import { checksum } from "../src/seed.ts";
import { isAlive } from "../src/proc.ts";
import { createEpisode, readPids, secretDir, startEpisode, stopEpisode } from "../src/episode.ts";

const EPISODES = 6;
const ROWS = 1000;

function ledger(dir: string): { order_id: number; amount_cents: number }[] {
  return readFileSync(join(dir, "ledger.jsonl"), "utf8").trim().split("\n").map((l) => JSON.parse(l));
}

test("six episodes run in parallel without losing writes or leaking processes", async () => {
  const root = mkdtempSync(join(tmpdir(), "rlh-episodes-"));
  const dirs = Array.from({ length: EPISODES }, (_, i) => join(root, `ep${i}`));
  const sums = dirs.map((dir, i) => createEpisode(dir, { rows: ROWS, seed: i + 1 }));
  const started = Date.now();
  const pids = await Promise.all(dirs.map((dir) => startEpisode(dir, { rate: 15 })));
  const startMs = Date.now() - started;
  try {
    await sleep(4000);
  } finally {
    dirs.forEach(stopEpisode);
  }
  await sleep(500);

  for (const [i, dir] of dirs.entries()) {
    const acked = ledger(dir);
    assert.ok(acked.length > 10, `episode ${i} acknowledged only ${acked.length} orders`);
    const db = openDb(join(dir, "app.db"));
    const find = db.prepare("SELECT amount_cents FROM orders WHERE id = ?");
    for (const entry of acked) {
      const row = find.get(entry.order_id) as { amount_cents: number } | undefined;
      assert.equal(row?.amount_cents, entry.amount_cents, `episode ${i} lost order ${entry.order_id}`);
    }
    assert.equal(checksum(db, ROWS), sums[i], `episode ${i} seeded data changed`);
    db.close();
    assert.deepEqual(readPids(dir), {});
    for (const pid of Object.values(pids[i])) assert.equal(isAlive(pid), false, `pid ${pid} leaked`);
  }

  console.log(`started ${EPISODES} episodes in ${startMs} ms`);
  rmSync(root, { recursive: true, force: true });
  dirs.forEach((dir) => rmSync(secretDir(dir), { recursive: true, force: true }));
});
