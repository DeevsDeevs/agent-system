import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, realpathSync } from "node:fs";
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
