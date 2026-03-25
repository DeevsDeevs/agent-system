#!/usr/bin/env bash
set -euo pipefail

# Chain Link Verification Script
# Spawns an isolated CLI process to benchmark a chain link's self-sufficiency.
# The verifier gets ONLY the chain link content and questions — zero shared context.

CHAIN_LINK_FILE="${1:?Usage: chain-verify.sh <chain-link-file> <questions-file>}"
QUESTIONS_FILE="${2:?Usage: chain-verify.sh <chain-link-file> <questions-file>}"

if [[ ! -f "$CHAIN_LINK_FILE" ]]; then
  echo "ERROR: Chain link file not found: $CHAIN_LINK_FILE" >&2
  exit 1
fi

if [[ ! -f "$QUESTIONS_FILE" ]]; then
  echo "ERROR: Questions file not found: $QUESTIONS_FILE" >&2
  exit 1
fi

CHAIN_CONTENT="$(cat "$CHAIN_LINK_FILE")"
QUESTIONS="$(cat "$QUESTIONS_FILE")"

SYSTEM_PROMPT="You are a developer resuming work from a chain link. You have NO other context besides what is provided in this prompt. You must answer each question using ONLY the chain link content given. If you cannot answer a question or the answer is incomplete/ambiguous, say INSUFFICIENT and explain what is missing."

USER_PROMPT="$(cat <<EOF
## Chain Link Content

${CHAIN_CONTENT}

## Verification Questions

${QUESTIONS}

## Instructions

Answer each question using ONLY the chain link content above. For each question respond with:

### Q[N]: [question text]
**Answer**: [your answer based solely on the chain link]
**Score**: [0-100, where 90-100 = fully answerable, 70-89 = missing some detail, 50-69 = significant gaps, 0-49 = cannot answer]
**Gap**: [what specific information is missing, if anything]

After all questions, provide:

### Aggregate
**Total Score**: [average of all 10 scores, as integer]
**Weakest Sections**: [which chain link sections (1-9) had lowest coverage]
**Critical Gaps**: [specific missing information that would block a resuming developer]
EOF
)"

# Detect available CLI
if command -v claude &>/dev/null; then
  # --print: non-interactive, output and exit
  # --system-prompt: override default system prompt for isolation
  # --no-session-persistence: don't save this throwaway session
  # --model haiku: fast and cheap for verification scoring
  #
  # NOTE: We do NOT use --bare because it disables OAuth/keychain auth.
  # Isolation is achieved by: separate process (no conversation context),
  # custom system prompt (overrides default behavior), and --no-session-persistence.
  # CLAUDE.md may load but it cannot provide conversation context from the parent session.
  echo "$USER_PROMPT" | claude --print \
    --system-prompt "$SYSTEM_PROMPT" \
    --no-session-persistence \
    --model haiku \
    --allowedTools ""
elif command -v codex &>/dev/null; then
  codex --quiet \
    --approval-mode full-auto \
    "$SYSTEM_PROMPT

$USER_PROMPT"
else
  echo "ERROR: Neither 'claude' nor 'codex' CLI found. Install one to run verification." >&2
  exit 1
fi
