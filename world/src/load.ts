// Load generator for an episode: sends a steady stream of orders to the API.
// Every order the API acknowledges (HTTP 201) is appended to ledger.jsonl, and
// load.json is rewritten each second with totals, the last 5 s of successes and
// failures, and a heartbeat. It re-reads api.port, so traffic survives an API
// restart. Run as `node src/load.ts <episode-dir> [requests-per-second]`.

import { appendFileSync, existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";

const dir = process.argv[2];
if (!dir) {
  console.error("usage: node src/load.ts <episode-dir> [requests-per-second]");
  process.exit(2);
}

const WINDOW_MS = 5000;
const rate = Number(process.argv[3] ?? 20);
const ledger = join(dir, "ledger.jsonl");
const portFile = join(dir, "api.port");
const counts = { sent: 0, acked: 0, failed: 0 };
const recent: { at: number; ok: boolean }[] = [];
let port = 0;

function readPort(): number {
  return existsSync(portFile) ? Number(readFileSync(portFile, "utf8")) || port : port;
}

function record(ok: boolean): void {
  if (ok) counts.acked++;
  else counts.failed++;
  recent.push({ at: Date.now(), ok });
}

async function sendOrder(n: number): Promise<void> {
  const amount = 100 + ((n * 7919) % 50_000);
  try {
    const res = await fetch(`http://127.0.0.1:${port}/orders`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ customer: `load-${n % 500}`, amount_cents: amount }),
      signal: AbortSignal.timeout(5000),
    });
    const body = (await res.json()) as { order_id?: number };
    const ok = res.status === 201 && body.order_id !== undefined;
    if (ok) appendFileSync(ledger, `${JSON.stringify({ order_id: body.order_id, amount_cents: amount })}\n`);
    record(ok);
  } catch {
    record(false);
  }
}

function heartbeat(): void {
  port = readPort();
  while (recent.length > 0 && recent[0].at < Date.now() - WINDOW_MS) recent.shift();
  const window = {
    acked_recent: recent.filter((r) => r.ok).length,
    failed_recent: recent.filter((r) => !r.ok).length,
  };
  const state = { ...counts, ...window, rate, port, heartbeat: Date.now() };
  writeFileSync(join(dir, "load.json"), JSON.stringify(state));
}

for (let i = 0; i < 200 && !existsSync(portFile); i++) await sleep(50);
port = readPort();
if (!port) throw new Error("api.port never appeared");
console.log(`${new Date().toISOString()} load sending ${rate} orders/s to port ${port}`);
heartbeat();
setInterval(heartbeat, 1000);
for (;;) {
  counts.sent++;
  void sendOrder(counts.sent);
  await sleep(1000 / rate);
}
