// Registry of every fault template, keyed by the name used on the command line.
// Adding a fault means writing its module next to this file and listing it
// here; the grader with the same name lives in src/rlh/graders on the Python side.

import type { Fault } from "./types.ts";

const ALL: Fault[] = [];

export const FAULTS: Record<string, Fault> = Object.fromEntries(ALL.map((f) => [f.name, f]));
