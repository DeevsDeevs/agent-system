#!/usr/bin/env node
// Deterministic gate engine for the agentic-tdd skill. Zero dependencies.
// All behavioral decisions consume typed fields; prose is display-only.
// Threat model: gates and hashes defend against cooperative-agent drift and
// accidents, not against a malicious same-user process (see references/permissions.md).

import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

export const TRANSITIONS = {
	NEW: ["PLANNING"],
	PLANNING: ["WAITING_FOR_USER_PLAN", "PLAN_READY", "BUDGET_EXHAUSTED"],
	WAITING_FOR_USER_PLAN: ["PLANNING"],
	PLAN_READY: ["PLAN_APPROVED", "PLANNING"],
	PLAN_APPROVED: ["LOOP_RUNNING", "PLANNING"],
	LOOP_RUNNING: ["BLOCKED_SPEC", "BLOCKED_ORACLE", "BLOCKED_ENVIRONMENT", "CANDIDATE_READY", "BUDGET_EXHAUSTED"],
	BLOCKED_SPEC: ["PLANNING"],
	BLOCKED_ORACLE: ["PLANNING"],
	BLOCKED_ENVIRONMENT: ["LOOP_RUNNING"],
	CANDIDATE_READY: ["ASSESSING", "LOOP_RUNNING"],
	ASSESSING: ["WAITING_FOR_USER_ASSESS", "CHANGES_REQUIRED", "ASSESSMENT_READY", "PLANNING", "BUDGET_EXHAUSTED"],
	WAITING_FOR_USER_ASSESS: ["ASSESSING"],
	CHANGES_REQUIRED: ["LOOP_RUNNING"],
	ASSESSMENT_READY: ["ASSESSMENT_ACCEPTED", "ASSESSING", "LOOP_RUNNING", "PLANNING"],
	ASSESSMENT_ACCEPTED: ["RELEASING"],
	RELEASING: ["WAITING_FOR_USER_RELEASE", "RELEASE_BLOCKED", "CLOSED", "PLANNING", "LOOP_RUNNING", "ASSESSING"],
	WAITING_FOR_USER_RELEASE: ["RELEASING"],
	RELEASE_BLOCKED: ["PLANNING"],
	BUDGET_EXHAUSTED: ["PLANNING", "LOOP_RUNNING", "ASSESSING"],
	CLOSED: [],
};

// Transitions that start or resume work; every other transition must carry a
// result whose (phase, status) pair is bound to that edge in RESULT_GATES.
const START_TRANSITIONS = new Set([
	"NEW>PLANNING",
	"WAITING_FOR_USER_PLAN>PLANNING",
	"BLOCKED_SPEC>PLANNING",
	"BLOCKED_ORACLE>PLANNING",
	"PLAN_APPROVED>LOOP_RUNNING",
	"BLOCKED_ENVIRONMENT>LOOP_RUNNING",
	"CANDIDATE_READY>ASSESSING",
	"WAITING_FOR_USER_ASSESS>ASSESSING",
	"CHANGES_REQUIRED>LOOP_RUNNING",
	"ASSESSMENT_ACCEPTED>RELEASING",
	"WAITING_FOR_USER_RELEASE>RELEASING",
	"RELEASE_BLOCKED>PLANNING",
	"BUDGET_EXHAUSTED>PLANNING",
	"BUDGET_EXHAUSTED>LOOP_RUNNING",
	"BUDGET_EXHAUSTED>ASSESSING",
]);

// Edge-specific result binding: which result phase and statuses may drive each transition.
const RESULT_GATES = {
	"PLANNING>WAITING_FOR_USER_PLAN": { phases: ["plan"], statuses: ["WAITING_FOR_USER", "NEEDS_HUMAN_DOMAIN_INPUT"] },
	"PLANNING>PLAN_READY": { phases: ["plan"], statuses: ["PLAN_READY"] },
	"PLANNING>BUDGET_EXHAUSTED": { phases: ["plan"], statuses: ["BUDGET_EXHAUSTED"] },
	"PLAN_READY>PLAN_APPROVED": { phases: ["plan", "challenge"], statuses: ["PLAN_READY", "NO_BLOCKERS"] },
	"PLAN_READY>PLANNING": { phases: ["plan", "challenge"], statuses: ["PLAN_REVISION_REQUIRED", "ESCALATE_LIGHT_TO_FULL", "NEEDS_REPOSITORY_EVIDENCE", "USER_DECISION_REQUIRED"] },
	"PLAN_APPROVED>PLANNING": { phases: ["plan", "loop"], statuses: ["PLAN_AMENDMENT_REQUIRED", "PLAN_REVISION_REQUIRED"] },
	"LOOP_RUNNING>BLOCKED_SPEC": { phases: ["loop"], statuses: ["BLOCKED_SPEC"] },
	"LOOP_RUNNING>BLOCKED_ORACLE": { phases: ["loop"], statuses: ["BLOCKED_ORACLE"] },
	"LOOP_RUNNING>BLOCKED_ENVIRONMENT": { phases: ["loop"], statuses: ["BLOCKED_ENVIRONMENT"] },
	"LOOP_RUNNING>CANDIDATE_READY": { phases: ["loop"], statuses: ["CANDIDATE_READY"] },
	"LOOP_RUNNING>BUDGET_EXHAUSTED": { phases: ["loop"], statuses: ["BUDGET_EXHAUSTED", "IMPLEMENTATION_FAILED"] },
	"CANDIDATE_READY>LOOP_RUNNING": { phases: ["challenge", "assess"], statuses: ["NEW_IMPLEMENTATION_FINDING", "CHANGES_REQUIRED"] },
	"ASSESSING>WAITING_FOR_USER_ASSESS": { phases: ["assess"], statuses: ["HUMAN_DECISION_REQUIRED", "WAITING_FOR_USER"] },
	"ASSESSING>CHANGES_REQUIRED": { phases: ["assess"], statuses: ["CHANGES_REQUIRED"] },
	"ASSESSING>ASSESSMENT_READY": { phases: ["assess"], statuses: ["PASS", "PASS_WITH_NONBLOCKING_FINDINGS"] },
	"ASSESSING>PLANNING": { phases: ["assess"], statuses: ["PLAN_AMENDMENT_REQUIRED"] },
	"ASSESSING>BUDGET_EXHAUSTED": { phases: ["assess"], statuses: ["BUDGET_EXHAUSTED", "ASSESSMENT_INCONCLUSIVE"] },
	"ASSESSMENT_READY>ASSESSMENT_ACCEPTED": { phases: ["assess", "challenge"], statuses: ["PASS", "PASS_WITH_NONBLOCKING_FINDINGS", "ASSESSMENT_ACCEPTED", "NO_BLOCKERS"] },
	"ASSESSMENT_READY>ASSESSING": { phases: ["challenge"], statuses: ["MORE_EVIDENCE_REQUIRED", "INCONCLUSIVE", "FINDING_RECLASSIFICATION_REQUIRED"] },
	"ASSESSMENT_READY>LOOP_RUNNING": { phases: ["challenge"], statuses: ["NEW_IMPLEMENTATION_FINDING"] },
	"ASSESSMENT_READY>PLANNING": { phases: ["challenge"], statuses: ["PLAN_AMBIGUITY_FOUND"] },
	"RELEASING>WAITING_FOR_USER_RELEASE": { phases: ["release"], statuses: ["USER_SIGNOFF_REQUIRED"] },
	"RELEASING>RELEASE_BLOCKED": { phases: ["release"], statuses: ["RELEASE_BLOCKED"] },
	"RELEASING>CLOSED": { phases: ["release"], statuses: ["RELEASE_APPROVED"] },
	"RELEASING>PLANNING": { phases: ["release"], statuses: ["RETURN_TO_PLAN"] },
	"RELEASING>LOOP_RUNNING": { phases: ["release"], statuses: ["RETURN_TO_LOOP"] },
	"RELEASING>ASSESSING": { phases: ["release"], statuses: ["RETURN_TO_ASSESS", "INSUFFICIENT_EVIDENCE"] },
};

