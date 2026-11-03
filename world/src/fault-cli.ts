// Lists fault templates or injects one into a running episode.
//   node src/fault-cli.ts list
//   node src/fault-cli.ts inject <episode-dir> <fault> [--seed N]
// Writes task.json (the alert the agent sees) into the episode and fault.json
// (ids and thresholds for the grader) into the episode's .secret folder.

import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { parseArgs } from "node:util";
import { errorMessage } from "./db.ts";
import { secretDir } from "./episode.ts";
import { mulberry32 } from "./seed.ts";
import { FAULTS } from "./faults/index.ts";

const { positionals, values } = parseArgs({
  allowPositionals: true,
  options: { seed: { type: "string" } },
});
const [command, dir, name] = positionals;

async function inject(): Promise<void> {
  const fault = FAULTS[name ?? ""];
  if (!dir || !fault) {
    throw new Error(`usage: inject <dir> <fault>; faults: ${Object.keys(FAULTS).join(", ")}`);
  }
  const seedValue = Number(values.seed ?? 1);
  const { rows } = JSON.parse(readFileSync(join(dir, "episode.json"), "utf8")) as { rows: number };
  const started = Date.now();
  const result = await fault.inject({ dir, rows, rand: mulberry32(seedValue) });
  const injectedAt = new Date().toISOString();
  const task = { fault: fault.name, alert: result.alert, injected_at: injectedAt };
  writeFileSync(join(dir, "task.json"), `${JSON.stringify(task, null, 2)}\n`);
  const secret = { fault: fault.name, seed: seedValue, injected_at: injectedAt, ...result.secret };
  writeFileSync(join(secretDir(dir), "fault.json"), JSON.stringify(secret, null, 2));
  console.log(JSON.stringify({ ...task, ms: Date.now() - started }));
}

async function main(): Promise<void> {
  if (command === "list") {
    for (const fault of Object.values(FAULTS)) console.log(`${fault.name.padEnd(18)} ${fault.summary}`);
  } else if (command === "inject") {
    await inject();
  } else {
    throw new Error("usage: fault-cli.ts list | inject <dir> <fault> [--seed N]");
  }
}

main().catch((err: unknown) => {
  console.error(errorMessage(err));
  process.exit(1);
});
