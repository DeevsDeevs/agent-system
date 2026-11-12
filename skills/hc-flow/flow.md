# flow.mjs scripts

The script starts with a plain `meta` literal, then a body with top-level `await` and
`return`, with no imports:

```js
export const meta = { name: 'review-auth', description: 'Three lenses on src/auth, then a judge' }
phase('Review')
const lenses = ['correctness', 'security', 'tests']
const found = await parallel(lenses.map((lens) => () =>
  agent(`Review src/auth through the ${lens} lens only. READ-ONLY. List concrete issues with file:line.`, { label: lens, cwd: args.repo })))
phase('Judge')
return await agent(`Merge these reviews, drop duplicates and anything unproven:\n\n${found.filter(Boolean).join('\n\n---\n\n')}`, {
  harness: 'claude', label: 'judge', cwd: args.repo,
  schema: { type: 'object', required: ['issues'], properties: { issues: { type: 'array' } } },
})
```

- `agent(prompt, opts)` starts one worker, briefs it, and resolves with its result file's
  text (with `schema`, the parsed object). It rejects with the reason when the worker errors,
  exits, times out or writes no valid result after one retry. Options:
  - `harness`: `'pi'` (default), `'claude'` or `'codex'`. `model`: the harness's own model
    string; omit for its default.
  - `cwd` (default: the runner's), `on` (an hc machine), `label` (the terminal is named
    `<run>-<label>`).
  - `schema`: a JSON schema. The worker writes one JSON object; the runner checks that it's
    an object with the required keys.
  - `args`: extra CLI args for the harness, for example `['--permission-mode', 'acceptEdits']`
    for claude. claude starts with `--permission-mode auto` unless `args` sets a mode; the
    runner adds no other permission flags, only `--add-dir <run dir>` for claude and codex
    so they can write the result file, and `--no-daemon` for codex.
  - `timeout`: seconds for the whole agent (default 1800). `phase`: shown in its start line.
- A worker that is `blocked`, or not ready within 60 s (a trust or login prompt), is left
  running for the person. The runner prints `BLOCKED <name> <address>: <screen>`, lists it
  in `result.json`, and `agent()` rejects. Workers belong to the terminal that started the
  runner, so a blocked one outlives the runner.
- `parallel(thunks)` takes functions, waits for all, and turns a rejection into `null`.
  `pipeline(items, ...stages)` moves each item through the stages on its own; a stage gets
  `(previous, item, index)`, and a throw or `null` ends that item as `null`. Prefer
  `pipeline` over chained `parallel` calls unless a stage needs every earlier result.
- `phase(title)` and `log(text)` print progress lines; `args` is `--args` parsed as JSON.
- Ctrl-C or `hc kill flow-<name>` removes the workers the runner started and exits 130.
- Workers get your brief plus a footer: write the answer to `<run dir>/<name>.md` (or
  `.json`), finish the turn, don't `hc send`, start no other agents. Finishing the turn is
  the signal. The runner isn't an agent and can't receive messages. With `on`, the result
  is written in that machine's state dir and read back with `hc file read --on`.
- Not yet: resuming a stopped run, a worktree per writer, cost caps. For writers that
  touch the same repo, give each its own files or folder, or run them one after another.
