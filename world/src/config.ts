// Per-episode settings the app's services read when they start.
// Stored at <episode>/config.json so an operator (or the agent) can edit it and
// restart a service to apply it. Faults break it on purpose, for example by
// setting busy_timeout_ms to 0 or giving the worker an invalid batch size.

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

export interface AppConfig {
  busy_timeout_ms: number;
  worker_poll_ms: number;
  worker_batch_size: number;
}

export const DEFAULT_CONFIG: AppConfig = {
  busy_timeout_ms: 2000,
  worker_poll_ms: 50,
  worker_batch_size: 1,
};

export const configPath = (dir: string): string => join(dir, "config.json");

export function readConfig(dir: string): AppConfig {
  if (!existsSync(configPath(dir))) return { ...DEFAULT_CONFIG };
  return { ...DEFAULT_CONFIG, ...(JSON.parse(readFileSync(configPath(dir), "utf8")) as object) };
}

export function writeConfig(dir: string, config: AppConfig): void {
  writeFileSync(configPath(dir), `${JSON.stringify(config, null, 2)}\n`);
}