const RESULT_PHASES = new Set(["plan", "loop", "assess", "release", "challenge"]);
const QUESTION_CLASSES = new Set(["BLOCKING_DOMAIN", "BLOCKING_POLICY", "NONBLOCKING_ASSUMPTION", "OPTIONAL_PREFERENCE"]);
const CHALLENGE_PHASES = new Set(["plan", "loop", "assess"]);
const CHALLENGE_STATES = new Set(["not_invoked", "prepared", "ingested", "dispositioned", "skipped"]);
const CHALLENGE_VERDICTS = new Set([
	"NO_BLOCKERS", "PLAN_REVISION_REQUIRED", "USER_DECISION_REQUIRED", "ESCALATE_LIGHT_TO_FULL",
	"INCONCLUSIVE", "NEW_IMPLEMENTATION_FINDING", "MORE_EVIDENCE_REQUIRED", "PLAN_AMBIGUITY_FOUND",
	"FINDING_RECLASSIFICATION_REQUIRED", "ASSESSMENT_ACCEPTED",
]);
const DISPOSITIONS = new Set(["ACCEPTED", "REJECTED_WITH_EVIDENCE", "MORE_EVIDENCE_REQUIRED", "USER_DECISION_REQUIRED", "PARKED_NONBLOCKING", "DUPLICATE"]);
const SEVERITIES = new Set(["critical", "major", "minor"]);
const REVIEW_DECISIONS = new Set(["RELEASE_APPROVED", "RETURN_TO_PLAN", "RETURN_TO_LOOP", "RETURN_TO_ASSESS", "USER_SIGNOFF_REQUIRED", "RELEASE_BLOCKED", "INSUFFICIENT_EVIDENCE"]);
const PROTECTION_MODES = new Set(["auto", "flags", "chmod", "none"]);
const UNPROTECT_STATES = new Set(["CLOSED", "RELEASE_BLOCKED"]);
const DEPTHS = new Set(["auto", "light", "full"]);
const CHECKPOINT_STATES = new Set(["PLAN_READY", "PLAN_APPROVED", "CANDIDATE_READY", "ASSESSMENT_READY", "ASSESSMENT_ACCEPTED", "CLOSED"]);
const FREEZE_STATES = { plan: "PLANNING", loop: "LOOP_RUNNING", assess: "ASSESSING", release: "RELEASING" };
const BUDGET_COUNTERS = new Set([
	"planning_revisions",
	"semantic_replans",
	"implementation_repairs",
	"external_challenges",
]);
const BUILTIN_BUDGETS = {
	light: { planning_revisions: 1, semantic_replans: 1, implementation_repairs: 1, external_challenges: 1 },
	full: { planning_revisions: 3, semantic_replans: 2, implementation_repairs: 3, external_challenges: 3 },
};
const STALE_LOCK_MS = 15 * 60 * 1000;
const DEFAULT_CHECK_OUTPUT_CAP = 1024 * 1024;

class EngineError extends Error {
	constructor(code, message) {
		super(message);
		this.code = code;
	}
}

const fail = (code, message) => { throw new EngineError(code, message); };

function git(root, args, env) {
	return execFileSync("git", args, { cwd: root, encoding: "utf8", env: env ? { ...process.env, ...env } : undefined }).trim();
}

function canonicalJson(value) {
	if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
	if (value && typeof value === "object") {
		return `{${Object.keys(value).sort().map((k) => `${JSON.stringify(k)}:${canonicalJson(value[k])}`).join(",")}}`;
	}
	return JSON.stringify(value);
}

const sha256 = (data) => createHash("sha256").update(data).digest("hex");
const hashFile = (file) => `sha256:${sha256(fs.readFileSync(file))}`;
const hashObject = (obj) => `sha256:${sha256(canonicalJson(obj))}`;

function featureDir(root, feature) {
	if (typeof feature !== "string" || !/^[a-z0-9][a-z0-9._-]*$/.test(feature) || feature.includes("..")) {
		fail("INVALID_FEATURE_ID", `Feature id must be [a-z0-9._-], got: ${feature}`);
	}
	return path.join(root, ".tdd", feature);
}

// Realpath-based containment: rejects escapes AND any symlinked path component,
// including symlinked ancestors that physically point outside the repository.
function resolveInsideRoot(root, file) {
	const realRoot = fs.realpathSync(root);
	const resolved = path.resolve(realRoot, file);
	const rel = path.relative(realRoot, resolved);
	if (rel.startsWith("..") || path.isAbsolute(rel)) fail("PATH_ESCAPE", `Path escapes repository root: ${file}`);
	let probe = resolved;
	while (!fs.existsSync(probe)) probe = path.dirname(probe);
	if (fs.realpathSync(probe) !== probe) fail("SYMLINK_REJECTED", `Symlinked path component is not allowed: ${file}`);
	if (fs.existsSync(resolved) && fs.lstatSync(resolved).isSymbolicLink()) fail("SYMLINK_REJECTED", `Symlinks are not allowed: ${file}`);
	return resolved;
}

function atomicWriteJson(file, value) {
	const tmp = `${file}.${process.pid}.tmp`;
	fs.writeFileSync(tmp, `${JSON.stringify(value, null, "\t")}\n`);
	fs.renameSync(tmp, file);
}

const readJson = (file) => JSON.parse(fs.readFileSync(file, "utf8"));
const manifestPath = (dir) => path.join(dir, "manifest.json");
const protectedPath = (dir) => path.join(dir, "protected-manifest.json");
const checksIndexPath = (dir) => path.join(dir, "checks", "index.jsonl");

function loadManifest(root, feature) {
	const file = manifestPath(featureDir(root, feature));
	if (!fs.existsSync(file)) fail("NOT_INITIALIZED", `No manifest for feature '${feature}'. Run init first.`);
	return readJson(file);
}

function saveManifest(root, feature, manifest) {
	atomicWriteJson(manifestPath(featureDir(root, feature)), manifest);
}

function lockDir(root, feature) {
	return path.join(featureDir(root, feature), ".lock");
}

function withLock(root, feature, fn) {
	const lock = lockDir(root, feature);
	try {
		fs.mkdirSync(lock);
	} catch (error) {
		if (error.code === "EEXIST") fail("LOCKED", `Feature '${feature}' is locked by another writer (${lock}). Use 'unlock ${feature} --stale' if the holder crashed.`);
		throw error;
	}
	try {
		atomicWriteJson(path.join(lock, "meta.json"), { pid: process.pid, host: os.hostname(), started_at: new Date().toISOString() });
		return fn();
	} finally {
		fs.rmSync(lock, { recursive: true, force: true });
	}
}

export function unlock(root, feature, options = {}) {
	const lock = lockDir(root, feature);
	if (!fs.existsSync(lock)) return { released: false, reason: "not_locked" };
	if (options.force) {
		fs.rmSync(lock, { recursive: true, force: true });
		return { released: true, reason: "forced" };
	}
	if (!options.stale) fail("UNLOCK_REFUSED", "Refusing to unlock a live lock. Pass stale (dead holder) or force.");
	const metaFile = path.join(lock, "meta.json");
	const meta = fs.existsSync(metaFile) ? readJson(metaFile) : null;
	let dead = !meta;
	if (meta && meta.host === os.hostname()) {
		try {
			process.kill(meta.pid, 0);
		} catch {
			dead = true;
		}
	}
	const old = meta && Date.now() - Date.parse(meta.started_at) > STALE_LOCK_MS;
	if (!dead && !old) fail("LOCK_NOT_STALE", `Lock holder pid=${meta.pid} on ${meta.host} appears alive and recent.`);
	fs.rmSync(lock, { recursive: true, force: true });
	return { released: true, reason: dead ? "dead_holder" : "expired_lease" };
}

