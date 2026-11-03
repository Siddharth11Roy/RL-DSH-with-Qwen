// Opens the practice app's SQLite database with the pragmas every process shares.
// WAL journal, NORMAL sync, foreign keys on and a busy timeout so concurrent
// writers wait instead of failing. Faults later change these settings on
// purpose (for example dropping the busy timeout to cause SQLITE_BUSY errors).

import { DatabaseSync } from "node:sqlite";
import { SCHEMA } from "./schema.ts";

export type Db = DatabaseSync;

export interface DbOptions {
  busyTimeoutMs?: number;
}

export function openDb(file: string, options: DbOptions = {}): Db {
  const db = new DatabaseSync(file);
  db.exec(`PRAGMA busy_timeout = ${options.busyTimeoutMs ?? 2000}`);
  db.exec("PRAGMA journal_mode = WAL");
  db.exec("PRAGMA synchronous = NORMAL");
  db.exec("PRAGMA foreign_keys = ON");
  db.exec(SCHEMA);
  return db;
}

export function tx<T>(db: Db, fn: () => T): T {
  db.exec("BEGIN IMMEDIATE");
  try {
    const out = fn();
    db.exec("COMMIT");
    return out;
  } catch (err) {
    db.exec("ROLLBACK");
    throw err;
  }
}

export function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}
