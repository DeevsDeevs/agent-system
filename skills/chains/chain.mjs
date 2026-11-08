#!/usr/bin/env node
// Chains: markdown handoff links under .chains/<chain>/<timestamp>-<slug>.md.
import { existsSync, mkdirSync, readdirSync, readFileSync, realpathSync, statSync, unlinkSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const USAGE = `chain <command> [options]   (add --json for JSON)
  save <chain> [--branch B] [--parent FILE] [--next TEXT] [--title T]   link text on stdin
  load <chain> [--branch B] [--link FILE]
  context <chain> [--branch B] [--parents 2] [--recent 3]
  list [chain] [--max N]   no chain: newest first with next steps, nothing when there are none
  search <query> [--chain C]
  fork <chain> <branch> [--from FILE | --from-branch B]
  remind --session ID [--after 30] [--since MS] | --hook claude-stop|claude-precompact   hook JSON on stdin
  root`;
const NAME = /^[\p{L}\p{N}][\p{L}\p{N}._-]{0,79}$/u;
const LINK = /^[\p{L}\p{N}][\p{L}\p{N}._-]*\.md$/u;

function parseArgs(argv) {
  const pos = [], opt = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--json") opt.json = true;
    else if (a.startsWith("--")) opt[a.slice(2)] = argv[++i];
    else pos.push(a);
  }
  return { pos, opt };
}

function fail(message) {
  process.stderr.write(`chain: ${message}\n`);
  process.exit(1);
}

function name(value, kind) {
  if (!value || !NAME.test(value) || value.includes("..")) fail(`invalid ${kind} name ${JSON.stringify(value ?? "")}: letters, digits, . _ -, no slashes`);
  return value;
}

// The nearest .chains from the cwd up to the git root; outside git, up to just below ~ (~ itself
// only from ~), so a ~/.chains is never some other folder's. None: the git root's, else the cwd's.
function root() {
  const cwd = process.cwd();
  let home = homedir();
  try { home = realpathSync(home); } catch {}
  for (let dir = cwd; ; dir = dirname(dir)) {
    if (dir === home && cwd !== home) break;
    if (existsSync(join(dir, ".chains")) || existsSync(join(dir, ".git"))) return join(dir, ".chains");
    if (dir === home || dirname(dir) === dir) break;
  }
  return join(cwd, ".chains");
}

