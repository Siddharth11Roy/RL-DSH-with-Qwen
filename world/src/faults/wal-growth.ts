// Fault: a stuck report job holds a read transaction open, so checkpoints stall
// and app.db-wal grows without limit. A fix finds the job (queue list, logs),
// cancels it or kills its process, then runs PRAGMA wal_checkpoint(TRUNCATE).
// Randomised per seed: the report period and how many MB of report data piled up.

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { openDb, tx } from "../db.ts";
import { fileExists, startProcess, waitFor } from "../proc.ts";
import { readPids, writePids } from "../services.ts";
import { between, type Fault } from "./types.ts";

const CHUNK = 64 * 1024;

export const walGrowth: Fault = {
  name: "wal-growth",
  summary: "a stuck report job blocks checkpoints, so app.db-wal keeps growing",
  async inject({ dir, rand }) {
    const db = openDb(join(dir, "app.db"));
    const period = `2026-${String(between(rand, 1, 9)).padStart(2, "0")}`;
    const reportMb = between(rand, 24, 40);
    const { id: jobId } = db.prepare(
      `INSERT INTO jobs (kind, payload, status, attempts, locked_by, locked_at)
       VALUES ('generate_report', ?, 'running', 1, 'report-runner',
               strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '-14 minutes')) RETURNING id`,
    ).get(JSON.stringify({ period })) as { id: number };

    const pid = startProcess(dir, "report", "faults/report-holder.ts", [String(jobId)]);
    writePids(dir, { ...readPids(dir), report: pid });
    const logFile = join(dir, "logs", "report.log");
    const holding = () => fileExists(logFile) && readFileSync(logFile, "utf8").includes("holding");
    if (!(await waitFor(holding, 15_000))) throw new Error("report holder did not start");

    db.exec("CREATE TABLE IF NOT EXISTS report_cache (id INTEGER PRIMARY KEY, period TEXT, chunk BLOB)");
    const insert = db.prepare("INSERT INTO report_cache (period, chunk) VALUES (?, randomblob(?))");
    for (let mb = 0; mb < reportMb; mb++) {
      tx(db, () => { for (let i = 0; i < 1_048_576 / CHUNK; i++) insert.run(period, CHUNK); });
    }
    db.close();
    return {
      alert: `app.db-wal has grown past ${reportMb} MB and keeps growing; write latency is climbing.`,
      secret: { job_id: jobId, report_mb: reportMb, wal_limit_bytes: 8 * 1024 * 1024 },
    };
  },
};
