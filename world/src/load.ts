// Load generator for an episode: sends a steady stream of orders to the API.
// Every order the API acknowledges (HTTP 201) is appended to ledger.jsonl, and
// load.json is rewritten each second with counts and a heartbeat. Graders use
// them to prove no acknowledged write was lost and that load never stopped.
// Run as `node src/load.ts <episode-dir> [requests-per-second]`.

import { appendFileSync, existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";

const dir = process.argv[2];
if (!dir) {
  console.error("usage: node src/load.ts <episode-dir> [requests-per-second]");
  process.exit(2);
}

const rate = Number(process.argv[3] ?? 20);
const ledger = join(dir, "ledger.jsonl");
const counts = { sent: 0, acked: 0, failed: 0 };

async function waitForPort(): Promise<number> {
  const file = join(dir, "api.port");
  for (let i = 0; i < 200; i++) {
    if (existsSync(file)) return Number(readFileSync(file, "utf8"));
    await sleep(50);
  }
  throw new Error("api.port never appeared");
}

async function sendOrder(port: number, n: number): Promise<void> {
  const amount = 100 + ((n * 7919) % 50_000);
  try {
    const res = await fetch(`http://127.0.0.1:${port}/orders`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ customer: `load-${n % 500}`, amount_cents: amount }),
      signal: AbortSignal.timeout(5000),
    });
    const body = (await res.json()) as { order_id?: number };
    if (res.status === 201 && body.order_id) {
      appendFileSync(ledger, `${JSON.stringify({ order_id: body.order_id, amount_cents: amount })}\n`);
      counts.acked++;
    } else {
      counts.failed++;
    }
  } catch {
    counts.failed++;
  }
}

function heartbeat(): void {
  writeFileSync(join(dir, "load.json"), JSON.stringify({ ...counts, rate, heartbeat: Date.now() }));
}

const port = await waitForPort();
console.log(`${new Date().toISOString()} load sending ${rate} orders/s to port ${port}`);
heartbeat();
setInterval(heartbeat, 1000);
for (;;) {
  counts.sent++;
  void sendOrder(port, counts.sent);
  await sleep(1000 / rate);
}