export function appendEvent(root, feature, type, data = {}) {
	const line = { ts: new Date().toISOString(), type, ...data };
	fs.appendFileSync(path.join(featureDir(root, feature), "events.jsonl"), `${JSON.stringify(line)}\n`);
	return line;
}

// NUL-delimited porcelain parsing; rename/copy records carry a second path field.
function worktreeStatus(root) {
	const raw = execFileSync("git", ["status", "--porcelain=v1", "-z"], { cwd: root, encoding: "utf8" });
	const fields = raw.split("\0").filter((f) => f.length > 0);
	const modified = [];
	const untracked = [];
	for (let i = 0; i < fields.length; i++) {
		const record = fields[i];
		const xy = record.slice(0, 2);
		const file = record.slice(3);
		if (xy === "??") untracked.push(file);
		else modified.push(file);
		if (xy[0] === "R" || xy[0] === "C") i++;
	}
	return { modified, untracked };
}

// Exact candidate identity, independent of user-visible commits: stage the whole
// worktree (tracked + untracked, .gitignore respected) into a temporary index.
function computeWorktree(root, feature) {
	const idx = path.join(featureDir(root, feature), `.index-${process.pid}`);
	try {
		const env = { GIT_INDEX_FILE: idx };
		git(root, ["add", "-A"], env);
		return git(root, ["write-tree"], env);
	} finally {
		fs.rmSync(idx, { force: true });
	}
}

function snapshotCandidate(root, feature, runId) {
	const tree = computeWorktree(root, feature);
	const head = git(root, ["rev-parse", "HEAD"]);
	const commit = git(root, [
		"-c", "user.name=agentic-tdd", "-c", "user.email=tdd@local",
		"commit-tree", tree, "-p", head, "-m", `agentic-tdd candidate ${feature}/${runId}`,
	]);
	const ref = `refs/agentic-tdd/${feature}/candidate/${runId}`;
	git(root, ["update-ref", ref, commit]);
	return { tree, commit, ref };
}

function detectTestCommand(root) {
	const pkg = path.join(root, "package.json");
	if (fs.existsSync(pkg) && readJson(pkg).scripts?.test) return "npm test";
	if (fs.existsSync(path.join(root, "CMakeLists.txt"))) return "ctest --test-dir build";
	if (fs.existsSync(path.join(root, "pyproject.toml")) || fs.existsSync(path.join(root, "pytest.ini"))) return "pytest";
	if (fs.existsSync(path.join(root, "Cargo.toml"))) return "cargo test";
	return null;
}

function loadProfile(depth, domains = []) {
	const profileDir = path.join(path.dirname(new URL(import.meta.url).pathname), "..", "profiles");
	const effectiveDepth = depth === "auto" ? "light" : depth;
	let profile = { budgets: { ...BUILTIN_BUDGETS[effectiveDepth] }, required_check_ids: [] };
	const merge = (file) => {
		if (!fs.existsSync(file)) return;
		const data = readJson(file);
		profile.budgets = {
			planning_revisions: data.planning?.maximum_revisions ?? profile.budgets.planning_revisions,
			semantic_replans: data.loop?.semantic_replans ?? profile.budgets.semantic_replans,
			implementation_repairs: data.loop?.maximum_repair_rounds ?? profile.budgets.implementation_repairs,
			external_challenges: data.external_challenge?.maximum_total
				?? (data.external_challenge?.maximum_per_phase_version ? data.external_challenge.maximum_per_phase_version * 3 : profile.budgets.external_challenges),
		};
		if (Array.isArray(data.assessment?.required_check_ids)) {
			profile.required_check_ids = [...new Set([...profile.required_check_ids, ...data.assessment.required_check_ids])];
		}
	};
	merge(path.join(profileDir, `${effectiveDepth}.json`));
	for (const domain of domains) merge(path.join(profileDir, `${domain}.json`));
	return profile;
}

const budgetRemaining = (manifest, counter) => {
	const profile = loadProfile(manifest.feature.depth, manifest.feature.domains);
	return (profile.budgets[counter] ?? 0) + (manifest.budgets.extra[counter] ?? 0) - (manifest.budgets.used[counter] ?? 0);
};

export function init(root, feature, options = {}) {
	const depth = options.depth ?? "auto";
	if (!DEPTHS.has(depth)) fail("INVALID_DEPTH", `Unknown depth: ${depth} (auto|light|full)`);
	const domains = options.domains ?? [];
	const protection = options.protection ?? "auto";
	if (!PROTECTION_MODES.has(protection)) fail("INVALID_PROTECTION", `Unknown protection_mode: ${protection}`);

	const dir = featureDir(root, feature);
	if (fs.existsSync(manifestPath(dir))) fail("ALREADY_INITIALIZED", `Feature '${feature}' already exists.`);

	let baseline;
	try {
		baseline = git(root, ["rev-parse", "HEAD"]);
	} catch {
		fail("NOT_A_GIT_REPO", `Target root is not a git repository with commits: ${root}`);
	}
	const status = worktreeStatus(root);
	if (status.modified.length && !options.allowDirty) {
		fail("DIRTY_WORKTREE", `Tracked files modified: ${status.modified.join(", ")}. Ask the USER, then re-run with allowDirty.`);
	}

	fs.mkdirSync(dir, { recursive: true });
	for (const sub of ["input", "decisions/questions", "decisions/answers", "decisions/waivers", "plan", "loop", "assess", "challenges", "release", "checks", "results"]) {
		fs.mkdirSync(path.join(dir, sub), { recursive: true });
	}

	const manifest = {
		schema_version: 2,
		feature: { id: feature, title: options.title ?? feature, depth, domains },
		workflow: { state: "NEW" },
		repository: {
			baseline_commit: baseline,
			candidate_tree: null,
			candidate_commit: null,
			candidate_ref: null,
			branch: git(root, ["rev-parse", "--abbrev-ref", "HEAD"]),
			test_command: options.testCommand ?? detectTestCommand(root),
			untracked_at_init: status.untracked,
		},
		current: { plan_version: null, loop_run: null, assessment_run: null },
		options: {
			protection_mode: protection,
			challenges: {
				plan: options.challenges?.includes("plan") ?? false,
				loop: options.challenges?.includes("loop") ?? false,
				assess: options.challenges?.includes("assess") ?? false,
			},
			models: options.models ?? {},
		},
		integrity: {},
		budgets: { used: {}, extra: {} },
		questions: { open: {} },
		challenges: {
			plan: { state: "not_invoked" },
			loop: { state: "not_invoked" },
			assess: { state: "not_invoked" },
		},
		release: { reviewer_status: "not_started", decision: null, candidate_tree: null, report_hash: null },
	};
	saveManifest(root, feature, manifest);
	appendEvent(root, feature, "init", { depth, domains, baseline_commit: baseline });
	return manifest;
}

export function setDepth(root, feature, depth, options = {}) {
	if (!DEPTHS.has(depth) || depth === "auto") fail("INVALID_DEPTH", `set-depth requires light or full, got: ${depth}`);
	return withLock(root, feature, () => {
		const manifest = loadManifest(root, feature);
		if (manifest.workflow.state !== "PLANNING") fail("WRONG_STATE", `set-depth allowed only in PLANNING; state is ${manifest.workflow.state}.`);
		const previous = manifest.feature.depth;
		manifest.feature.depth = depth;
		saveManifest(root, feature, manifest);
		appendEvent(root, feature, "set_depth", { from: previous, to: depth, evidence: options.evidence ?? null });
		return { depth, previous };
	});
}

