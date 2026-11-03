// Service control for an episode, later exposed to the agent as its `svc` tool.
//   status               each service with its pid and whether it is up
//   restart <name|all>   restart api, workerN or every app service (re-reads config.json)
//   start|stop <name>    start or stop one app service; the load generator is off-limits
// Run as `node src/svc-cli.ts <episode-dir> <command> [name]`.

import { errorMessage } from "./db.ts";
import { isAlive } from "./proc.ts";
import {
  appServices, isAppService, readPids, restartService, startService, stopService,
} from "./services.ts";

const [dir, command, name] = process.argv.slice(2);

function guard(service: string | undefined): string {
  if (!service) throw new Error(`${command} needs a service name (api, workerN or all)`);
  if (service !== "all" && !isAppService(service)) {
    throw new Error(`${service} is not an app service; only api and workerN can be controlled`);
  }
  return service;
}

async function main(): Promise<void> {
  if (!dir || !command) throw new Error("usage: svc-cli.ts <episode-dir> <command> [name]");
  if (command === "status") {
    for (const [service, pid] of Object.entries(readPids(dir))) {
      console.log(`${service.padEnd(8)} pid ${pid} ${isAlive(pid) ? "up" : "DOWN"}`);
    }
    return;
  }
  const target = guard(name);
  const names = target === "all" ? appServices(dir) : [target];
  for (const service of names) {
    if (command === "restart") console.log(`restarted ${service} (pid ${await restartService(dir, service)})`);
    else if (command === "start") console.log(`started ${service} (pid ${await startService(dir, service)})`);
    else if (command === "stop") console.log(stopService(dir, service) ? `stopped ${service}` : `${service} not found`);
    else throw new Error(`unknown command: ${command}`);
  }
}

main().catch((err: unknown) => {
  console.error(errorMessage(err));
  process.exit(1);
});
