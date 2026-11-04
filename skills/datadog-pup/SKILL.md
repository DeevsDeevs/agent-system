---
name: datadog-pup
description: "Inspect and operate Datadog with the pup CLI: logs, metrics, monitors, APM, incidents, dashboards, SLOs, Live Debugger, Service Catalog."
---

# Datadog via Pup

Pup is broad and self-describing; prefer live command discovery over memorized flags.

## First moves

1. `which pup && pup --version && pup auth status`. This user's org is on `datadoghq.eu` — export `DD_SITE=datadoghq.eu` for the session. If auth is missing/expired, ask the user to run `pup auth login` or provide the right `DD_SITE`. Do not loop on 401/403.
2. Discover before guessing: `pup agent schema --compact` (command map), `pup agent guide`, `pup <domain> --help`. `FORCE_AGENT_MODE=1` turns help into JSON — never use it for writes without `--read-only`; agent mode may auto-approve prompts.
3. Prefer `--output=json`, `--read-only`, explicit `--from`, and small limits:

```bash
DD_SITE=datadoghq.eu pup --read-only logs search --query="status:error" --from="1h" --limit=20 --output=json
```

## Safety rules

- Treat Datadog as production data. Default to read-only; writes (create/update/delete, downtimes, debugger probes, workflow runs, key/user/config changes) need explicit confirmation with the exact command or JSON body shown first.
- Use API-side filters/aggregation; never fetch huge datasets to post-process locally. Always pass `--from`; start narrow (15m–1h, low limits) and widen only with a reason.
- Redact secrets, tokens, emails, user IDs, and sensitive attributes unless explicitly needed. Preserve IDs and links so findings are auditable.
- 401/403: stop, report auth/scope issue, suggest `pup auth refresh`/`login` or key scopes. 429: back off and narrow.

## Common read workflows

Logs — count first, then sample. Query syntax: `status:error`, `service:api`, `env:prod`, `@http.status_code:[500 TO 599]`, quoted phrases, `AND`/`OR`, negation:

```bash
pup --read-only logs aggregate --query="status:error env:prod" --from="1h" --compute="count" --group-by="service" --output=json
pup --read-only logs search --query="status:error env:prod service:<svc>" --from="1h" --limit=20 --output=json
```

Metrics — shape `<aggregation>:<metric>{<scope>} by {<group>}`:

```bash
pup --read-only metrics query --query="avg:system.cpu.user{env:prod} by {host}" --from="1h" --output=json
pup --read-only metrics list --filter="trace.*" --output=json
```

APM/traces — **durations in trace search are often nanoseconds: `1s = 1000000000`**:

```bash
pup --read-only apm services stats --env production --from="1h" --output=json
pup --read-only traces search --query="service:<svc> status:error" --from="1h" --limit=20 --output=json
pup --read-only traces aggregate --query="service:<svc>" --from="1h" --compute="avg(@duration)" --group-by="resource_name" --output=json
```

Monitors/SLOs/incidents — filter monitor lists by `service:`/`team:`/`env:`/status in large orgs:

```bash
pup --read-only monitors search --query="status:Alert" --output=json
pup --read-only slos list --output=json
pup --read-only incidents list --query="status:active" --output=json
```

Service Catalog — use before guessing ownership, on-call, dependencies, or health: `pup --read-only idp find|assist|owner|deps <service> --output=json`.

Live Debugger / Symbol DB — can affect production; explicit user approval only. Before creating a probe confirm service, env, location, captures, TTL, and cleanup; prefer capture expressions over full snapshots; short TTL; delete after use.

```bash
pup --read-only debugger context <service> --fields service,language,envs
pup --read-only symdb search --service <service> --query "Controller" --view probe-locations
```

Run a probe watch in hc so it doesn't block you: `hc run --bg --name pup-watch pup debugger probes watch <id> --timeout 60 --limit 10 --fields message,captures,timestamp`, then `hc wait pup-watch` and `hc read pup-watch`.

## Writes

Explain the change → prepare a body file (`pup monitors create --file monitor.json`) → validate with list/get → show the exact command → get confirmation → execute with the smallest scope → verify with a read → record created IDs and rollback steps. `--yes` only after user approval, never to bypass ambiguity.

## Domain map

`pup agent schema --compact` for the live list. Common: `logs`, `metrics`, `traces`, `apm`, `monitors`/`downtime`, `slos`, `incidents`/`on-call`/`cases`, `dashboards`/`notebooks`, `idp`/`service-catalog`, `security`/`audit-logs`/`csm-threats`, `rum`/`synthetics`/`error-tracking`, `cloud`/`infrastructure`/`containers`/`network`/`processes`, `usage`/`costs`, `debugger`/`symdb`, `workflows`/`runbooks`/`investigations`/`bits`.

Some domains need API/app keys even with OAuth; if scopes are unsupported/insufficient, report it and ask for the right credential path.

## Reporting

Summarize — no raw JSON dumps unless requested: what I checked (command + range + filters), findings (counts/trends/top offenders + IDs/links), caveats (auth/site/sampling/retention), and one or two next safe queries. For incidents, preserve chronology: deploys/events → monitor state → log spikes → trace latency/errors → infra metrics → active incidents.
