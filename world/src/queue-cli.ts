// Operator command for the job queue, later exposed to the agent as its `queue` tool.
//   stats            counts by status        list [status]   newest 20 jobs
//   show <id>        one job in full         cancel <id>     stop a pending/running job
//   requeue-dead     send dead-letter jobs back to pending
// Run as `node src/queue-cli.ts <episode-dir> <command> [arg]`.

import { join } from "node:path";
import { errorMessage, openDb } from "./db.ts";
import { STATUSES, cancel, requeueDead, stats, type JobStatus } from "./queue.ts";

const [dir, command, arg] = process.argv.slice(2);
const COLUMNS = "id, kind, status, attempts, locked_by, locked_at, last_error";

function list(db: ReturnType<typeof openDb>, status?: string): void {
  if (status && !STATUSES.includes(status as JobStatus)) {
    throw new Error(`status must be one of: ${STATUSES.join(", ")}`);
  }
  const where = status ? "WHERE status = ?" : "";
  const rows = db.prepare(`SELECT ${COLUMNS} FROM jobs ${where} ORDER BY id DESC LIMIT 20`)
    .all(...(status ? [status] : []));
  if (rows.length === 0) return console.log("no jobs");
  for (const r of rows as Record<string, unknown>[]) {
    const held = r.locked_by ? ` held by ${r.locked_by} since ${r.locked_at}` : "";
    const error = r.last_error ? ` error: ${r.last_error}` : "";
    console.log(`#${r.id} ${r.kind} ${r.status} attempts=${r.attempts}${held}${error}`);
  }
}

function run(): void {
  if (!dir || !command) throw new Error("usage: queue-cli.ts <episode-dir> <command> [arg]");
  const db = openDb(join(dir, "app.db"));
  try {
    if (command === "stats") console.log(JSON.stringify(stats(db)));
    else if (command === "list") list(db, arg);
    else if (command === "show") {
      const row = db.prepare("SELECT * FROM jobs WHERE id = ?").get(Number(arg));
      console.log(row ? JSON.stringify(row, null, 2) : `no job ${arg}`);
    } else if (command === "cancel") {
      console.log(cancel(db, Number(arg)) ? `cancelled job ${arg}` : `job ${arg} not cancellable`);
    } else if (command === "requeue-dead") console.log(`requeued ${requeueDead(db)} dead jobs`);
    else throw new Error(`unknown command: ${command}`);
  } finally {
    db.close();
  }
}

try {
  run();
} catch (err) {
  console.error(errorMessage(err));
  process.exit(1);
}