const unresolvedBlocking = (manifest) =>
	Object.values(manifest.questions.open).filter((c) => c.startsWith("BLOCKING_")).length;

function challengeSatisfied(manifest, phase) {
	const state = manifest.challenges[phase].state;
	if (state === "dispositioned" || state === "skipped") return true;
	if (state === "not_invoked") return !manifest.options.challenges[phase];
	return false;
}

function requiredChecksSatisfied(root, feature, manifest) {
	const required = loadProfile(manifest.feature.depth, manifest.feature.domains).required_check_ids;
	if (!required.length) return { ok: true, missing: [] };
	const indexFile = checksIndexPath(featureDir(root, feature));
	const records = fs.existsSync(indexFile)
		? fs.readFileSync(indexFile, "utf8").trim().split("\n").filter(Boolean).map((l) => JSON.parse(l))
		: [];
	const missing = required.filter((id) =>
		!records.some((r) => r.check_id === id && r.exit_code === 0 && r.candidate_tree === manifest.repository.candidate_tree));
	return { ok: missing.length === 0, missing };
}

function validateResult(result, edge) {
	for (const field of ["phase", "run_id", "status", "requested_transition"]) {
		if (typeof result?.[field] !== "string" || !result[field]) fail("INVALID_RESULT", `Result missing required string field: ${field}`);
	}
	if (!RESULT_PHASES.has(result.phase)) fail("INVALID_RESULT", `Unknown result phase: ${result.phase}`);
	const gate = RESULT_GATES[edge];
	if (!gate) fail("INVALID_RESULT", `No result gate defined for ${edge}.`);
	if (!gate.phases.includes(result.phase)) {
		fail("RESULT_PHASE_MISMATCH", `${edge} accepts result phases [${gate.phases.join(", ")}], got '${result.phase}'.`);
	}
	if (!gate.statuses.includes(result.status)) {
		fail("RESULT_STATUS_MISMATCH", `${edge} accepts statuses [${gate.statuses.join(", ")}], got '${result.status}'.`);
	}
	const to = edge.split(">")[1];
	if (result.requested_transition !== to) {
		fail("RESULT_MISMATCH", `Result requests ${result.requested_transition}, transition is to ${to}.`);
	}
}

function checkGates(root, feature, manifest, from, to) {
	if (CHECKPOINT_STATES.has(to) && unresolvedBlocking(manifest) > 0) {
		fail("BLOCKING_QUESTIONS_OPEN", `${unresolvedBlocking(manifest)} blocking user question(s) open; answer or waive them first.`);
	}
	if (from === "PLAN_READY" && to === "PLAN_APPROVED" && !challengeSatisfied(manifest, "plan")) {
		fail("CHALLENGE_PENDING", `Plan challenge is ${manifest.challenges.plan.state}; disposition or skip it before approval.`);
	}
	if (from === "CANDIDATE_READY" && to === "ASSESSING" && !challengeSatisfied(manifest, "loop")) {
		fail("CHALLENGE_PENDING", `Loop challenge is ${manifest.challenges.loop.state}; disposition or skip it before assessment.`);
	}
	if (from === "ASSESSMENT_READY" && to === "ASSESSMENT_ACCEPTED" && !challengeSatisfied(manifest, "assess")) {
		fail("CHALLENGE_PENDING", `Assess challenge is ${manifest.challenges.assess.state}; disposition or skip it before acceptance.`);
	}
	if (from === "ASSESSING" && to === "ASSESSMENT_READY") {
		const checks = requiredChecksSatisfied(root, feature, manifest);
		if (!checks.ok) {
			fail("REQUIRED_CHECKS_MISSING", `No passing engine-executed record bound to the candidate for: ${checks.missing.join(", ")}. Use run-check.`);
		}
	}
	if (to === "CLOSED") {
		if (manifest.release.decision !== "RELEASE_APPROVED") {
			fail("REVIEW_MISSING", `Release reviewer decision is '${manifest.release.decision ?? "absent"}'; ingest a RELEASE_APPROVED report first.`);
		}
		if (manifest.release.candidate_tree !== manifest.repository.candidate_tree) {
			fail("REVIEW_STALE", "Reviewer report is bound to a different candidate tree than the current one.");
		}
		for (const phase of CHALLENGE_PHASES) {
			if (!challengeSatisfied(manifest, phase)) fail("CHALLENGE_PENDING", `Challenge '${phase}' is ${manifest.challenges[phase].state}.`);
		}
		const waiverDir = path.join(featureDir(root, feature), "decisions", "waivers");
		for (const file of fs.readdirSync(waiverDir)) {
			const waiver = readJson(path.join(waiverDir, file));
			if (Date.parse(waiver.expires) < Date.now()) fail("WAIVER_EXPIRED", `Waiver ${waiver.id} expired ${waiver.expires}.`);
		}
	}
}

export function transition(root, feature, to, options = {}) {
	return withLock(root, feature, () => {
		const manifest = loadManifest(root, feature);
		const from = manifest.workflow.state;
		const edge = `${from}>${to}`;
		if (!(to in TRANSITIONS)) fail("UNKNOWN_STATE", `Unknown state: ${to}`);
		if (!TRANSITIONS[from].includes(to)) fail("ILLEGAL_TRANSITION", `${from} → ${to} is not a legal transition.`);

		let result = null;
		if (!START_TRANSITIONS.has(edge)) {
			if (!options.resultFile) fail("RESULT_REQUIRED", `${edge.replace(">", " → ")} requires a phase result file.`);
			result = readJson(resolveInsideRoot(root, options.resultFile));
			validateResult(result, edge);
		}

		checkGates(root, feature, manifest, from, to);

		const report = verifyManifest(root, feature, manifest);
		if (!report.ok) {
			fail("VERIFY_FAILED", `Evidence chain is not intact: ${report.problems.map((p) => p.code).join(", ")}. Resolve before transitioning.`);
		}

		if (to === "LOOP_RUNNING" && from !== "BLOCKED_ENVIRONMENT") {
			manifest.repository.candidate_tree = null;
			manifest.repository.candidate_commit = null;
			manifest.repository.candidate_ref = null;
		}
		if (to === "CANDIDATE_READY") {
			const snapshot = snapshotCandidate(root, feature, result?.run_id ?? "run");
			manifest.repository.candidate_tree = snapshot.tree;
			manifest.repository.candidate_commit = snapshot.commit;
			manifest.repository.candidate_ref = snapshot.ref;
		}

		manifest.workflow.state = to;
		saveManifest(root, feature, manifest);
		appendEvent(root, feature, "transition", { from, to, run_id: result?.run_id ?? null, status: result?.status ?? null });
		return { from, to, state: to, candidate_tree: manifest.repository.candidate_tree };
	});
}

export function freeze(root, feature, phase, files) {
	return withLock(root, feature, () => {
		const manifest = loadManifest(root, feature);
		const requiredState = FREEZE_STATES[phase];
		if (!requiredState) fail("INVALID_PHASE", `freeze phase must be one of: ${Object.keys(FREEZE_STATES).join(", ")}`);
		if (manifest.workflow.state !== requiredState) {
			fail("WRONG_STATE", `freeze '${phase}' allowed only in ${requiredState}; state is ${manifest.workflow.state}.`);
		}
		const hashes = {};
		for (const file of files) {
			const resolved = resolveInsideRoot(root, file);
			if (!fs.existsSync(resolved)) fail("MISSING_ARTIFACT", `Cannot freeze missing file: ${file}`);
			hashes[path.relative(fs.realpathSync(root), resolved)] = hashFile(resolved);
		}
		manifest.integrity[phase] = { commit: git(root, ["rev-parse", "HEAD"]), files: hashes };
		saveManifest(root, feature, manifest);
		appendEvent(root, feature, "freeze", { phase, files: Object.keys(hashes) });
		return manifest.integrity[phase];
	});
}

