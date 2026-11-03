// Lifecycle of one practice-world episode, kept inside a single folder.
// create() seeds a fresh database and stores its checksum in a sibling
// "<dir>.secret" folder the agent never works in; start() launches the API,
// workers and load generator; stop() kills them all; status() reports health.

import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { initSchema, openDb } from "./db.ts";
import { DEFAULT_CONFIG, writeConfig } from "./config.ts";
import { checksum, seed } from "./seed.ts";
import { fileExists, isAlive, killTree } from "./proc.ts";
import { readPids, startLoad, startService, type Pids } from "./services.ts";

export interface CreateOptions { rows?: number; seed?: number }
export interface StartOptions { rate?: number; workers?: number }
export { readPids, type Pids };

export const secretDir = (dir: string): string => `${resolve(dir)}.secret`;

export function createEpisode(dir: string, options: CreateOptions = {}): string {
  const rows = options.rows ?? 2000;
  const seedValue = options.seed ?? 1;
  rmSync(dir, { recursive: true, force: true });
  rmSync(secretDir(dir), { recursive: true, force: true });
  mkdirSync(join(dir, "logs"), { recursive: true });
  mkdirSync(secretDir(dir), { recursive: true });
  const db = openDb(join(dir, "app.db"));
  initSchema(db);
  seed(db, rows, seedValue);
  const sum = checksum(db, rows);
  db.close();
  const meta = { rows, seed: seedValue, created_at: new Date().toISOString() };
  writeConfig(dir, DEFAULT_CONFIG);
  writeFileSync(join(dir, "episode.json"), JSON.stringify(meta, null, 2));
  writeFileSync(join(secretDir(dir), "checksum.json"), JSON.stringify({ ...meta, checksum: sum }));
  return sum;
}

export async function startEpisode(dir: string, options: StartOptions = {}): Promise<Pids> {
  if (Object.values(readPids(dir)).some(isAlive)) throw new Error(`episode already running: ${dir}`);
  rmSync(join(dir, "pids.json"), { force: true });
  try {
    for (let i = 1; i <= (options.workers ?? 1); i++) await startService(dir, `worker${i}`);
    await startService(dir, "api");
  } catch (err) {
    stopEpisode(dir);
    throw err;
  }
  startLoad(dir, options.rate ?? 20);
  return readPids(dir);
}

export function stopEpisode(dir: string): number {
  const pids = Object.values(readPids(dir));
  for (const pid of pids) killTree(pid);
  rmSync(join(dir, "pids.json"), { force: true });
  return pids.length;
}

export async function episodeStatus(dir: string): Promise<Record<string, unknown>> {
  const alive = Object.fromEntries(Object.entries(readPids(dir)).map(([k, p]) => [k, isAlive(p)]));
  const portFile = join(dir, "api.port");
  let api: unknown = "not running";
  if (alive.api && fileExists(portFile)) {
    const port = readFileSync(portFile, "utf8").trim();
    api = await fetch(`http://127.0.0.1:${port}/stats`, { signal: AbortSignal.timeout(2000) })
      .then((r) => r.json())
      .catch((err: unknown) => `unreachable: ${String(err)}`);
  }
  const loadFile = join(dir, "load.json");
  const load = fileExists(loadFile) ? JSON.parse(readFileSync(loadFile, "utf8")) : null;
  return { processes: alive, api, load };
}
