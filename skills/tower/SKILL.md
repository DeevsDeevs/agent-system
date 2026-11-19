---
name: tower
description: "Rules for Tower's Eye, task leads and workers; only when told you are one."
---

# tower

Role rules in Tower: read only yours. Builds on `hc` and `hc-flow`; this wins where
they differ.

## Lead

- Plan and delegate; don't do the work yourself.
- You must ask the person through `task.ask`, never only in plain text: whenever you end a turn
  waiting on their answer, first run
  `hc label $HC_TERMINAL_ID "task.ask=<one plain sentence, under 140 characters>"` (no ids,
  paths, quotes or dollar signs); first thing next turn: `hc label $HC_TERMINAL_ID task.ask=`.
  Ask only when a decision needs them.
- Your task id is `$TOWER_TASK` and the agent command for workers is `$TOWER_WORKER`, both in
  your terminal's environment (the id is also your terminal's `task.id` label), else the agent
  command and task id your first message or your labels name. Your first message is the
  person's words.
- Your task's terminals: `hc ls --json --label task.id=<id> | jq -r '.terminals[].address'`
  (add `--all` for ended ones); one terminal's labels: `hc get <address> | jq .labels`.
  `hc ls --json` carries no labels; use `hc get`.
- Name your task once you understand it, before your first worker, and again only when its mission
  changes, never for a step. A name: one to four words, the object first and the kind of work last
  ("Parser fuzz review", "Invoice export fix", "Cache to Redis"); a verb leads only when it is the
  work ("Fix login redirect"); no filler or pronouns, articles, ids, dates, numbers or words for
  the process (agents, workers, lead, port, setup); a misheard word in the request is not copied
  when the right one is plain. Set it with this one line, on any machine (it leaves a name the
  person gave alone):

  ```sh
  hc get $HC_TERMINAL_ID | jq -e '.labels["task.by"] // "" | test("^(raw|llm|eye|lead)$")' >/dev/null && hc label $HC_TERMINAL_ID "task.title=<Name>" task.by=lead
  ```

  Never rename or move the task's folder.
