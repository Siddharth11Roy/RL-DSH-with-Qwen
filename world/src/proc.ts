// Starts and stops the Node processes that make up one episode.
// Each process runs detached with its output in logs/<name>.log. Stopping
// kills the whole process tree: taskkill /T on Windows, a signal to the
// negative pid (the process group) elsewhere, so nothing leaks between episodes.

import { spawn, spawnSync } from "node:child_process";
import { closeSync, existsSync, mkdirSync, openSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { setTimeout as sleep } from "node:timers/promises";

const SRC = dirname(fileURLToPath(import.meta.url));
const NODE_FLAGS = ["--disable-warning=ExperimentalWarning"];

export function startProcess(dir: string, name: string, script: string, args: string[] = []): number {
  mkdirSync(join(dir, "logs"), { recursive: true });
  const out = openSync(join(dir, "logs", `${name}.log`), "a");
  const child = spawn(process.execPath, [...NODE_FLAGS, join(SRC, script), dir, ...args], {
    detached: true,
    stdio: ["ignore", out, out],
    windowsHide: true,
  });
  closeSync(out);
  child.unref();
  if (child.pid === undefined) throw new Error(`failed to start ${name}`);
  return child.pid;
}

export function isAlive(pid: number): boolean {
  try {
    process.kill(pid, 0);
    return true;
  } catch (err) {
    return (err as NodeJS.ErrnoException).code === "EPERM";
  }
}

export function killTree(pid: number): void {
  if (!isAlive(pid)) return;
  if (process.platform === "win32") {
    spawnSync("taskkill", ["/PID", String(pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
    return;
  }
  try {
    process.kill(-pid, "SIGKILL");
  } catch {
    process.kill(pid, "SIGKILL");
  }
}

export async function waitFor(check: () => boolean, timeoutMs: number): Promise<boolean> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (check()) return true;
    await sleep(25);
  }
  return check();
}

export function fileExists(path: string): boolean {
  return existsSync(path);
}
