// Command line for episodes, used by `rlh world` and by hand while debugging.
//   node src/episode-cli.ts create <dir> [--rows N] [--seed S]
//   node src/episode-cli.ts start  <dir> [--rate R] [--workers W]
//   node src/episode-cli.ts stop   <dir>
//   node src/episode-cli.ts status <dir>

import { parseArgs } from "node:util";
import { createEpisode, episodeStatus, startEpisode, stopEpisode } from "./episode.ts";
import { errorMessage } from "./db.ts";

const { positionals, values } = parseArgs({
  allowPositionals: true,
  options: {
    rows: { type: "string" },
    seed: { type: "string" },
    rate: { type: "string" },
    workers: { type: "string" },
  },
});

const [command, dir] = positionals;
const num = (value: string | undefined): number | undefined =>
  value === undefined ? undefined : Number(value);

async function main(): Promise<void> {
  if (!command || !dir) throw new Error("usage: episode-cli.ts <create|start|stop|status> <dir>");
  const started = Date.now();
  if (command === "create") {
    const sum = createEpisode(dir, { rows: num(values.rows), seed: num(values.seed) });
    console.log(JSON.stringify({ created: dir, checksum: sum.slice(0, 12), ms: Date.now() - started }));
  } else if (command === "start") {
    const pids = await startEpisode(dir, { rate: num(values.rate), workers: num(values.workers) });
    console.log(JSON.stringify({ started: dir, pids, ms: Date.now() - started }));
  } else if (command === "stop") {
    console.log(JSON.stringify({ stopped: dir, processes: stopEpisode(dir) }));
  } else if (command === "status") {
    console.log(JSON.stringify(await episodeStatus(dir), null, 2));
  } else {
    throw new Error(`unknown command: ${command}`);
  }
}

main().catch((err: unknown) => {
  console.error(errorMessage(err));
  process.exit(1);
});
