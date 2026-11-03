// Shape of a fault template: code that breaks a running episode on purpose.
// inject() gets the episode folder, its seeded row count and a seeded random
// generator. It breaks the app and returns the alert the agent will see, plus
// secret facts (ids it created, thresholds) that only the grader may read.

export interface FaultContext {
  dir: string;
  rows: number;
  rand: () => number;
}

export interface FaultResult {
  alert: string;
  secret: Record<string, unknown>;
}

export interface Fault {
  name: string;
  summary: string;
  inject(ctx: FaultContext): Promise<FaultResult>;
}

export function between(rand: () => number, low: number, high: number): number {
  return low + Math.floor(rand() * (high - low + 1));
}
