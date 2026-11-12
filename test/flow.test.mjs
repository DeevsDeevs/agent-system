import assert from "node:assert/strict";
import { execFile, execFileSync, spawn } from "node:child_process";
import { chmodSync, existsSync, mkdirSync, mkdtempSync, readFileSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

const FLOW = new URL("../skills/hc-flow/flow.mjs", import.meta.url).pathname;
const FAKE = new URL("./fake-hc.mjs", import.meta.url).pathname;
chmodSync(FAKE, 0o755);

function setup(script, env = {}) {
  const root = mkdtempSync(join(tmpdir(), "hc-flow-"));
  mkdirSync(join(root, "bin"));
  symlinkSync(FAKE, join(root, "bin", "hc"));
  writeFileSync(join(root, "script.js"), script);
  const dir = join(root, "run");
  return {
    root, dir,
    env: { ...process.env, PATH: `${join(root, "bin")}:${process.env.PATH}`, FAKE_HC: join(root, "hc"), HC_TERMINAL_ID: "t1", XDG_STATE_HOME: join(root, "state"), ...env },
    calls: () => readFileSync(join(root, "hc", "calls.log"), "utf8").trim().split("\n").map((l) => JSON.parse(l)),
    result: () => JSON.parse(readFileSync(join(dir, "result.json"), "utf8")),
  };
}

function flow(t, ...extra) {
  return new Promise((done) => execFile("node", [FLOW, "run", join(t.root, "script.js"), "--dir", t.dir, ...extra], { env: t.env, cwd: t.root }, (err, stdout, stderr) => done({ code: err?.code ?? 0, stdout, stderr })));
}
const named = (calls, cmd) => calls.filter((c) => c[0] === cmd).map((c) => (cmd === "run" ? c[c.indexOf("--name") + 1] : c[1]));

test("parallel, pipeline and schema results; harness flags; every worker removed", async () => {
  const t = setup(`export const meta = { name: 'demo', description: 'a "test" {run}' }
phase('Scan')
const [a, b, c] = await parallel([() => agent('FAKE:ok:alpha', { label: 'a' }), () => agent('FAKE:ok:beta', { label: 'b', harness: 'codex', model: 'm1' }), () => agent('FAKE:ok:gamma', { harness: 'claude' })])
const piped = await pipeline([1, 2], (n) => agent('FAKE:json:{"n":' + n + '}', { harness: 'claude', args: ['--permission-mode', 'acceptEdits'], schema: { type: 'object', required: ['n'], properties: { n: { type: 'number' } } } }), (r) => r.n * 10)
return { a, b, c, piped, args, meta: meta.name }`, { FAKE_LEAD: "t0" });
  const r = await flow(t, "--args", '{"x":1}');
  assert.equal(r.code, 0, r.stdout + r.stderr);
  assert.deepEqual(t.result(), { name: "demo", run: t.result().run, ok: true, result: { a: "alpha", b: "beta", c: "gamma", piped: [10, 20], args: { x: 1 }, meta: "demo" }, blocked: [] });
  assert.match(r.stdout, /== Scan\n/);
  assert.match(r.stdout, /run dir /);
  const calls = t.calls(), runs = calls.filter((c) => c[0] === "run");
  assert.deepEqual(runs.map((c) => c.slice(c.indexOf("--") + 1)[0]).sort(), ["claude", "claude", "claude", "codex", "pi"]);
  const plain = runs.find((c) => c.includes("claude") && !c.includes("acceptEdits"));
  assert.deepEqual(plain.slice(plain.indexOf("--") + 1, plain.indexOf("--") + 4), ["claude", "--permission-mode", "auto"]);
  const codex = runs.find((c) => c.includes("codex"));
  assert.deepEqual(codex.slice(codex.indexOf("--") + 1, codex.indexOf("--") + 5), ["codex", "--no-daemon", "--model", "m1"]);
  assert.ok(codex.includes("--add-dir") && codex.includes(t.dir));
  assert.ok(runs.filter((c) => c.includes("acceptEdits")).length === 2 && runs.filter((c) => c.includes("acceptEdits")).every((c) => !c.includes("auto")), "a script's mode replaces the default");
  assert.ok(!runs.find((c) => c[c.indexOf("--") + 1] === "pi").includes("--add-dir"), "pi has no --add-dir");
  assert.ok(runs.every((c) => c.includes("--parent") && c.includes("t0") && c.includes("--no-notify")), "workers belong to the runner's parent");
  assert.ok(runs.every((c) => c[c.indexOf("--name") + 1].length <= 32));
  assert.deepEqual(named(calls, "rm").sort(), named(calls, "run").sort());
  assert.deepEqual(named(calls, "kill").sort(), named(calls, "run").sort());
  const sends = calls.filter((c) => c[0] === "send");
  assert.ok(sends.every((c) => /Don't report with hc send\. Start no other agents\.$/.test(c.at(-1))));
  assert.ok(sends.some((c) => c.at(-1).includes('matching this JSON schema: {"type":"object"')));
});

test("failures reject cleanly; blocked and never-ready workers stay up; one retry for a bad result", async () => {
  const t = setup(`export const meta = { name: 'bad', description: 'failures' }
return await parallel([
  () => agent('FAKE:ok:x', { label: 'cwd', cwd: '/no/such/folder' }),
  () => agent('FAKE:error', { label: 'err' }),
  () => agent('FAKE:exit', { label: 'exit' }),
  () => agent('FAKE:slow', { label: 'slow', timeout: 1 }),
  () => agent('FAKE:blocked', { label: 'blocked' }),
  () => agent('FAKE:ok:x', { label: 'notready' }),
  () => agent('FAKE:fixjson', { label: 'fix', schema: { type: 'object', required: ['a'] } }),
  () => agent('FAKE:ok:', { label: 'empty' }),
  () => agent('FAKE:ok:x', { harness: 'gemini' }),
])`);
  const r = await flow(t, "--max", "9");
  assert.equal(r.code, 0, r.stdout + r.stderr);
  const result = t.result();
  assert.deepEqual(result.result, [null, null, null, null, null, null, { a: 1 }, null, null]);
  assert.deepEqual(result.blocked.map((b) => b.name.replace(/^bad-\w+-/, "")).sort(), ["blocked", "notready"]);
  assert.ok(result.blocked.every((b) => b.address && b.reason));
  for (const why of [/FAILED .*-cwd: no folder \/no\/such\/folder/, /FAILED .*-err: error: screen of/, /FAILED .*-exit: exited \(1\)/, /FAILED .*-slow: timed out after 1s/, /BLOCKED .*-blocked .*needs a person/, /BLOCKED .*-notready .*not ready after 60s/, /retry .*-fix: result file is invalid \(not JSON/, /FAILED .*-empty: result file .* is empty/, /FAILED unknown harness gemini/])
    assert.match(r.stdout, why);
  const calls = t.calls();
  const removed = named(calls, "rm");
  assert.ok(!removed.some((n) => /blocked|notready/.test(n)), "blocked workers are left for the person");
  assert.deepEqual(removed.sort(), named(calls, "run").filter((n) => !/blocked|notready/.test(n)).sort());
});

test("--max caps concurrent workers; a script error fails the run", async () => {
  const t = setup(`export const meta = { name: 'cap', description: 'cap' }
await parallel([1, 2, 3, 4].map((n) => () => agent('FAKE:delay:300:r' + n)))
throw new Error('boom')`);
  const r = await flow(t, "--max", "2");
  assert.equal(r.code, 1);
  assert.equal(t.result().ok, false);
  assert.equal(t.result().error, "boom");
  const live = readFileSync(join(t.root, "hc", "live.log"), "utf8").trim().split("\n").map(Number);
  assert.equal(live.length, 4);
  assert.ok(Math.max(...live) <= 2, `live: ${live}`);
});

test("remote workers: result read on that machine; a blocked one outlives the runner", async () => {
  const t = setup(`export const meta = { name: 'far', description: 'remote' }
return await parallel([() => agent('FAKE:ok:far away', { on: 'box', cwd: '/srv' }), () => agent('FAKE:blocked', { on: 'box', label: 'stuck' })])`, { FAKE_LEAD: "t0" });
  const r = await flow(t);
  assert.equal(r.code, 0, r.stdout + r.stderr);
  assert.deepEqual(t.result().result, ["far away", null]);
  const calls = t.calls(), runs = calls.filter((c) => c[0] === "run");
  assert.ok(runs.every((c) => c.includes("--on") && c.includes("box")));
  assert.ok(runs.some((c) => c.includes("/srv")));
  assert.ok(calls.some((c) => c[0] === "exec" && c.includes("box")));
  assert.ok(calls.some((c) => c[0] === "file" && c.includes("--on")));
  assert.ok(existsSync(join(t.root, "state", "hc-flow")), "the remote run dir is made through hc exec");
  const ran = named(calls, "run").map((n) => "box/" + n);
  assert.deepEqual(named(calls, "rm"), ran.filter((a) => !a.endsWith("stuck")));
  // The runner's terminal ends: the blocked worker stays for the person.
  execFileSync("hc", ["_ended", "t1"], { env: t.env });
  assert.ok(existsSync(join(t.root, "hc", "t", ran.find((a) => a.endsWith("stuck")).replace("/", "_") + ".json")));
});

test("with no lead, a blocked local worker outlives the runner", async () => {
  const t = setup(`export const meta = { name: 'solo', description: 'no lead' }
return await agent('FAKE:blocked', { label: 'stuck' })`);
  const r = await flow(t);
  assert.equal(r.code, 1, r.stdout + r.stderr);
  const [name] = named(t.calls(), "run");
  execFileSync("hc", ["_ended", "t1"], { env: t.env });
  assert.ok(existsSync(join(t.root, "hc", "t", name + ".json")));
});

test("Ctrl-C removes the workers the runner started", async () => {
  const t = setup(`export const meta = { name: 'stop', description: 'stop' }
await parallel([() => agent('FAKE:slow', { label: 'one' }), () => agent('FAKE:slow', { label: 'two', on: 'box' })])`, { FAKE_LEAD: "t0" });
  // Its own process group, signalled whole, as a terminal's Ctrl-C does: the runner's hc calls get it too.
  const child = spawn("node", [FLOW, "run", join(t.root, "script.js"), "--dir", t.dir], { env: t.env, detached: true });
  let stdout = "", armed = null;
  child.stdout.on("data", (d) => {
    stdout += d;
    if (!armed && (stdout.match(/start /g) ?? []).length === 2) armed = setTimeout(() => process.kill(-child.pid, "SIGINT"), 300);
  });
  const fallback = setTimeout(() => process.kill(-child.pid, "SIGINT"), 5000); // a worker that never starts fails, not hangs
  const code = await new Promise((done) => child.on("exit", done));
  clearTimeout(fallback);
  assert.equal(code, 130, stdout);
  assert.match(stdout, /stopped \(SIGINT\): removing 2 worker/);
  assert.equal(t.result().error, "stopped by SIGINT");
  const ran = t.calls().filter((c) => c[0] === "run").map((c) => (c.includes("--on") ? "box/" : "") + c[c.indexOf("--name") + 1]);
  assert.deepEqual(named(t.calls(), "rm").sort(), ran.sort());
});

test("a script without the meta literal first is refused", async () => {
  const t = setup(`const x = 1\nexport const meta = { name: 'late', description: 'x' }`);
  const r = await flow(t);
  assert.equal(r.code, 2);
  assert.match(r.stderr, /must start with `export const meta/);
});
