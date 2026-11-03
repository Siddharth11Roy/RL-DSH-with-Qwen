// Registry of every fault template, keyed by the name used on the command line.
// Adding a fault means writing its module next to this file and listing it
// here; the grader with the same name lives in src/rlh/graders on the Python side.

import type { Fault } from "./types.ts";
import { busyErrors } from "./busy-errors.ts";
import { missingIndex } from "./missing-index.ts";
import { orphanRows } from "./orphan-rows.ts";
import { poisonPayload } from "./poison-payload.ts";
import { stuckRunning } from "./stuck-running.ts";
import { walGrowth } from "./wal-growth.ts";

const ALL: Fault[] = [
  walGrowth, busyErrors, missingIndex, orphanRows,
  poisonPayload, stuckRunning,
];

export const FAULTS: Record<string, Fault> = Object.fromEntries(ALL.map((f) => [f.name, f]));