function applyProtection(file, mode) {
	if (mode === "none") return "hash_only";
	const useFlags = mode === "flags" || (mode === "auto" && (process.platform === "darwin" || process.getuid?.() === 0));
	if (useFlags) {
		try {
			if (process.platform === "darwin") execFileSync("chflags", ["uchg", file]);
			else execFileSync("chattr", ["+i", file]);
			return process.platform === "darwin" ? "chflags" : "chattr";
		} catch {
			if (mode === "flags") fail("PROTECTION_FAILED", `Immutable flag failed for ${file}; requires root on linux. Use protection_mode chmod or none.`);
		}
	}
	fs.chmodSync(file, 0o444);
	return "chmod";
}

function removeProtection(file, method) {
	if (method === "chflags") execFileSync("chflags", ["nouchg", file]);
	else if (method === "chattr") execFileSync("chattr", ["-i", file]);
	else if (method === "chmod") fs.chmodSync(file, 0o644);
}

export function protect(root, feature, files) {
	return withLock(root, feature, () => {
		const manifest = loadManifest(root, feature);
		const file = protectedPath(featureDir(root, feature));
		const entries = fs.existsSync(file) ? readJson(file) : [];
		const known = new Set(entries.map((e) => e.path));
		for (const raw of files) {
			const resolved = resolveInsideRoot(root, raw);
			if (!fs.existsSync(resolved)) fail("MISSING_ARTIFACT", `Cannot protect missing file: ${raw}`);
			const rel = path.relative(fs.realpathSync(root), resolved);
			if (known.has(rel)) continue;
			const method = applyProtection(resolved, manifest.options.protection_mode);
			entries.push({ path: rel, hash: hashFile(resolved), method });
		}
		atomicWriteJson(file, entries);
		manifest.integrity.protected_manifest_hash = hashObject(entries);
		saveManifest(root, feature, manifest);
		appendEvent(root, feature, "protect", { files: entries.map((e) => e.path) });
		return entries;
	});
}

export function unprotect(root, feature) {
	return withLock(root, feature, () => {
		const manifest = loadManifest(root, feature);
		if (!UNPROTECT_STATES.has(manifest.workflow.state)) {
			fail("UNPROTECT_FORBIDDEN", `Unprotect allowed only in ${[...UNPROTECT_STATES].join("/")}; state is ${manifest.workflow.state}.`);
		}
		const file = protectedPath(featureDir(root, feature));
		const entries = fs.existsSync(file) ? readJson(file) : [];
		for (const entry of entries) removeProtection(path.resolve(root, entry.path), entry.method);
		atomicWriteJson(file, []);
		manifest.integrity.protected_manifest_hash = hashObject([]);
		saveManifest(root, feature, manifest);
		appendEvent(root, feature, "unprotect", { files: entries.map((e) => e.path) });
		return { released: entries.length };
	});
}

function verifyManifest(root, feature, manifest) {
	const problems = [];

	const file = protectedPath(featureDir(root, feature));
	const entries = fs.existsSync(file) ? readJson(file) : [];
	if (manifest.integrity.protected_manifest_hash && manifest.integrity.protected_manifest_hash !== hashObject(entries)) {
		problems.push({ code: "PROTECTED_MANIFEST_TAMPERED", path: path.relative(root, file) });
	}
	for (const entry of entries) {
		const target = path.resolve(root, entry.path);
		if (!fs.existsSync(target)) problems.push({ code: "PROTECTED_FILE_DELETED", path: entry.path });
		else if (hashFile(target) !== entry.hash) problems.push({ code: "PROTECTED_FILE_MODIFIED", path: entry.path });
	}

	for (const [phase, record] of Object.entries(manifest.integrity)) {
		if (typeof record !== "object" || !record?.files) continue;
		for (const [rel, hash] of Object.entries(record.files)) {
			const target = path.resolve(root, rel);
			if (!fs.existsSync(target)) problems.push({ code: "FROZEN_ARTIFACT_DELETED", phase, path: rel });
			else if (hashFile(target) !== hash) problems.push({ code: "FROZEN_ARTIFACT_MODIFIED", phase, path: rel });
		}
	}

	if (manifest.repository.candidate_tree) {
		const currentTree = computeWorktree(root, feature);
		if (currentTree !== manifest.repository.candidate_tree) {
			problems.push({ code: "CANDIDATE_TREE_DRIFT", expected: manifest.repository.candidate_tree, actual: currentTree });
		}
	}

	const status = worktreeStatus(root);
	return { ok: problems.length === 0, state: manifest.workflow.state, problems, untracked: status.untracked, modified: status.modified };
}

export function verify(root, feature) {
	return verifyManifest(root, feature, loadManifest(root, feature));
}

export function consumeBudget(root, feature, counter) {
	if (!BUDGET_COUNTERS.has(counter)) fail("UNKNOWN_BUDGET", `Unknown budget counter: ${counter}`);
	return withLock(root, feature, () => {
		const manifest = loadManifest(root, feature);
		if (budgetRemaining(manifest, counter) <= 0) {
			fail("BUDGET_EXHAUSTED", `Budget exhausted: ${counter}. Transition to BUDGET_EXHAUSTED or ask the USER for a grant.`);
		}
		manifest.budgets.used[counter] = (manifest.budgets.used[counter] ?? 0) + 1;
		saveManifest(root, feature, manifest);
		const remaining = budgetRemaining(manifest, counter);
		appendEvent(root, feature, "budget", { counter, remaining });
		return { counter, remaining };
	});
}

export function grantBudget(root, feature, counter, n, authorizedBy) {
	if (!BUDGET_COUNTERS.has(counter)) fail("UNKNOWN_BUDGET", `Unknown budget counter: ${counter}`);
	if (!authorizedBy) fail("AUTHORITY_REQUIRED", "grant requires authorized-by (the USER or domain owner).");
	const units = n ?? 1;
	if (!Number.isInteger(units) || units < 1) fail("INVALID_GRANT", `Grant units must be a positive integer, got: ${n}`);
	return withLock(root, feature, () => {
		const manifest = loadManifest(root, feature);
		manifest.budgets.extra[counter] = (manifest.budgets.extra[counter] ?? 0) + units;
		saveManifest(root, feature, manifest);
		const remaining = budgetRemaining(manifest, counter);
		appendEvent(root, feature, "budget_grant", { counter, units, authorized_by: authorizedBy, remaining });
		return { counter, remaining, authorized_by: authorizedBy };
	});
}

export function questionOpen(root, feature, questionFile) {
	return withLock(root, feature, () => {
		const manifest = loadManifest(root, feature);
		const question = readJson(resolveInsideRoot(root, questionFile));
		for (const field of ["id", "class", "question"]) {
			if (typeof question?.[field] !== "string" || !question[field]) fail("INVALID_QUESTION", `Question missing required string field: ${field}`);
		}
		if (!QUESTION_CLASSES.has(question.class)) fail("INVALID_QUESTION", `Unknown question class: ${question.class}`);
		if (manifest.questions.open[question.id]) fail("QUESTION_EXISTS", `Question ${question.id} is already open.`);
		atomicWriteJson(path.join(featureDir(root, feature), "decisions", "questions", `${question.id}.json`), question);
		manifest.questions.open[question.id] = question.class;
		saveManifest(root, feature, manifest);
		appendEvent(root, feature, "question_open", { id: question.id, class: question.class });
		return { id: question.id, class: question.class, unresolved_blocking: unresolvedBlocking(manifest) };
	});
}