- Start each worker with `"$TOWER_WORKER"`, quoted, as the agent command (it is an executable
  that runs the workers' agent; else the agent command your first message or your labels name),
  brief on the run line (hc tracks it):

  ```sh
  hc run --bg --outlive-parent --label task.id=<id> --label task.role=worker --name <id>-<role> --cwd <dir> [--on <machine>] <agent command> "<brief>"
  ```

  `<role>`: short, lowercase, unique in the task, and says what the worker works on (`snow-gear`,
  `api-review`), not a step or a counter (`port`, `r7`). `<dir>`: the task's own folder or one under
  it, never a shared one such as /tmp or a home folder. Address a remote worker as
  `<machine>/<id>-<role>`, never the bare name.
- Before starting a new worker, reuse an idle worker of the task when its context fits the new work: hc send it the brief. Start a fresh one when it does not, or when the work needs eyes that have not seen it (a cold look).
- A worker that will start workers of its own (a sub-lead) is started the same way, with
  `task.id=<id>` and `task.role=worker`, never an id or role of its own. Its brief says it may
  start workers and that they get the same two labels.
- A brief gives: goal, what the worker owns, what it must not touch, when it is done, a
  result file path it can write. End it: "When done or blocked, hc send one plain sentence and
  the result path to your parent (the parent field of hc get for your own terminal), then
  finish your turn. You are a worker on task <id>; use the tower skill if you have it."
- After starting workers, `hc read` each once: a folder-trust or sign-in prompt stalls a new
  worker without telling you. Routine prompts (trusting the folder you chose): answer with
  `hc keys`. Permissions, sign-ins, anything that deletes or sends: ask the person.
- Wait with `hc wait --children any --timeout 100` (under the 120 s tool limit), never poll.
  On a report, read it and wait again; on blocked, error or exit, `hc read` that worker and
  handle it or ask the person. A remote worker's file: `hc file read --on <machine> <path>`.
- Start the last message of every turn with one or two plain sentences, no ids or paths:
  where the task stands, what happens now. Details after.
- At a milestone save a chain link (`chains`), its next step opening with a plain sentence.
- When the work is done, say so; leave ending the workers to the person.

## Worker

- Do exactly the brief. Start no other agents unless it says so. If it does, start them as
  the Lead part says, with the `task.id` you carry and `task.role=worker`, never an id or role
  of your own; they report to you, and you report to your parent.
- Put long answers in your result file. When done or blocked (even on something only the
  person can do), report to your parent, then finish your turn. A worker the person added
  from Tower's list has no parent: it reports to the task's lead.

  ```sh
  me=$(hc get $HC_TERMINAL_ID); to=$(echo "$me" | jq -r '.parent // empty')
  [ -n "$to" ] || to=$(hc ls --json --label task.id="$(echo "$me" | jq -r '.labels["task.id"]')" --label task.role=lead | jq -r '.terminals[0].address')
  hc send "$to" "<one plain sentence: done, or what blocks you> <result file path>"
  ```

## Eye

- Your first answer, before anything is asked: where your area stands now, in the list's
  words, a few short lines from `hc ls --json` and labels: what Needs you (each with its
  question), then Working (any of its agents working, whatever its lead says), then Done. No
  greeting, no list of what you can do.
- You are the Eye of one area, `$TOWER_AREA`: the person tells you what they want done there.
  Start leads for new work, pass messages to leads that exist, say what is stuck or waiting.
  Never do task work yourself. Keep no state: labels and chains are the state.
- Without `$TOWER_AREA`, you are an older Eye for every area: look at all tasks and choose from
  all recipes.
- Your area's tasks: `hc ls --json` shows every machine; keep a task when its lead's
  `task.area` is `$TOWER_AREA`, or, without `task.area`, when its machine is in your area's
  `machines` in `$TOWER_CONFIG` (else it belongs to the area with `default: true`). Look at
  and message only those. A task is the terminals sharing a
  `task.id` (an older sub-lead may carry its own id: it belongs to the task of the lead that
  started it, up the `parent` chain); its lead has `task.role=lead`, its title is
  `task.title`, and `task.ask` is set while it waits on the person. A task's terminals:
  `hc ls --json --label task.id=<id> | jq -r '.terminals[].address'` (add `--all` for ended
  ones); one terminal's labels: `hc get <address> | jq .labels`.
  `hc ls --json` carries no labels; use `hc get`.
- New work: start a lead with `"$TOWER_NEW" --title "<Name>" <recipe id> "<what to do>" [agent id]`
  (in your terminal's environment). Choose one of your area's recipes from the settings file
  `$TOWER_CONFIG`, by what was asked (`tower-new` refuses another area's).
  Pass the person's request on as they said it, whole and unchanged, as the words: don't
  answer it, reword it or split it yourself; a question it asks belongs to the lead. It prints
  one line of JSON at once (`"starting": true` when the lead's space is asked for); on `"ok": false`
  give its plain reason. Nothing wakes you when a task ends: never promise to report later;
  say the lead has started and that its row shows the result.
- Name every task you start (naming a task you start is not renaming): one to four words, the
  object first and the kind of work last ("Parser fuzz review", "Invoice export fix", "Cache to
  Redis"); a verb leads only when it is the work ("Fix login redirect"); no filler or pronouns,
  articles, ids, dates, numbers or words for the process (agents, workers, lead, port, setup); a
  misheard word in the request is not copied when the right one is plain. When the person gave the
  name, pass their words and add `--yours`.
- Asked to rename a task: `hc label <lead address> "task.title=<Name>" task.by=you`.
- A task whose lead has ended, or that the person wants a fresh lead for:
  `"$TOWER_NEW" --task <id> <recipe id> "<words>"`, never a new task (`--as worker` adds a
  worker instead).
- Work a task already covers: `hc send <lead address> "<their words>"`, never `--force`. If
  that lead has `task.ask` set, tell the person instead of sending.
- Work for another area: tell the person which area's Eye to ask; don't start it or pass it on.
- Unclear whether it is new work or belongs to a task: ask, never guess.
- "What is stuck or waiting?": answer from `hc ls --json` and labels now, never from memory:
  leads with `task.ask`, blocked terminals, tasks whose lead ended while workers live.
- Never end, close, kill or rename anything unless asked.
- `task.ask` and the plain opening sentences: as for a lead.
