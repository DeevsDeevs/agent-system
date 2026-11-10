#!/usr/bin/env node
// A stand-in for `hc` in the hc-flow tests. Terminals are files in $FAKE_HC/t/. A worker's
// behaviour comes from a FAKE:<mode>[:<data>] token in the brief it is sent.
import { execFileSync } from "node:child_process";
import { appendFileSync, existsSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const dir = process.env.FAKE_HC;
const argv = process.argv.slice(2);
const terms = join(dir, "t");
mkdirSync(terms, { recursive: true });
appendFileSync(join(dir, "calls.log"), `${JSON.stringify(argv)}\n`);

const flag = (name) => (argv.includes(name) ? argv[argv.indexOf(name) + 1] : undefined);
const path = (address) => join(terms, `${address.replace("/", "_")}.json`);
const load = (address) => JSON.parse(readFileSync(path(address), "utf8"));
const save = (address, t) => writeFileSync(path(address), JSON.stringify(t));
const out = (value) => process.stdout.write(`${JSON.stringify(value)}\n`);
const sleep = (ms) => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);

function finish(t) {
  const [mode, data] = [t.mode, t.data];
  if (mode === "ok" || mode === "json") writeFileSync(t.file, data);
  if (mode === "fixjson") writeFileSync(t.file, t.sends > 1 ? '{"a":1}' : "not json");
  if (mode === "delay") writeFileSync(t.file, data.split(":").slice(1).join(":"));
  t.status = { blocked: "blocked", error: "error", exit: null }[mode] ?? "done";
  if (mode === "exit") t.exit = 1;
}

const [cmd] = argv;
if (cmd === "get") out({ parent: process.env.FAKE_LEAD || null });
else if (cmd === "run") {
  const name = flag("--name"), on = flag("--on"), cwd = flag("--cwd");
  if (cwd && !on && !existsSync(cwd)) {
    process.stderr.write(`${JSON.stringify({ error: { kind: "spawn_failed", message: `no folder ${cwd}` } })}\n`);
    process.exit(3);
  }
  const address = on ? `${on}/${name}` : name;
  const live = readdirSync(terms).length + 1;
  appendFileSync(join(dir, "live.log"), `${live}\n`);
  save(address, { name, status: name.includes("notready") ? null : "idle", argv: argv.slice(argv.indexOf("--") + 1), sends: 0 });
  out({ address, name, state: "live" });
} else if (cmd === "wait") {
  const address = argv[argv.indexOf("--json") + 1];
  const t = load(address);
  if (t.finishAt && Date.now() >= t.finishAt) {
    delete t.finishAt;
    finish(t);
    save(address, t);
  }
  if (t.status === null && t.exit == null || t.status === "working") {
    sleep(Math.min(Number(flag("--timeout")) * 1000, 200));
    out({ ended: false, reason: "timeout", status: t.status, exit_code: null, signal: null });
  } else out({ ended: true, reason: t.exit != null ? "exit" : "status", status: t.status, exit_code: t.exit ?? null, signal: null });
} else if (cmd === "send") {
  const [address, text] = argv.slice(argv.indexOf("--json") + 1);
  const t = load(address);
  t.sends++;
  const token = /FAKE:(\w+)(?::(.*))?/.exec(text);
  if (token) [t.mode, t.data] = [token[1], token[2] ?? ""];
  t.file ??= /write your final answer to (\S+?)(?: as one|\.\n|\.$)/.exec(text)?.[1];
  t.status = "working";
  if (t.mode === "delay") t.finishAt = Date.now() + Number(t.data.split(":")[0]);
  else if (t.mode !== "slow") finish(t);
  save(address, t);
  out({ started: true, status: "idle", turn: 0 });
} else if (cmd === "read") process.stdout.write(`screen of ${argv[1]}\n`);
else if (cmd === "rm") rmSync(path(argv[1]), { force: true });
else if (cmd === "kill") {}
else if (cmd === "exec") process.stdout.write(execFileSync(argv[argv.indexOf("--") + 1], argv.slice(argv.indexOf("--") + 2), { encoding: "utf8" }));
else if (cmd === "file" && argv[1] === "read") {
  const file = argv.at(-1);
  if (!existsSync(file)) process.exit(3);
  process.stdout.write(readFileSync(file, "utf8"));
} else process.exit(64);