function resolveQuestion(root, feature, id, record, eventType) {
	return withLock(root, feature, () => {
		const manifest = loadManifest(root, feature);
		if (!manifest.questions.open[id]) fail("QUESTION_NOT_OPEN", `Question ${id} is not open.`);
		atomicWriteJson(path.join(featureDir(root, feature), "decisions", "answers", `${id}.json`), { id, ts: new Date().toISOString(), ...record });
		delete manifest.questions.open[id];
		saveManifest(root, feature, manifest);
		appendEvent(root, feature, eventType, { id });
		return { id, unresolved_blocking: unresolvedBlocking(manifest) };
	});
}

export function questionAnswer(root, feature, id, answer) {
	if (!answer) fail("INVALID_ANSWER", "answer requires the user's decision text or option id.");
	return resolveQuestion(root, feature, id, { answer }, "question_answer");
}

export function questionWaive(root, feature, id, authorizedBy) {
	if (!authorizedBy) fail("AUTHORITY_REQUIRED", "waiving a question requires authorized-by.");
	return resolveQuestion(root, feature, id, { waived_by: authorizedBy }, "question_waive");
}

const CHALLENGE_BOUNDARY = { plan: "PLAN_READY", loop: "CANDIDATE_READY", assess: "ASSESSMENT_READY" };

function challengeDir(root, feature, phase) {
	return path.join(featureDir(root, feature), "challenges", phase);
}

export function challengePrepare(root, feature, phase) {
	if (!CHALLENGE_PHASES.has(phase)) fail("INVALID_PHASE", `Challenge phase must be plan|loop|assess, got: ${phase}`);
	return withLock(root, feature, () => {
		const manifest = loadManifest(root, feature);
		if (manifest.workflow.state !== CHALLENGE_BOUNDARY[phase]) {
			fail("WRONG_STATE", `Challenge '${phase}' prepares at ${CHALLENGE_BOUNDARY[phase]}; state is ${manifest.workflow.state}.`);
		}
		if (manifest.challenges[phase].state !== "not_invoked" && manifest.challenges[phase].state !== "skipped") {
			fail("CHALLENGE_ACTIVE", `Challenge '${phase}' is already ${manifest.challenges[phase].state}.`);
		}
		if (budgetRemaining(manifest, "external_challenges") <= 0) {
			fail("BUDGET_EXHAUSTED", "Budget exhausted: external_challenges. Ask the USER for a grant.");
		}
		manifest.budgets.used.external_challenges = (manifest.budgets.used.external_challenges ?? 0) + 1;
		fs.mkdirSync(challengeDir(root, feature, phase), { recursive: true });
		manifest.challenges[phase] = { state: "prepared", candidate_tree: manifest.repository.candidate_tree };
		saveManifest(root, feature, manifest);
		appendEvent(root, feature, "challenge_prepare", { phase });
		return { phase, state: "prepared", packet_dir: path.relative(root, challengeDir(root, feature, phase)) };
	});
}

export function challengeIngest(root, feature, phase, responseFile) {
	return withLock(root, feature, () => {
		const manifest = loadManifest(root, feature);
		if (manifest.challenges[phase]?.state !== "prepared") {
			fail("WRONG_STATE", `Challenge '${phase}' must be prepared before ingest; it is ${manifest.challenges[phase]?.state}.`);
		}
		const resolved = resolveInsideRoot(root, responseFile);
		const response = readJson(resolved);
		if (!CHALLENGE_VERDICTS.has(response?.verdict?.value)) fail("INVALID_RESPONSE", `Unknown challenge verdict: ${response?.verdict?.value}`);
		if (!Array.isArray(response.findings)) fail("INVALID_RESPONSE", "Challenge response requires a findings array.");
		for (const finding of response.findings) {
			if (typeof finding?.id !== "string" || !finding.id) fail("INVALID_RESPONSE", "Every finding requires a string id.");
			if (!SEVERITIES.has(finding.severity)) fail("INVALID_RESPONSE", `Finding ${finding.id}: severity must be critical|major|minor.`);
			if (typeof finding.claim !== "string" || !finding.claim) fail("INVALID_RESPONSE", `Finding ${finding.id}: claim is required.`);
		}
		fs.copyFileSync(resolved, path.join(challengeDir(root, feature, phase), "response.json"));
		manifest.challenges[phase] = {
			...manifest.challenges[phase],
			state: "ingested",
			response_hash: hashFile(resolved),
			provenance: response.provenance ?? null,
			finding_ids: response.findings.map((f) => f.id),
		};
		saveManifest(root, feature, manifest);
		appendEvent(root, feature, "challenge_ingest", { phase, findings: response.findings.length, verdict: response.verdict.value });
		return { phase, state: "ingested", findings: response.findings.length };
	});
}

export function challengeDispose(root, feature, phase, dispositionFile) {
	return withLock(root, feature, () => {
		const manifest = loadManifest(root, feature);
		if (manifest.challenges[phase]?.state !== "ingested") {
			fail("WRONG_STATE", `Challenge '${phase}' must be ingested before disposition; it is ${manifest.challenges[phase]?.state}.`);
		}
		const resolved = resolveInsideRoot(root, dispositionFile);
		const body = readJson(resolved);
		if (!Array.isArray(body?.dispositions)) fail("INVALID_DISPOSITION", "Disposition file requires a dispositions array.");
		const response = readJson(path.join(challengeDir(root, feature, phase), "response.json"));
		const bySeverity = new Map(response.findings.map((f) => [f.id, f]));
		const seen = new Set();
		for (const item of body.dispositions) {
			const finding = bySeverity.get(item?.finding);
			if (!finding) fail("INVALID_DISPOSITION", `Disposition references unknown finding: ${item?.finding}`);
			if (!DISPOSITIONS.has(item.disposition)) fail("INVALID_DISPOSITION", `Unknown disposition: ${item.disposition}`);
			// Critical findings cannot be dismissed by prose: rejection demands evidence
			// refs; parking is not available at critical severity.
			if (finding.severity === "critical") {
				if (item.disposition === "PARKED_NONBLOCKING") fail("CRITICAL_UNDISMISSABLE", `Critical finding ${finding.id} cannot be parked.`);
				if (item.disposition === "REJECTED_WITH_EVIDENCE" && !(Array.isArray(item.evidence) && item.evidence.length)) {
					fail("CRITICAL_UNDISMISSABLE", `Rejecting critical finding ${finding.id} requires evidence references.`);
				}
			}
			seen.add(item.finding);
		}
		const missing = response.findings.filter((f) => !seen.has(f.id)).map((f) => f.id);
		if (missing.length) fail("INVALID_DISPOSITION", `Every finding needs a disposition; missing: ${missing.join(", ")}`);
		fs.copyFileSync(resolved, path.join(challengeDir(root, feature, phase), "disposition.json"));
		manifest.challenges[phase] = { ...manifest.challenges[phase], state: "dispositioned", disposition_hash: hashFile(resolved) };
		saveManifest(root, feature, manifest);
		appendEvent(root, feature, "challenge_dispose", { phase, dispositions: body.dispositions.length });
		return { phase, state: "dispositioned" };
	});
}

