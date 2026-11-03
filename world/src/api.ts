// HTTP API of the practice app, the front door for the load generator and agent.
// POST /orders stores an order and enqueues its process_order job in one
// transaction; GET /health and GET /stats report liveness, WAL size and queue
// counts. Run as `node src/api.ts <episode-dir>`; it picks a free port and
// writes it to <episode-dir>/api.port.

import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { existsSync, statSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { errorMessage, openDb, tx } from "./db.ts";
import { enqueue, stats } from "./queue.ts";

const dir = process.argv[2];
if (!dir) {
  console.error("usage: node src/api.ts <episode-dir>");
  process.exit(2);
}

const dbFile = join(dir, "app.db");
const db = openDb(dbFile);
const insertOrder = db.prepare(
  "INSERT INTO orders (customer, amount_cents) VALUES (?, ?) RETURNING id",
);

function walBytes(): number {
  const wal = `${dbFile}-wal`;
  return existsSync(wal) ? statSync(wal).size : 0;
}

function send(res: ServerResponse, code: number, body: unknown): void {
  res.writeHead(code, { "content-type": "application/json" });
  res.end(JSON.stringify(body));
}

async function readJson(req: IncomingMessage): Promise<Record<string, unknown>> {
  let raw = "";
  for await (const chunk of req) raw += chunk;
  return JSON.parse(raw || "{}") as Record<string, unknown>;
}

function placeOrder(customer: string, amount: number): number {
  return tx(db, () => {
    const { id } = insertOrder.get(customer, amount) as { id: number };
    enqueue(db, "process_order", { order_id: id });
    return id;
  });
}

const server = createServer(async (req, res) => {
  try {
    if (req.method === "POST" && req.url === "/orders") {
      const body = await readJson(req);
      const { customer, amount_cents: amount } = body;
      if (typeof customer !== "string" || !Number.isInteger(amount) || (amount as number) <= 0) {
        return send(res, 400, { error: "need customer (string) and amount_cents (int > 0)" });
      }
      return send(res, 201, { order_id: placeOrder(customer, amount as number) });
    }
    if (req.method === "GET" && req.url === "/health") {
      return send(res, 200, { ok: true, wal_bytes: walBytes() });
    }
    if (req.method === "GET" && req.url === "/stats") {
      return send(res, 200, { queue: stats(db), wal_bytes: walBytes() });
    }
    send(res, 404, { error: "not found" });
  } catch (err) {
    console.error(`${new Date().toISOString()} ${req.method} ${req.url} failed: ${errorMessage(err)}`);
    send(res, 503, { error: errorMessage(err) });
  }
});

server.listen(0, "127.0.0.1", () => {
  const { port } = server.address() as { port: number };
  writeFileSync(join(dir, "api.port"), String(port));
  console.log(`${new Date().toISOString()} api listening on 127.0.0.1:${port}`);
});
