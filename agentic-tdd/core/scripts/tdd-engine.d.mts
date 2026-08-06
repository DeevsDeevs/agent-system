export interface InitOptions {
	depth?: string;
	domains?: string[];
	title?: string;
	protection?: string;
	challenges?: string[];
	testCommand?: string;
	allowDirty?: boolean;
	models?: Record<string, string>;
}

export interface Manifest {
	schema_version: number;
	feature: { id: string; title: string; depth: string; domains: string[] };
	workflow: { state: string };
	repository: {
		baseline_commit: string;
		candidate_tree: string | null;
		candidate_commit: string | null;
		candidate_ref: string | null;
		branch: string;
		test_command: string | null;
		untracked_at_init: string[];
	};
	current: { plan_version: string | null; loop_run: string | null; assessment_run: string | null };
	options: {
		protection_mode: string;
		challenges: { plan: boolean; loop: boolean; assess: boolean };
		models: Record<string, string>;
	};
	integrity: Record<string, unknown>;
	budgets: { used: Record<string, number>; extra: Record<string, number> };
	questions: { open: Record<string, string> };
	challenges: Record<string, { state: string } & Record<string, unknown>>;
	release: { reviewer_status: string; decision: string | null; candidate_tree: string | null; report_hash: string | null };
}

export interface VerifyReport {
	ok: boolean;
	state: string;
	problems: Array<{ code: string; path?: string; phase?: string; expected?: string; actual?: string }>;
	untracked: string[];
	modified: string[];
}

export interface Status {
	feature: Manifest["feature"];
	state: string;
	allowed_next: string[];
	required_next: string;
	repository: Manifest["repository"];
	current: Manifest["current"];
	budgets: Record<string, number>;
	required_check_ids: string[];
	unresolved_blocking: number;
	open_questions: Record<string, string>;
	options: Manifest["options"];
	challenges: Manifest["challenges"];
	release: Manifest["release"];
}

export interface CheckRecord {
	check_id: string;
	seq: number;
	argv: string[];
	cwd: string;
	candidate_tree: string;
	bound_to_candidate: boolean;
	environment: { platform: string; node: string };
	started_at: string;
	duration_ms: number;
	exit_code: number;
	stdout_hash: string;
	stderr_hash: string;
	truncated: boolean;
}

export declare const TRANSITIONS: Record<string, string[]>;
export declare function init(root: string, feature: string, options?: InitOptions): Manifest;
export declare function setDepth(root: string, feature: string, depth: string, options?: { evidence?: string }): { depth: string; previous: string };
export declare function transition(root: string, feature: string, to: string, options?: { resultFile?: string }): { from: string; to: string; state: string; candidate_tree: string | null };
export declare function freeze(root: string, feature: string, phase: string, files: string[]): { commit: string; files: Record<string, string> };
export declare function protect(root: string, feature: string, files: string[]): Array<{ path: string; hash: string; method: string }>;
export declare function unprotect(root: string, feature: string): { released: number };
export declare function verify(root: string, feature: string): VerifyReport;
export declare function consumeBudget(root: string, feature: string, counter: string): { counter: string; remaining: number };
export declare function grantBudget(root: string, feature: string, counter: string, n: number, authorizedBy: string): { counter: string; remaining: number; authorized_by: string };
export declare function questionOpen(root: string, feature: string, questionFile: string): { id: string; class: string; unresolved_blocking: number };
export declare function questionAnswer(root: string, feature: string, id: string, answer: string): { id: string; unresolved_blocking: number };
export declare function questionWaive(root: string, feature: string, id: string, authorizedBy: string): { id: string; unresolved_blocking: number };
export declare function challengePrepare(root: string, feature: string, phase: string): { phase: string; state: string; packet_dir: string };
export declare function challengeIngest(root: string, feature: string, phase: string, responseFile: string): { phase: string; state: string; findings: number };
export declare function challengeDispose(root: string, feature: string, phase: string, dispositionFile: string): { phase: string; state: string };
export declare function challengeSkip(root: string, feature: string, phase: string, reason: string): { phase: string; state: string };
export declare function reviewIngest(root: string, feature: string, reportFile: string): { decision: string };
export declare function waiverAuthorize(root: string, feature: string, waiverFile: string): { id: string; expires: string };
export declare function runCheck(root: string, feature: string, checkId: string, argv: string[], options?: { cwd?: string; maxBytes?: number }): CheckRecord;
export declare function assessWorktree(root: string, feature: string, options?: { remove?: boolean }): Record<string, unknown>;
export declare function runBegin(root: string, feature: string, phase: string): { phase: string; run_id: string; dir: string };
export declare function runPublish(root: string, feature: string, phase: string, runId: string): { phase: string; run_id: string; dir: string };
export declare function unlock(root: string, feature: string, options?: { stale?: boolean; force?: boolean }): { released: boolean; reason: string };
export declare function status(root: string, feature: string): Status;
export declare function appendEvent(root: string, feature: string, type: string, data?: Record<string, unknown>): Record<string, unknown>;