export function challengeSkip(root, feature, phase, reason) {
	if (!CHALLENGE_PHASES.has(phase)) fail("INVALID_PHASE", `Challenge phase must be plan|loop|assess, got: ${phase}`);
	if (typeof reason !== "string" || !reason) fail("REASON_REQUIRED", "Skipping a challenge requires a recorded reason.");
	return withLock(root, feature, () => {
		const manifest = loadManifest(root, feature);
		const state = manifest.challenges[phase].state;
		if (state !== "not_invoked" && state !== "prepared") fail("WRONG_STATE", `Cannot skip challenge '${phase}' in state ${state}.`);
		manifest.challenges[phase] = { state: "skipped", reason };
		saveManifest(root, feature, manifest);
		appendEvent(root, feature, "challenge_skip", { phase, reason });
		return { phase, state: "skipped" };
	});
}

export function reviewIngest(root, feature, reportFile) {
	return withLock(root, feature, () => {
		const manifest = loadManifest(root, feature);
		if (manifest.workflow.state !== "RELEASING") fail("WRONG_STATE", `review ingest allowed only in RELEASING; state is ${manifest.workflow.state}.`);
		const resolved = resolveInsideRoot(root, reportFile);
		const report = readJson(resolved);
		if (!REVIEW_DECISIONS.has(report?.decision)) fail("INVALID_REVIEW", `Unknown reviewer decision: ${report?.decision}`);
		if (report.candidate_tree !== manifest.repository.candidate_tree) {
			fail("REVIEW_STALE", "Reviewer report must name the exact current candidate_tree it reviewed.");
		}
		fs.copyFileSync(resolved, path.join(featureDir(root, feature), "release", "reviewer-report.json"));
		manifest.release = {
			reviewer_status: "ingested",
			decision: report.decision,
			candidate_tree: report.candidate_tree,
			report_hash: hashFile(resolved),
		};
		saveManifest(root, feature, manifest);
		appendEvent(root, feature, "review_ingest", { decision: report.decision });
		return { decision: report.decision };
	});
}

export function waiverAuthorize(root, feature, waiverFile) {
	return withLock(root, feature, () => {
		loadManifest(root, feature);
		const waiver = readJson(resolveInsideRoot(root, waiverFile));
		for (const field of ["id", "authorized_by", "rationale", "expires"]) {
			if (typeof waiver?.[field] !== "string" || !waiver[field]) fail("INVALID_WAIVER", `Waiver missing required string field: ${field}`);
		}
		if (!Number.isFinite(Date.parse(waiver.expires)) || Date.parse(waiver.expires) < Date.now()) {
			fail("INVALID_WAIVER", `Waiver expiry must be a future date, got: ${waiver.expires}`);
		}
		atomicWriteJson(path.join(featureDir(root, feature), "decisions", "waivers", `${waiver.id}.json`), waiver);
		appendEvent(root, feature, "waiver_authorize", { id: waiver.id, authorized_by: waiver.authorized_by, expires: waiver.expires });
		return { id: waiver.id, expires: waiver.expires };
	});
}

