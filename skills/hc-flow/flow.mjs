#!/usr/bin/env node
// hc-flow runner: a script of agent() / parallel() / pipeline() calls where every agent is a real
// harness (pi, claude, codex) in its own hc terminal. Node stdlib only.
import { execFile } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join, resolve } from "node:path";

const USAGE = "usage: node flow.mjs run <script.js> [--args JSON] [--max 4] [--dir DIR]";
const HARNESSES = { pi: [], claude: [], codex: ["--no-daemon"] };
const READY_SECONDS = 60;
const DEFAULT_TIMEOUT = 1800;

function parseArgs(argv) {
  const pos = [], opt = {};
  for (let i = 0; i < argv.length; i++) argv[i].startsWith("--") ? (opt[argv[i].slice(2)] = argv[++i]) : pos.push(argv[i]);
  return { pos, opt };
}

const stamp = () => new Date().toTimeString().slice(0, 8);
const say = (line) => process.stdout.write(`${stamp()} ${line}\n`);
const slug = (s) => String(s).toLowerCase().replace(/[^a-z0-9_-]+/g, "-").replace(/^-+|-+$/g, "") || "x";

function hc(args) {
  return new Promise((done) => execFile("hc", args, { maxBuffer: 16 << 20 }, (err, stdout, stderr) => done({ code: err ? (err.code ?? 1) : 0, stdout, stderr })));
}

async function hcJson(args) {
  const r = await hc(args);
  if (r.code !== 0) {
    let why = r.stderr.trim() || `exit ${r.code}`;
    try { why = JSON.parse(why).error.message; } catch {}
    throw new Error(`hc ${args[0]}: ${why}`);
  }
  return JSON.parse(r.stdout);
}

// The meta literal must come first: `export const meta = { ... }`. Returns its source span.
function metaSpan(text) {
  const head = /^\s*(?:\/\/[^\n]*\n\s*|\/\*[\s\S]*?\*\/\s*)*export\s+const\s+meta\s*=\s*/.exec(text);
  if (!head || text[head[0].length] !== "{") throw new Error("the script must start with `export const meta = { name, description }`");
  let depth = 0, quote = null;
  for (let i = head[0].length; i < text.length; i++) {
    const c = text[i];
    if (quote) {
      if (c === "\\") i++;
      else if (c === quote) quote = null;
    } else if (c === '"' || c === "'" || c === "`") quote = c;
    else if (c === "{") depth++;
    else if (c === "}" && --depth === 0) return { start: head.index + head[0].indexOf("export"), literal: text.slice(head[0].length, i + 1), end: i + 1 };
  }
  throw new Error("unterminated meta literal");
}

function loadScript(text) {
  const span = metaSpan(text);
  const meta = new Function(`return (${span.literal});`)();
  if (typeof meta?.name !== "string" || typeof meta?.description !== "string") throw new Error("meta needs a name and a description");
  return { meta, body: `${text.slice(0, span.start)}const meta = ${span.literal}${text.slice(span.end)}` };
}

// Shallow check: an object with the schema's required keys. The worker is told the full schema.
function checkResult(text, schema) {
  if (!schema) return text.trim() ? text : null;
  let value;
  try { value = JSON.parse(text.trim().replace(/^```(?:json)?\s*\n?|\n?```$/g, "")); } catch (e) { throw new Error(`not JSON: ${e.message}`); }
  if (schema.type === "object" && (typeof value !== "object" || value === null || Array.isArray(value))) throw new Error("not a JSON object");
  const missing = (schema.required ?? []).filter((k) => !(k in value));
  if (missing.length) throw new Error(`missing keys: ${missing.join(", ")}`);
  return value;
}

