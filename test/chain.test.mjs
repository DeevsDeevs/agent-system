import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, realpathSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

const CHAIN = new URL("../skills/chains/chain.mjs", import.meta.url).pathname;

function run(cwd, args, input) {
  return execFileSync("node", [CHAIN, ...args, "--json"], { cwd, input, encoding: "utf8" });
}
const json = (cwd, args, input) => JSON.parse(run(cwd, args, input));

test("save, load, fork and context keep the .chains format", () => {
  const repo = realpathSync(mkdtempSync(join(tmpdir(), "chains-")));
  mkdirSync(join(repo, ".git"));
  mkdirSync(join(repo, "src"));
  const sub = join(repo, "src");

  const first = json(sub, ["save", "work", "--next", "write the parser"], "# Start\n\n## Request\nbuild it\n");
  assert.equal(first.branch, "main");
  assert.equal(first.parent, null);
  assert.match(first.file, /^\d{4}-\d{2}-\d{2}-\d{9}-start\.md$/);
  assert.equal(json(repo, ["root"]).root, join(repo, ".chains"), "a subfolder saves at the git root");

  const second = json(repo, ["save", "work", "--title", "Parser done"], "parser works\n");
  assert.equal(second.parent, first.file);
  const text = readFileSync(join(repo, ".chains", "work", second.file), "utf8");
  assert.match(text, /^---\nchain: "work"\nbranch: "main"\nparent: ".+"\ncreated: ".+"\n---\n\n# Parser done\n\nparser works\n$/);

  assert.throws(() => run(repo, ["save", "work", "--branch", "spike"], "x"), /fork/);
  const fork = json(repo, ["fork", "work", "spike"]);
  assert.equal(fork.parent, second.file);
  const spike = json(repo, ["save", "work", "--branch", "spike", "--parent", fork.parent], "# Spike\ntry another way\n");
  assert.equal(spike.parent, second.file);

  assert.equal(json(repo, ["load", "work"]).file, second.file, "load defaults to main");
  const ctx = json(repo, ["context", "work", "--branch", "spike"]);
  assert.equal(ctx.current.file, spike.file);
  assert.deepEqual(ctx.parents.map((l) => l.file), [second.file, first.file]);

  const list = json(repo, ["list"]);
  assert.deepEqual(list.map((c) => [c.chain, c.count, c.branches.sort()]), [["work", 3, ["main", "spike"]]]);
  assert.equal(json(repo, ["search", "parser"])[0].file, second.file);
  assert.throws(() => run(repo, ["save", "../x"], "x"), /invalid chain name/);
});

test("the root stops at the git root, and outside git below ~; list is the startup digest", () => {
  const home = realpathSync(mkdtempSync(join(tmpdir(), "chains-home-")));
  const env = { ...process.env, HOME: home };
  const chain = (cwd, args, input) => execFileSync("node", [CHAIN, ...args], { cwd, env, input, encoding: "utf8" });
  const at = (...parts) => join(home, ...parts);
  for (const dir of ["notes/deep", "ws/repo/.git", "ws/repo/src"]) mkdirSync(at(dir), { recursive: true });

  chain(home, ["save", "home-notes"], "# Home\n");
  assert.equal(chain(home, ["root"]).trim(), at(".chains"), "~ uses its own .chains");
  assert.equal(chain(at("notes/deep"), ["root"]).trim(), at("notes/deep/.chains"), "a folder under ~ doesn't fall back to ~/.chains");
  assert.equal(chain(at("notes/deep"), ["list", "--max", "5"]), "", "no chains: list prints nothing");
  chain(at("notes"), ["save", "notes"], "# Notes\n");
  assert.equal(chain(at("notes/deep"), ["root"]).trim(), at("notes/.chains"), "outside git it finds a parent's .chains");

  chain(at("ws"), ["save", "workspace"], "# Workspace\n");
  const repo = at("ws/repo");
  assert.equal(chain(at("ws/repo/src"), ["root"]).trim(), join(repo, ".chains"), "git root is the boundary");
  mkdirSync(join(repo, ".chains/old"), { recursive: true });
  writeFileSync(join(repo, ".chains/old/2020-01-01-000000000-old.md"), '---\nchain: "old"\nbranch: "main"\nnextStep: "check the cache"\ncreated: "2020-01-01T00:00:00.000Z"\n---\n\n# Old idea\n');
  chain(repo, ["save", "work", "--next", "ship it"], "# Fresh\n");
  mkdirSync(join(repo, ".chains/empty"));
  assert.match(chain(at("ws/repo/src"), ["list", "--max", "5"]), new RegExp(`^Chains \\(saved work context\\) in ${join(repo, ".chains")}, newest first:\n- work  1 links  \\[main\\]  latest: Fresh \\(0d\\)  → next: ship it\n- old  1 links  \\[main\\]  latest: Old idea \\(\\d+d, stale\\)  → next: check the cache\nBefore continuing one of these: node .*chain\\.mjs context <chain>\n$`));
  assert.match(chain(repo, ["list", "--max", "1"]), /newest first \(1 of 2\):\n- work .*\nBefore continuing/);
  assert.deepEqual(JSON.parse(chain(repo, ["list", "--json"])).map((c) => c.chain), ["work", "old"]);
});

test("remind: once per session, only after --after minutes with no link saved", () => {
  const home = realpathSync(mkdtempSync(join(tmpdir(), "chains-remind-")));
  const repo = join(home, "repo");
  mkdirSync(join(repo, ".git"), { recursive: true });
  mkdirSync(join(repo, "pkg/app"), { recursive: true });
  mkdirSync(join(home, "elsewhere"));
  const env = { ...process.env, HOME: home, XDG_STATE_HOME: join(home, "state"), CHAINS_REMIND_AFTER: "0" };
  const chain = (args, input = "", cwd = repo) => execFileSync("node", [CHAIN, ...args], { cwd, env, input, encoding: "utf8" });

  assert.equal(chain(["remind", "--session", "s1", "--after", "30"]), "", "too early");
  assert.match(chain(["remind", "--session", "s1"]), /^\[chains reminder\] About 0 min of work .* chains skill now; otherwise ignore this\.\n$/);
  assert.equal(chain(["remind", "--session", "s1"]), "", "only once");

  chain(["remind", "--session", "s2", "--after", "30"], "", home);
  chain(["save", "work"], "# Saved\n", join(repo, "pkg/app"));
  assert.equal(chain(["remind", "--session", "s2"], "", home), "", "a link saved since the session started, in a .chains below the cwd");
  chain(["remind", "--session", "s3", "--after", "30"]);
  chain(["save", "nested"], "# Nested\n", join(home, "elsewhere"));
  assert.match(chain(["remind", "--session", "s3"]), /chains reminder/, "a link outside this folder doesn't count");

  const stop = (input) => chain(["remind", "--hook", "claude-stop"], JSON.stringify({ cwd: repo, transcript_path: "/nonexistent", ...input }));
  assert.deepEqual(JSON.parse(stop({ session_id: "c1" })), { decision: "block", reason: JSON.parse(stop({ session_id: "c2" })).reason });
  assert.equal(stop({ session_id: "c1" }), "");
  assert.equal(stop({ session_id: "c3", stop_hook_active: true }), "");
  assert.match(chain(["remind", "--hook", "claude-precompact"], JSON.stringify({ session_id: "p1", cwd: repo })), /^End the summary with this line, verbatim: "\[chains reminder\]/);
  assert.equal(chain(["remind", "--hook", "claude-stop"], "not json"), "");
  assert.equal(chain(["remind"]), "");
});
