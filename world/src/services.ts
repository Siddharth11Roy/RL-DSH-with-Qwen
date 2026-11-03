// Starts, stops and restarts the long-running services inside one episode.
// Shared by episode.ts, the `svc` command and the fault injectors. Only the API
// and workers count as app services; the load generator is outside their reach
// because stopping customer traffic is never an acceptable fix.

import { readFileSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { fileExists, isAlive, killTree, startProcess, waitFor } from "./proc.ts";

export type Pids = Record<string, number>;

const pidsFile = (dir: string): string => join(dir, "pids.json");
const WORKER = /^worker(\d+)$/;

export function readPids(dir: string): Pids {
  return fileExists(pidsFile(dir)) ? (JSON.parse(readFileSync(pidsFile(dir), "utf8")) as Pids) : {};
}

export function writePids(dir: string, pids: Pids): void {
  writeFileSync(pidsFile(dir), JSON.stringify(pids));
}

export function isAppService(name: string): boolean {
  return name === "api" || WORKER.test(name);
}

export function appServices(dir: string): string[] {
  return Object.keys(readPids(dir)).filter(isAppService);
}

function launch(dir: string, name: string): number {
  if (name === "api") return startProcess(dir, "api", "api.ts");
  const match = WORKER.exec(name);
  if (!match) throw new Error(`not an app service: ${name} (use api or workerN)`);
  return startProcess(dir, name, "worker.ts", [`worker-${match[1]}`]);
}

export async function startService(dir: string, name: string): Promise<number> {
  const current = readPids(dir)[name];
  if (current !== undefined && isAlive(current)) throw new Error(`${name} is already running`);
  if (name === "api") rmSync(join(dir, "api.port"), { force: true });
  const pid = launch(dir, name);
  writePids(dir, { ...readPids(dir), [name]: pid });
  if (name === "api" && !(await waitFor(() => fileExists(join(dir, "api.port")), 10_000))) {
    throw new Error(`api did not come up; see ${join(dir, "logs", "api.log")}`);
  }
  return pid;
}

export function stopService(dir: string, name: string): boolean {
  const pid = readPids(dir)[name];
  if (pid === undefined) return false;
  killTree(pid);
  return true;
}

export async function restartService(dir: string, name: string): Promise<number> {
  if (!isAppService(name)) throw new Error(`not an app service: ${name} (use api or workerN)`);
  stopService(dir, name);
  return startService(dir, name);
}

export function startLoad(dir: string, rate: number): number {
  const pid = startProcess(dir, "load", "load.ts", [String(rate)]);
  writePids(dir, { ...readPids(dir), load: pid });
  return pid;
}