// Engine-owned check execution: assessors interpret this evidence but cannot
// manufacture it. Records bind to the candidate tree computed at start time.
export function runCheck(root, feature, checkId, argv, options = {}) {
	if (!/^[a-z0-9][a-z0-9._-]*$/.test(checkId ?? "")) fail("INVALID_CHECK_ID", `Check id must be [a-z0-9._-], got: ${checkId}`);
	if (!Array.isArray(argv) || !argv.length) fail("INVALID_CHECK", "run-check requires argv after --");
	const manifest = loadManifest(root, feature);
	const cwd = options.cwd ? resolveInsideRoot(root, options.cwd) : fs.realpathSync(root);
	const cap = options.maxBytes ?? DEFAULT_CHECK_OUTPUT_CAP;
	const treeAtStart = computeWorktree(root, feature);
	const started = Date.now();
	let exitCode = 0;
	let stdout = "";
	let stderr = "";
	try {
		stdout = execFileSync(argv[0], argv.slice(1), { cwd, encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
	} catch (error) {
		if (error.status === undefined && !error.stdout && !error.stderr) fail("CHECK_SPAWN_FAILED", `Could not execute ${argv[0]}: ${error.message}`);
		exitCode = error.status ?? 1;
		stdout = error.stdout?.toString() ?? "";
		stderr = error.stderr?.toString() ?? "";
	}
	const dir = path.join(featureDir(root, feature), "checks");
	const seq = fs.readdirSync(dir).filter((f) => f.startsWith(`${checkId}-`) && f.endsWith(".out")).length + 1;
	const base = path.join(dir, `${checkId}-${String(seq).padStart(3, "0")}`);
	fs.writeFileSync(`${base}.out`, stdout.slice(0, cap));
	fs.writeFileSync(`${base}.err`, stderr.slice(0, cap));
	const record = {
		check_id: checkId,
		seq,
		argv,
		cwd: path.relative(fs.realpathSync(root), cwd) || ".",
		candidate_tree: treeAtStart,
		bound_to_candidate: treeAtStart === manifest.repository.candidate_tree,
		environment: { platform: process.platform, node: process.version },
		started_at: new Date(started).toISOString(),
		duration_ms: Date.now() - started,
		exit_code: exitCode,
		stdout_hash: `sha256:${sha256(stdout)}`,
		stderr_hash: `sha256:${sha256(stderr)}`,
		truncated: stdout.length > cap || stderr.length > cap,
	};
	fs.appendFileSync(checksIndexPath(featureDir(root, feature)), `${JSON.stringify(record)}\n`);
	appendEvent(root, feature, "run_check", { check_id: checkId, exit_code: exitCode, bound_to_candidate: record.bound_to_candidate });
	return record;
}

export function assessWorktree(root, feature, options = {}) {
	const manifest = loadManifest(root, feature);
	const dir = path.join(featureDir(root, feature), "assess", "worktree");
	if (options.remove) {
		git(root, ["worktree", "remove", "--force", dir]);
		appendEvent(root, feature, "assess_worktree_remove", {});
		return { removed: true };
	}
	if (!manifest.repository.candidate_commit) fail("NO_CANDIDATE", "No candidate snapshot exists; reach CANDIDATE_READY first.");
	if (fs.existsSync(dir)) fail("WORKTREE_EXISTS", `Assessment worktree already exists: ${dir}`);
	git(root, ["worktree", "add", "--detach", dir, manifest.repository.candidate_commit]);
	appendEvent(root, feature, "assess_worktree_add", { candidate_commit: manifest.repository.candidate_commit });
	return { path: dir, candidate_commit: manifest.repository.candidate_commit, candidate_tree: manifest.repository.candidate_tree };
}

const RUN_DIR_KEYS = { plan: "plan_version", loop: "loop_run", assessment: "assessment_run" };

export function runBegin(root, feature, phase) {
	const group = phase === "plan" ? "plan" : phase === "loop" ? "loop" : phase === "assess" ? "assessment" : null;
	if (!group) fail("INVALID_PHASE", `run begin phase must be plan|loop|assess, got: ${phase}`);
	return withLock(root, feature, () => {
		loadManifest(root, feature);
		const parent = path.join(featureDir(root, feature), phase === "assess" ? "assess" : phase);
		const existing = fs.readdirSync(parent).filter((f) => !f.startsWith(".")).length;
		const runId = phase === "plan" ? `v${String(existing + 1).padStart(3, "0")}` : `run-${String(existing + 1).padStart(3, "0")}`;
		fs.mkdirSync(path.join(parent, `${runId}.partial`), { recursive: true });
		appendEvent(root, feature, "run_begin", { phase, run_id: runId });
		return { phase, run_id: runId, dir: path.relative(root, path.join(parent, `${runId}.partial`)) };
	});
}

export function runPublish(root, feature, phase, runId) {
	const key = phase === "plan" ? "plan_version" : phase === "loop" ? "loop_run" : phase === "assess" ? "assessment_run" : null;
	if (!key) fail("INVALID_PHASE", `run publish phase must be plan|loop|assess, got: ${phase}`);
	return withLock(root, feature, () => {
		const manifest = loadManifest(root, feature);
		const parent = path.join(featureDir(root, feature), phase === "assess" ? "assess" : phase);
		const partial = path.join(parent, `${runId}.partial`);
		const final = path.join(parent, runId);
		if (!fs.existsSync(partial)) fail("MISSING_RUN", `No partial run directory: ${path.relative(root, partial)}`);
		if (fs.existsSync(final)) fail("RUN_EXISTS", `Run already published: ${path.relative(root, final)}`);
		fs.renameSync(partial, final);
		manifest.current[key] = runId;
		saveManifest(root, feature, manifest);
		appendEvent(root, feature, "run_publish", { phase, run_id: runId });
		return { phase, run_id: runId, dir: path.relative(root, final) };
	});
}

const NEXT_COMMANDS = {
	NEW: "transition PLANNING",
	PLANNING: "produce plan artifacts, then transition PLAN_READY",
	WAITING_FOR_USER_PLAN: "question answer/waive, then transition PLANNING",
	PLAN_READY: "challenge plan or skip, then transition PLAN_APPROVED",
	PLAN_APPROVED: "protect acceptance tests, then transition LOOP_RUNNING",
	LOOP_RUNNING: "implement, then transition CANDIDATE_READY",
	BLOCKED_SPEC: "transition PLANNING (amend)",
	BLOCKED_ORACLE: "transition PLANNING (amend)",
	BLOCKED_ENVIRONMENT: "fix environment, then transition LOOP_RUNNING",
	CANDIDATE_READY: "challenge loop or skip, then transition ASSESSING",
	ASSESSING: "run-check required checks, then transition ASSESSMENT_READY",
	WAITING_FOR_USER_ASSESS: "question answer/waive, then transition ASSESSING",
	CHANGES_REQUIRED: "transition LOOP_RUNNING (repair, consume budget)",
	ASSESSMENT_READY: "challenge assess or skip, then transition ASSESSMENT_ACCEPTED",
	ASSESSMENT_ACCEPTED: "transition RELEASING",
	RELEASING: "review ingest, then transition CLOSED",
	WAITING_FOR_USER_RELEASE: "question answer/waive, then transition RELEASING",
	RELEASE_BLOCKED: "transition PLANNING or stop",
	BUDGET_EXHAUSTED: "grant budget, then transition back to the owning phase",
	CLOSED: "unprotect, append memory observations",
};

export function status(root, feature) {
	const manifest = loadManifest(root, feature);
	const profile = loadProfile(manifest.feature.depth, manifest.feature.domains);
	const budgets = {};
	for (const counter of BUDGET_COUNTERS) budgets[counter] = budgetRemaining(manifest, counter);
	return {
		feature: manifest.feature,
		state: manifest.workflow.state,
		allowed_next: TRANSITIONS[manifest.workflow.state],
		required_next: NEXT_COMMANDS[manifest.workflow.state],
		repository: manifest.repository,
		current: manifest.current,
		budgets,
		required_check_ids: profile.required_check_ids,
		unresolved_blocking: unresolvedBlocking(manifest),
		open_questions: manifest.questions.open,
		options: manifest.options,
		challenges: manifest.challenges,
		release: manifest.release,
	};
}

function parseArgs(argv) {
	const positional = [];
	const flags = {};
	let passthrough = null;
	for (let i = 0; i < argv.length; i++) {
		if (argv[i] === "--") {
			passthrough = argv.slice(i + 1);
			break;
		}
		if (argv[i].startsWith("--")) {
			const key = argv[i].slice(2);
			flags[key] = argv[i + 1] !== undefined && !argv[i + 1].startsWith("--") ? argv[++i] : true;
		} else positional.push(argv[i]);
	}
	return { positional, flags, passthrough };
}

function main() {
	const { positional, flags, passthrough } = parseArgs(process.argv.slice(2));
	const [command, ...args] = positional;
	const root = path.resolve(flags.root ?? process.cwd());

	const run = () => {
		switch (command) {
			case "init":
				return init(root, args[0], {
					depth: flags.depth, title: flags.title, protection: flags.protection,
					domains: flags.domains ? flags.domains.split(",") : [],
					challenges: flags.challenges ? flags.challenges.split(",") : [],
					testCommand: flags["test-command"], allowDirty: flags["allow-dirty"] === true,
					models: flags.models ? JSON.parse(flags.models) : {},
				});
			case "status": return status(root, args[0]);
			case "transition": return transition(root, args[0], args[1], { resultFile: flags.result });
			case "freeze": return freeze(root, args[0], args[1], (flags.files ?? "").split(",").filter(Boolean));
			case "protect": return protect(root, args[0], args.slice(1));
			case "unprotect": return unprotect(root, args[0]);
			case "verify": return verify(root, args[0]);
			case "budget": return consumeBudget(root, args[0], args[1]);
			case "grant": return grantBudget(root, args[0], args[1], flags.n ? Number(flags.n) : 1, flags["authorized-by"]);
			case "set-depth": return setDepth(root, args[0], args[1], { evidence: flags.evidence });
			case "unlock": return unlock(root, args[0], { stale: flags.stale === true, force: flags.force === true });
			case "event": return appendEvent(root, args[0], args[1], flags.data ? JSON.parse(flags.data) : {});
			case "run-check": return runCheck(root, args[0], args[1], passthrough ?? [], { cwd: flags.cwd, maxBytes: flags["max-bytes"] ? Number(flags["max-bytes"]) : undefined });
			case "assess-worktree": return assessWorktree(root, args[0], { remove: flags.remove === true });
			case "question":
				if (args[0] === "open") return questionOpen(root, args[1], flags.file);
				if (args[0] === "answer") return questionAnswer(root, args[1], args[2] ?? flags.answer);
				if (args[0] === "waive") return questionWaive(root, args[1], args[2], flags["authorized-by"]);
				return fail("USAGE", "question <open|answer|waive> <feature> ...");
			case "challenge":
				if (args[0] === "prepare") return challengePrepare(root, args[1], args[2]);
				if (args[0] === "ingest") return challengeIngest(root, args[1], args[2], flags.response);
				if (args[0] === "dispose") return challengeDispose(root, args[1], args[2], flags.file);
				if (args[0] === "skip") return challengeSkip(root, args[1], args[2], flags.reason);
				return fail("USAGE", "challenge <prepare|ingest|dispose|skip> <feature> <phase> ...");
			case "review":
				if (args[0] === "ingest") return reviewIngest(root, args[1], flags.report);
				return fail("USAGE", "review ingest <feature> --report FILE");
			case "waiver":
				if (args[0] === "authorize") return waiverAuthorize(root, args[1], flags.file);
				return fail("USAGE", "waiver authorize <feature> --file FILE");
			case "run":
				if (args[0] === "begin") return runBegin(root, args[1], args[2]);
				if (args[0] === "publish") return runPublish(root, args[1], args[2], args[3]);
				return fail("USAGE", "run <begin|publish> <feature> <phase> [run-id]");
			default:
				return fail("USAGE", "Usage: tdd-engine.mjs <init|status|transition|freeze|protect|unprotect|verify|budget|grant|set-depth|unlock|event|run-check|assess-worktree|question|challenge|review|waiver|run> ... [--root DIR]");
		}
	};

	try {
		const output = run();
		process.stdout.write(`${JSON.stringify(output, null, 2)}\n`);
		if (command === "verify" && !output.ok) process.exit(2);
	} catch (error) {
		process.stderr.write(`${JSON.stringify({ error: error.message, code: error.code ?? "ENGINE_ERROR" })}\n`);
		process.exit(1);
	}
}

if (process.argv[1] && path.resolve(process.argv[1]) === new URL(import.meta.url).pathname) main();
