#!/usr/bin/env bash
set -euo pipefail

# Hook: PostToolUse (Write|Edit)
# Fires automatically after any file write. Checks if the written file is a
# chain link (.claude/chains/**/*.md) and runs isolated verification if so.
#
# Exit codes:
#   0 = pass (or not a chain file — skip silently)
#   2 = fail (blocks the write, feeds gaps back to the agent)

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.filePath // empty')

# Only trigger on chain link files
if [[ ! "$FILE_PATH" =~ \.claude/chains/.*\.md$ ]]; then
  exit 0
fi

if [[ ! -f "$FILE_PATH" ]]; then
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERIFY_SCRIPT="$SCRIPT_DIR/../scripts/chain-verify.sh"

if [[ ! -x "$VERIFY_SCRIPT" ]]; then
  echo "WARNING: chain-verify.sh not found or not executable at $VERIFY_SCRIPT" >&2
  exit 0
fi

# Generate verification questions from the chain link content
# Write them to a temp file for the verification script
QUESTIONS_FILE="$(mktemp /tmp/chain-verify-questions-XXXXXX.md)"
CHAIN_CONTENT="$(cat "$FILE_PATH")"

# Use a simple, deterministic question set derived from the 9 required sections.
# These probe whether each section is present and substantive.
cat > "$QUESTIONS_FILE" << 'EOF'
1. What is the user's primary request? Describe the exact goal, not a vague summary.
2. What specific technologies, frameworks, or patterns are involved, and why were they chosen?
3. What work has been completed so far? List concrete deliverables with their current status.
4. What key decisions were made during this work? For each, what was the alternative and why was it rejected?
5. What files were created or modified? For created files, is the full code included? For modified files, are the before/after changes and line numbers present?
6. Are there any unresolved issues or blockers? If so, what solutions were attempted and why did they fail?
7. What tasks remain to be done? Are they specific enough to act on without guessing?
8. What was actively in progress when this chain link was saved? Include file names, line numbers, and code context.
9. What is the exact next step? Is it a single, unambiguous action that a new session can execute immediately?
10. Could you resume this work right now with ONLY the information in this chain link, without asking any clarifying questions? If not, what would you need to ask?
EOF

echo "Verifying chain link: $(basename "$FILE_PATH")" >&2

# Run verification in isolated process
VERIFY_OUTPUT=$("$VERIFY_SCRIPT" "$FILE_PATH" "$QUESTIONS_FILE" 2>/dev/null) || true
rm -f "$QUESTIONS_FILE"

if [[ -z "$VERIFY_OUTPUT" ]]; then
  echo "WARNING: Verification produced no output (CLI may not be available). Chain link saved without benchmark." >&2
  exit 0
fi

# Extract the aggregate score from the verification output
# Look for "Total Score": followed by a number
SCORE=$(echo "$VERIFY_OUTPUT" | grep -oP 'Total Score\D*\K[0-9]+' | head -1 || echo "")

if [[ -z "$SCORE" ]]; then
  # Could not parse score — let it through with the raw output
  echo "Chain link saved. Verification output (could not parse score):"
  echo "$VERIFY_OUTPUT"
  exit 0
fi

if [[ "$SCORE" -ge 85 ]]; then
  echo "Chain link verified. Benchmark: ${SCORE}/100"
  echo ""
  echo "$VERIFY_OUTPUT"
  exit 0
else
  # Fail — block the write, feed gaps back to the agent
  cat >&2 << FEEDBACK
CHAIN LINK VERIFICATION FAILED — Benchmark: ${SCORE}/100 (threshold: 85)

The chain link is not self-sufficient. A fresh session would not be able to resume
from this chain link alone. Review the gaps below and rewrite the chain link with
the missing information, then save it again to re-trigger verification.

--- Verification Output ---
${VERIFY_OUTPUT}
--- End Verification Output ---

ACTION REQUIRED: Rewrite the chain link addressing the gaps above, then save again.
FEEDBACK
  exit 2
fi