async function main(argv) {
  const { pos, opt } = parseArgs(argv);
  if (pos[0] !== "run" || !pos[1]) {
    process.stderr.write(`${USAGE}\n`);
    return 2;
  }
  const { meta, body } = loadScript(readFileSync(pos[1], "utf8"));
  const args = opt.args === undefined ? undefined : JSON.parse(opt.args);
  const max = Math.max(1, Number(opt.max) || 4);
  const run = `${slug(meta.name).slice(0, 14)}-${Date.now().toString(36).slice(-4)}`;
  const stateRel = join("hc-flow", run);
  const dir = resolve(opt.dir ?? join(process.env.XDG_STATE_HOME || join(homedir(), ".local/state"), stateRel));
  mkdirSync(dir, { recursive: true });

  const live = new Map(); // address -> name: workers to clean up
  const blocked = [];
  const names = new Set();
  const remoteDirs = new Map();
  let count = 0, active = 0, stopping = false;
  const queue = [];

  // Workers belong to whoever started the runner, so one left blocked outlives the runner's exit.
  const self = process.env.HC_TERMINAL_ID;
  const lead = self ? (await hcJson(["get", "--json", self]).catch(() => ({}))).parent : null;
  const parentArgs = lead ? ["--parent", lead, "--no-notify"] : [];

  const remove = async (address) => {
    live.delete(address);
    await hc(["kill", address]);
    await hc(["rm", address]);
  };
  const tail = async (address) => (await hc(["read", address, "--lines", "0"])).stdout.split("\n").map((l) => l.trim()).filter(Boolean).slice(-6).join(" | ");
  const remoteDir = (machine) => {
    if (!remoteDirs.has(machine))
      remoteDirs.set(machine, hc(["exec", "--on", machine, "--", "sh", "-c", `d="\${XDG_STATE_HOME:-$HOME/.local/state}/${stateRel}"; mkdir -p "$d" && printf %s "$d"`]).then((r) => {
        if (r.code !== 0 || !r.stdout.trim()) throw new Error(`no run dir on ${machine}: ${r.stderr.trim() || `exit ${r.code}`}`);
        return r.stdout.trim();
      }));
    return remoteDirs.get(machine);
  };
  const uniqueName = (label) => {
    const base = `${run}-${slug(label)}`.slice(0, 32);
    let name = base;
    for (let n = 2; names.has(name); n++) name = `${base.slice(0, 32 - String(n).length - 1)}-${n}`;
    names.add(name);
    return name;
  };

  async function work(prompt, opts, label) {
    const harness = opts.harness ?? "pi";
    const name = uniqueName(label);
    const where = opts.on ? await remoteDir(opts.on) : dir;
    const file = `${where}/${name}.${opts.schema ? "json" : "md"}`;
    const argv = [harness, ...HARNESSES[harness], ...(opts.model ? ["--model", opts.model] : []), ...(harness === "pi" ? [] : ["--add-dir", where]), ...(opts.args ?? [])];
    const cwd = opts.on ? opts.cwd : resolve(opts.cwd ?? process.cwd());
    if (!opts.on && !existsSync(cwd)) throw new Error(`${name}: no folder ${cwd}`);
    const started = await hcJson(["run", "--bg", "--json", "--name", name, ...(opts.on ? ["--on", opts.on] : []), ...(cwd ? ["--cwd", cwd] : []), ...parentArgs, "--", ...argv]).catch((e) => {
      throw new Error(`${name}: ${e.message}`);
    });
    const address = started.address;
    live.set(address, name);
    const t0 = Date.now();
    say(`start ${name} ${address} (${harness}${opts.model ? ` ${opts.model}` : ""}${opts.on ? ` on ${opts.on}` : ""}${opts.phase ? `, ${opts.phase}` : ""})`);

    const fail = async (why) => {
      await remove(address);
      throw new Error(`${name}: ${why}`);
    };
    const stuck = (why) => {
      live.delete(address);
      blocked.push({ name, address, reason: why });
      say(`BLOCKED ${name} ${address}: ${why}. Left running for you: hc attach ${address}`);
      throw Object.assign(new Error(`${name} is blocked: ${why}`), { logged: true });
    };
    const ended = async (r) => {
      if (r.status === "blocked") stuck(`needs a person: ${await tail(address)}`);
      if (r.exit_code != null || r.signal != null || r.reason === "exit") await fail(`exited (${r.exit_code ?? r.signal}): ${await tail(address)}`);
      if (r.status === "error") await fail(`error: ${await tail(address)}`);
    };

    const ready = await hcJson(["wait", "--json", address, "--timeout", String(READY_SECONDS)]);
    if (!ready.ended) stuck(`not ready after ${READY_SECONDS}s (a trust or login prompt?): ${await tail(address)}`);
    await ended(ready);

    const timeout = Number(opts.timeout ?? DEFAULT_TIMEOUT);
    const deadline = t0 + timeout * 1000;
    const brief = [
      prompt.trim(),
      "",
      "---",
      `When you are done, write your final answer to ${file}${opts.schema ? ` as one JSON object (only the JSON, no fences) matching this JSON schema: ${JSON.stringify(opts.schema)}` : ""}.`,
      "Then finish your turn: the runner that sent this sees it. Don't report with hc send. Start no other agents.",
    ].join("\n");
    let message = brief;
    for (let attempt = 0; ; attempt++) {
      await hcJson(["send", "--json", address, message]).catch((e) => fail(e.message));
      for (;;) {
        const left = Math.ceil((deadline - Date.now()) / 1000);
        if (left <= 0) await fail(`timed out after ${timeout}s`);
        const r = await hcJson(["wait", "--json", address, "--timeout", String(Math.min(left, 600))]);
        if (!r.ended) continue;
        await ended(r);
        break;
      }
      const read = opts.on ? await hc(["file", "read", "--on", opts.on, file]) : await new Promise((done) => {
        try { done({ code: 0, stdout: readFileSync(file, "utf8") }); } catch { done({ code: 1, stdout: "" }); }
      });
      let why = read.code === 0 ? null : "is missing";
      if (!why) try {
        const value = checkResult(read.stdout, opts.schema);
        if (value === null) why = "is empty";
        else {
          await remove(address);
          say(`done ${name} in ${Math.round((Date.now() - t0) / 1000)}s`);
          return value;
        }
      } catch (e) { why = `is invalid (${e.message})`; }
      if (attempt > 0) await fail(`result file ${file} ${why}`);
      say(`retry ${name}: result file ${why}`);
      message = `The result file ${file} ${why}. Write your final answer there now${opts.schema ? " as the JSON object described before" : ""}, then finish your turn.`;
    }
  }

  async function agent(prompt, opts = {}) {
    if (typeof prompt !== "string" || !prompt.trim()) throw new Error("agent() needs a prompt");
    if (!HARNESSES[opts.harness ?? "pi"]) throw new Error(`unknown harness ${opts.harness}: pi, claude or codex`);
    const label = opts.label ?? `${opts.harness ?? "pi"}-${++count}`;
    if (active < max) active++;
    else await new Promise((go) => queue.push(go));
    try {
      return await work(prompt, opts, label);
    } catch (e) {
      if (!e.logged && !stopping) say(`FAILED ${e.message}`);
      throw Object.assign(e, { logged: true });
    } finally {
      const next = queue.shift();
      next ? next() : active--;
    }
  }
  const quiet = (e) => {
    if (!e?.logged && !stopping) say(`FAILED ${e?.message ?? e}`);
    return null;
  };
  const parallel = (thunks) => Promise.all(thunks.map((thunk) => Promise.resolve().then(thunk).catch(quiet)));
  const pipeline = (items, ...stages) => Promise.all(items.map(async (item, i) => {
    let value = item;
    for (const stage of stages) {
      try { value = await stage(value, item, i); } catch (e) { return quiet(e); }
      if (value == null) return null;
    }
    return value;
  }));
  const phase = (title) => say(`== ${title}`);
  const log = (message) => say(String(message));

  const finish = (outcome) => {
    writeFileSync(join(dir, "result.json"), `${JSON.stringify({ name: meta.name, run, ...outcome, blocked }, null, 2)}\n`);
  };
  // Ctrl-C also ends the runner's own hc calls, so the script may finish early: the handler exits.
  for (const signal of ["SIGINT", "SIGTERM", "SIGHUP"])
    process.on(signal, async () => {
      if (stopping) return;
      stopping = true;
      say(`stopped (${signal}): removing ${live.size} worker(s)`);
      await Promise.all([...live.keys()].map(remove));
      finish({ ok: false, error: `stopped by ${signal}` });
      process.exit(130);
    });

  say(`flow ${meta.name}: ${meta.description}`);
  say(`run dir ${dir}`);
  const AsyncFunction = (async () => {}).constructor;
  let outcome;
  try {
    const result = await new AsyncFunction("agent", "parallel", "pipeline", "phase", "log", "args", body)(agent, parallel, pipeline, phase, log, args);
    outcome = { ok: true, result: result ?? null };
  } catch (e) {
    outcome = { ok: false, error: e?.message ?? String(e) };
  }
  if (stopping) await new Promise(() => {});
  // Agents the script started but never awaited.
  await Promise.all([...live.keys()].map(remove));
  finish(outcome);
  say(outcome.ok ? `finished: ${join(dir, "result.json")}` : `failed: ${outcome.error} (${join(dir, "result.json")})`);
  return outcome.ok ? 0 : 1;
}

main(process.argv.slice(2)).then((code) => process.exit(code), (e) => {
    process.stderr.write(`flow: ${e.message}\n`);
    process.exit(2);
  });
