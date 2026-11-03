// Helper process for the wal-growth fault: a report job that never finishes.
// It opens a read transaction and keeps it open, pinning an old snapshot so no
// checkpoint can move past it. It lets go and exits as soon as its job is no
// longer 'running' (what `queue cancel <id>` does); killing the process also works.
// Run as `node src/faults/report-holder.ts <episode-dir> <job-id>`.

import { DatabaseSync } from "node:sqlite";
import { join } from "node:path";
import { openDb } from "../db.ts";

const [dir, jobArg] = process.argv.slice(2);
const jobId = Number(jobArg);
const file = join(dir, "app.db");
const log = (msg: string): void => console.log(`${new Date().toISOString()} report-runner ${msg}`);

const reader = new DatabaseSync(file);
reader.exec("BEGIN");
reader.prepare("SELECT count(*) FROM orders").get();
const status = openDb(file).prepare("SELECT status FROM jobs WHERE id = ?");
log(`job ${jobId}: building monthly report, holding snapshot`);

setInterval(() => {
  const row = status.get(jobId) as { status: string } | undefined;
  if (row?.status === "running") return;
  reader.exec("ROLLBACK");
  log(`job ${jobId}: no longer running (${row?.status ?? "missing"}), released snapshot`);
  process.exit(0);
}, 500);