function meta(text) {
  const m = /^---\s*\n([\s\S]*?)\n---\s*\n?/.exec(text);
  const out = {};
  for (const line of m?.[1].split(/\r?\n/) ?? []) {
    const pair = /^(chain|branch|parent|created|nextStep):\s*(.*)$/.exec(line.trim());
    if (pair) out[pair[1]] = pair[2].trim().replace(/^"|"$/g, "").replace(/\\"/g, '"') || undefined;
  }
  return { meta: out, body: m ? text.slice(m[0].length) : text };
}

function linkInfo(chain, file) {
  const path = join(root(), chain, file);
  const text = readFileSync(path, "utf8");
  const { meta: m, body } = meta(text);
  const stamp = /^(\d{4})-(\d{2})-(\d{2})-(\d{2})(\d{2})(\d{2})?/.exec(file);
  const created = m.created ? new Date(m.created) : stamp ? new Date(+stamp[1], stamp[2] - 1, +stamp[3], +stamp[4], +stamp[5], +(stamp[6] ?? 0)) : null;
  const ageDays = created && !isNaN(created) ? Math.floor((Date.now() - created) / 86_400_000) : null;
  return {
    chain, file, path,
    branch: m.branch && NAME.test(m.branch) ? m.branch : "main",
    parent: m.parent && LINK.test(m.parent) ? m.parent : null,
    nextStep: m.nextStep ?? null,
    title: /^#\s+(.+)$/m.exec(body)?.[1].trim() ?? file.replace(/\.md$/, ""),
    created: created && !isNaN(created) ? created.toISOString() : null,
    ageDays, stale: ageDays !== null && ageDays > 7, body,
  };
}

// Newest first.
function links(chain, branch) {
  const dir = join(root(), chain);
  if (!existsSync(dir)) return [];
  const all = readdirSync(dir).filter((f) => LINK.test(f)).sort().reverse().map((f) => linkInfo(chain, f));
  return branch ? all.filter((l) => l.branch === branch) : all;
}

function chains() {
  const r = root();
  return existsSync(r) ? readdirSync(r, { withFileTypes: true }).filter((e) => e.isDirectory() && NAME.test(e.name)).map((e) => e.name).sort() : [];
}

function pick(chain, branch, file) {
  const list = links(chain, file ? undefined : branch ?? "main");
  const link = file ? list.find((l) => l.file === file) : list[0];
  if (!link) fail(file ? `no link ${chain}/${file}` : `no links in ${chain}${branch ? ` on branch ${branch}` : ""}; run: chain list`);
  return link;
}

const strip = ({ body, path, ...rest }) => rest;
const age = (l) => (l.ageDays === null ? "" : ` (${l.ageDays}d${l.stale ? ", stale" : ""})`);
const line = (l) => `${l.file}  [${l.branch}]${age(l)}  ${l.title}${l.nextStep ? `  → ${l.nextStep}` : ""}`;

function timestamp() {
  const d = new Date(), p = (v, w = 2) => String(v).padStart(w, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}${p(d.getMilliseconds(), 3)}`;
}

function save(chain, opt) {
  const branch = name(opt.branch ?? "main", "branch");
  const text = readFileSync(0, "utf8").replace(/^---\s*\n[\s\S]*?\n---\s*\n?/, "").trim();
  if (!text) fail("empty link: pipe the link text on stdin");
  if (opt.parent && !LINK.test(opt.parent)) fail(`invalid parent ${opt.parent}`);
  const latest = links(chain, branch)[0];
  if (branch !== "main" && !latest && !opt.parent) fail(`branch ${branch} has no links yet: run chain fork ${chain} ${branch} first`);
  const parent = opt.parent ?? latest?.file;
  const title = opt.title?.trim() || /^#\s+(.+)$/m.exec(text)?.[1].trim() || "chain-link";
  const slug = title.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, "-").replace(/^-+|-+$/g, "").slice(0, 80) || "chain-link";
  const head = ["---", `chain: ${JSON.stringify(chain)}`, `branch: ${JSON.stringify(branch)}`];
  if (parent) head.push(`parent: ${JSON.stringify(parent)}`);
  if (opt.next?.trim()) head.push(`nextStep: ${JSON.stringify(opt.next.trim().slice(0, 1000))}`);
  head.push(`created: ${JSON.stringify(new Date().toISOString())}`, "---", "");
  mkdirSync(join(root(), chain), { recursive: true });
  for (let n = 1; n <= 10; n++) {
    const file = `${timestamp()}-${slug}${n > 1 ? `-${n}` : ""}.md`;
    try {
      writeFileSync(join(root(), chain, file), `${head.join("\n")}\n${opt.title && !text.startsWith("#") ? `# ${title}\n\n` : ""}${text}\n`, { flag: "wx" });
      return linkInfo(chain, file);
    } catch (e) {
      if (e.code !== "EEXIST") throw e;
    }
  }
  fail("could not pick a free file name");
}

function context(chain, opt) {
  const current = pick(chain, opt.branch, opt.link);
  const parents = [];
  for (let p = current.parent, n = Number(opt.parents ?? 2); p && parents.length < n; ) {
    const f = join(root(), chain, p);
    if (!existsSync(f)) break;
    const l = linkInfo(chain, p);
    parents.push(l);
    p = l.parent;
  }
  const seen = new Set([current.file, ...parents.map((l) => l.file)]);
  const recent = links(chain, current.branch).filter((l) => !seen.has(l.file)).slice(0, Number(opt.recent ?? 3));
  return { current, parents, recent };
}

function search(query, chain) {
  const terms = query.toLowerCase().split(/[^\p{L}\p{N}]+/u).filter((t) => t.length > 1);
  if (!terms.length) fail("search needs a query");
  const hits = [];
  for (const c of chain ? [name(chain, "chain")] : chains()) {
    for (const l of links(c)) {
      const lower = l.body.toLowerCase(), head = `${l.title} ${l.nextStep ?? ""}`.toLowerCase();
      const matched = terms.filter((t) => lower.includes(t) || head.includes(t));
      if (!matched.length) continue;
      const score = matched.length + terms.filter((t) => head.includes(t)).length + (lower.includes(query.toLowerCase()) ? 1 : 0) + Math.exp(-(l.ageDays ?? 0) / 30) * 0.5;
      const lines = l.body.split("\n");
      const best = lines.findIndex((x) => matched.some((t) => x.toLowerCase().includes(t)));
      hits.push({ ...strip(l), score: +score.toFixed(3), line: best + 1, snippet: lines[best]?.trim().slice(0, 200) ?? "" });
    }
  }
  return hits.sort((a, b) => b.score - a.score).slice(0, 20);
}

const STAMP = /^(\d{4})-(\d{2})-(\d{2})-(\d{2})(\d{2})(\d{2})(\d{3})?/;

// Newest link time (ms) in the list root and in any .chains up to 3 folders below the cwd.
function newestLink() {
  const roots = new Set([root()]);
  const walk = (dir, depth) => {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      if (!e.isDirectory()) continue;
      if (e.name === ".chains") roots.add(join(dir, e.name));
      else if (depth < 3 && !e.name.startsWith(".") && e.name !== "node_modules") try { walk(join(dir, e.name), depth + 1); } catch {}
    }
  };
  walk(process.cwd(), 0);
  let newest = 0;
  for (const r of roots) {
    if (!existsSync(r)) continue;
    for (const c of readdirSync(r, { withFileTypes: true })) {
      if (!c.isDirectory()) continue;
      for (const f of readdirSync(join(r, c.name))) {
        const m = LINK.test(f) && STAMP.exec(f);
        if (m) newest = Math.max(newest, new Date(+m[1], m[2] - 1, +m[3], +m[4], +m[5], +m[6], +(m[7] ?? 0)).getTime());
      }
    }
  }
  return newest;
}

// One reminder per session, once it has run `after` minutes with no link saved since it started.
// Prints nothing and exits 0 on any problem: hooks call it after every turn.
function remind(opt) {
  let since = Number(opt.since) || 0;
  const hook = opt.hook ? JSON.parse(readFileSync(0, "utf8")) : null;
  if (hook) {
    if (hook.stop_hook_active) return;
    if (hook.cwd) process.chdir(hook.cwd);
    opt.session ??= hook.session_id;
    try { since = statSync(hook.transcript_path).birthtimeMs; } catch {}
  }
  const session = String(opt.session ?? "").replace(/[^\w.-]/g, "_").slice(0, 128);
  if (!session) return;
  const dir = join(process.env.XDG_STATE_HOME || join(homedir(), ".local/state"), "chains", "remind");
  mkdirSync(dir, { recursive: true });
  const now = Date.now();
  for (const f of readdirSync(dir)) try { if (now - statSync(join(dir, f)).mtimeMs > 7 * 86_400_000) unlinkSync(join(dir, f)); } catch {}
  const file = join(dir, session);
  let state;
  try { state = JSON.parse(readFileSync(file, "utf8")); } catch {
    // A session older than 6h when the hook first sees it (e.g. resumed days later) counts from now.
    state = { first: since < now && now - since < 6 * 3_600_000 ? since : now, reminded: false };
    writeFileSync(file, JSON.stringify(state));
  }
  if (newestLink() >= state.first) return;
  const minutes = Math.round((now - state.first) / 60_000);
  if (opt.hook === "claude-precompact")
    return void process.stdout.write(`End the summary with this line, verbatim: "[chains reminder] No chain link was saved before this compaction. If this session's work is worth keeping, save a link with the chains skill before continuing."\n`);
  if (state.reminded || minutes < Number(opt.after ?? process.env.CHAINS_REMIND_AFTER ?? 30)) return;
  writeFileSync(file, JSON.stringify({ ...state, reminded: true }));
  const text = `[chains reminder] About ${minutes} min of work since this session started and no chain link saved. If any of it is worth keeping, save a link with the chains skill now; otherwise ignore this.`;
  process.stdout.write(`${opt.hook === "claude-stop" ? JSON.stringify({ decision: "block", reason: text }) : text}\n`);
}

const { pos: [cmd, ...pos], opt } = parseArgs(process.argv.slice(2));
const print = (data, text) => process.stdout.write(`${opt.json ? JSON.stringify(data, null, 2) : text}\n`);

switch (cmd) {
  case "root":
    print({ root: root() }, root());
    break;
  case "save": {
    const l = save(name(pos[0], "chain"), opt);
    print(strip(l), `saved ${l.path}`);
    break;
  }
  case "load": {
    const l = pick(name(pos[0], "chain"), opt.branch, opt.link);
    print({ ...strip(l), content: l.body }, `# ${l.chain}@${l.branch}/${l.file}${age(l)}\n\n${l.body.trim()}`);
    break;
  }
  case "context": {
    const { current, parents, recent } = context(name(pos[0], "chain"), opt);
    const block = (label, l) => `## ${label}: ${l.file}${age(l)}\nNext step: ${l.nextStep ?? "(none)"}\n\n${l.body.trim()}`;
    print(
      { current: { ...strip(current), content: current.body }, parents: parents.map((l) => ({ ...strip(l), content: l.body })), recent: recent.map(strip) },
      [`# Chain context: ${current.chain}@${current.branch}`, block("Current", current), ...parents.map((l, i) => block(`Parent ${i + 1}`, l)), recent.length ? `## Recent\n${recent.map((l) => `- ${line(l)}`).join("\n")}` : ""].filter(Boolean).join("\n\n"),
    );
    break;
  }
  case "list": {
    if (pos[0]) {
      const all = links(name(pos[0], "chain"));
      print(all.map(strip), all.map(line).join("\n") || `no links in ${pos[0]}`);
    } else {
      const all = chains().map((c) => {
        const ls = links(c);
        return { chain: c, count: ls.length, branches: [...new Set(ls.map((l) => l.branch))], latest: ls[0] ? strip(ls[0]) : null };
      }).filter((i) => i.count).sort((a, b) => b.latest.file.localeCompare(a.latest.file));
      const items = all.slice(0, Math.max(1, Number(opt.max) || Infinity));
      const C = fileURLToPath(import.meta.url), cut = (t) => (t.length > 120 ? `${t.slice(0, 119)}…` : t);
      const item = (i) => `- ${i.chain}  ${i.count} links  [${i.branches.join(", ")}]${i.latest ? `  latest: ${cut(i.latest.title)}${age(i.latest)}${i.latest.nextStep ? `  → next: ${cut(i.latest.nextStep)}` : ""}` : ""}`;
      if (opt.json) print(items);
      else if (items.length)
        print(items, [
          `Chains (saved work context) in ${root()}, newest first${items.length < all.length ? ` (${items.length} of ${all.length})` : ""}:`,
          ...items.map(item),
          `Before continuing one of these: node ${C} context <chain>`,
        ].join("\n"));
    }
    break;
  }
  case "remind":
    try { remind(opt); } catch {}
    break;
  case "search": {
    const hits = search(pos.join(" "), opt.chain);
    print(hits, hits.map((h) => `${h.chain}/${h.file}:${h.line}  ${h.snippet}`).join("\n") || "no matches");
    break;
  }
  case "fork": {
    const chain = name(pos[0], "chain"), branch = name(pos[1], "branch");
    if (branch === "main") fail("fork into a new branch, not main");
    if (links(chain, branch).length) fail(`branch ${branch} already has links`);
    const parent = opt.from ? pick(chain, undefined, opt.from) : pick(chain, opt["from-branch"]);
    print({ chain, branch, parent: parent.file }, `parent: ${parent.file}\nnext: chain save ${chain} --branch ${branch} --parent ${parent.file} < link.md`);
    break;
  }
  default:
    print({ usage: USAGE }, USAGE);
    if (cmd && cmd !== "help" && cmd !== "--help") process.exit(1);
}
