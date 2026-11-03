// Opens the practice app's SQLite database with the pragmas every process shares.
// WAL journal, NORMAL sync, foreign keys on and a busy timeout so concurrent
// writers wait instead of failing. The schema is created once, by initSchema at
// episode creation, so a restart never silently repairs a dropped index.

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
  return db;
}

export function initSchema(db: Db): void {
  db.exec(SCHEMA);
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
