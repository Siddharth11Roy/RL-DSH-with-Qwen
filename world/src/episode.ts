// Lifecycle of one practice-world episode, kept inside a single folder.
// create() seeds a fresh database and stores its checksum in a sibling
// "<dir>.secret" folder the agent never works in; start() launches the API,
// workers and load generator; stop() kills them all; status() reports health.

import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { openDb } from "./db.ts";
import { checksum, seed } from "./seed.ts";
import { fileExists, isAlive, killTree, startProcess, waitFor } from "./proc.ts";

export interface CreateOptions { rows?: number; seed?: number }
export interface StartOptions { rate?: number; workers?: number }
export type Pids = Record<string, number>;

export const secretDir = (dir: string): string => `${resolve(dir)}.secret`;
const pidsFile = (dir: string): string => join(dir, "pids.json");

export function readPids(dir: string): Pids {
  return fileExists(pidsFile(dir)) ? (JSON.parse(readFileSync(pidsFile(dir), "utf8")) as Pids) : {};
}

export function createEpisode(dir: string, options: CreateOptions = {}): string {
  const rows = options.rows ?? 2000;
  const seedValue = options.seed ?? 1;
  rmSync(dir, { recursive: true, force: true });
  rmSync(secretDir(dir), { recursive: true, force: true });
  mkdirSync(join(dir, "logs"), { recursive: true });
  mkdirSync(secretDir(dir), { recursive: true });
  const db = openDb(join(dir, "app.db"));
  seed(db, rows, seedValue);
  const sum = checksum(db, rows);
  db.close();
  const meta = { rows, seed: seedValue, created_at: new Date().toISOString() };
  writeFileSync(join(dir, "episode.json"), JSON.stringify(meta, null, 2));
  writeFileSync(join(secretDir(dir), "checksum.json"), JSON.stringify({ ...meta, checksum: sum }));
  return sum;
}

export async function startEpisode(dir: string, options: StartOptions = {}): Promise<Pids> {
  if (Object.values(readPids(dir)).some(isAlive)) throw new Error(`episode already running: ${dir}`);
  rmSync(join(dir, "api.port"), { force: true });
  const pids: Pids = { api: startProcess(dir, "api", "api.ts") };
  for (let i = 1; i <= (options.workers ?? 1); i++) {
    pids[`worker${i}`] = startProcess(dir, `worker${i}`, "worker.ts", [`worker-${i}`]);
  }
  writeFileSync(pidsFile(dir), JSON.stringify(pids));
  if (!(await waitFor(() => fileExists(join(dir, "api.port")), 10_000))) {
    stopEpisode(dir);
    throw new Error(`api did not start; see ${join(dir, "logs", "api.log")}`);
  }
  pids.load = startProcess(dir, "load", "load.ts", [String(options.rate ?? 20)]);
  writeFileSync(pidsFile(dir), JSON.stringify(pids));
  return pids;
}

export function stopEpisode(dir: string): number {
  const pids = Object.values(readPids(dir));
  for (const pid of pids) killTree(pid);
  rmSync(pidsFile(dir), { force: true });
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
