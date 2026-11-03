// Smoke test for the practice world's storage layer.
// Opens a temporary SQLite file with Node's built-in node:sqlite, switches it
// to WAL mode, writes a batch of rows and checks that a TRUNCATE checkpoint
// empties the -wal file. If this passes, every fault we build on WAL behaviour
// (growth, stuck checkpoints, busy writers) has a working base.

import { DatabaseSync } from "node:sqlite";
import { existsSync, mkdtempSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const dir = mkdtempSync(join(tmpdir(), "rlh-smoke-"));
const file = join(dir, "app.db");
const walSize = () => (existsSync(`${file}-wal`) ? statSync(`${file}-wal`).size : 0);

const db = new DatabaseSync(file);
const mode = db.prepare("PRAGMA journal_mode = WAL").get() as { journal_mode: string };
db.exec("PRAGMA wal_autocheckpoint = 0");
db.exec("CREATE TABLE jobs (id INTEGER PRIMARY KEY, payload TEXT NOT NULL)");

const insert = db.prepare("INSERT INTO jobs (payload) VALUES (?)");
db.exec("BEGIN");
for (let i = 0; i < 5000; i++) insert.run(`job-${i}-${"x".repeat(64)}`);
db.exec("COMMIT");

const before = walSize();
const result = db.prepare("PRAGMA wal_checkpoint(TRUNCATE)").get();
const after = walSize();
const rows = db.prepare("SELECT count(*) AS n FROM jobs").get() as { n: number };
db.close();
rmSync(dir, { recursive: true, force: true });

const ok = mode.journal_mode === "wal" && before > 0 && after === 0 && rows.n === 5000;
console.log(`journal_mode=${mode.journal_mode} rows=${rows.n}`);
console.log(`wal before checkpoint=${before} bytes, after=${after} bytes`);
console.log(`checkpoint result=${JSON.stringify(result)}`);
console.log(ok ? "smoke: ok" : "smoke: FAILED");
process.exit(ok ? 0 : 1);
