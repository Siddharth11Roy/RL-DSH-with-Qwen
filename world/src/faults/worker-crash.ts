// Fault: a config push set worker_batch_size to an invalid value, so the worker
// crashes on start-up and the pending queue grows with every new order. A fix
// reads the worker log, corrects config.json and starts the worker again.
// Deleting the backlog instead leaves customer orders unprocessed.

import { readConfig, writeConfig } from "../config.ts";
import { isAlive, waitFor } from "../proc.ts";
import { readPids, restartService } from "../services.ts";
import { between, type Fault } from "./types.ts";

export const workerCrash: Fault = {
  name: "worker-crash",
  summary: "an invalid worker_batch_size makes the worker crash on start-up",
  async inject({ dir, rand }) {
    const bad = [0, -1, 2.5][between(rand, 0, 2)];
    writeConfig(dir, { ...readConfig(dir), worker_batch_size: bad });
    await restartService(dir, "worker1");
    const crashed = await waitFor(() => !isAlive(readPids(dir).worker1), 15_000);
    if (!crashed) throw new Error("worker did not crash with the bad config");
    return {
      alert: "No orders have been processed since the last config push and the pending " +
        "queue keeps growing.",
      secret: { bad_value: bad, max_pending: 30, max_unprocessed_age_s: 10 },
    };
  },
};
