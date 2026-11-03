// Fault: a config change set busy_timeout_ms to 0 and scaled workers up, so
// concurrent writers fail instantly with SQLITE_BUSY ("database is locked") and
// worker logs flood with errors. A fix restores a sane busy timeout in
// config.json and restarts the services so they pick it up. Randomised: workers.

import { readConfig, writeConfig } from "../config.ts";
import { restartService, startService } from "../services.ts";
import { between, type Fault } from "./types.ts";

export const busyErrors: Fault = {
  name: "busy-errors",
  summary: "busy_timeout_ms is 0, so concurrent writers fail with 'database is locked'",
  async inject({ dir, rand }) {
    const workers = between(rand, 3, 4);
    writeConfig(dir, { ...readConfig(dir), busy_timeout_ms: 0, worker_poll_ms: 5 });
    await restartService(dir, "worker1");
    for (let i = 2; i <= workers; i++) await startService(dir, `worker${i}`);
    await restartService(dir, "api");
    return {
      alert: "Since this morning's config change the worker logs are flooded with " +
        "'database is locked' errors and order processing is lagging.",
      secret: { workers, min_busy_timeout_ms: 500 },
    };
  },
};
