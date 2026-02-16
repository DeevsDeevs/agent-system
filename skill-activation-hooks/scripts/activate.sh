#!/usr/bin/env bash
set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="$PLUGIN_ROOT/config/skills.json"

if ! command -v jq &>/dev/null; then
  exit 0
fi

if [ ! -f "$CONFIG" ]; then
  exit 0
fi

input=$(cat)
prompt=$(echo "$input" | jq -r '.prompt // empty')

if [ -z "$prompt" ]; then
  exit 0
fi

prompt_lower=$(echo "$prompt" | tr '[:upper:]' '[:lower:]')

# Single jq call: flatten all rules into TSV grouped by skill.
# Entry types prefixed for ordering: 0meta before 1kw before 2ip.
# jq iterates keys in insertion order, so entries for each skill are contiguous.
rules=$(jq -r '
  .skills | to_entries[] |
  .key as $sk | .value as $v |
  ([$sk, "0meta", ($v.threshold // 3 | tostring), $v.message] | @tsv),
  (($v.keywords // [])[] | [$sk, "1kw", .term, (.w // 1 | tostring)] | @tsv),
  (($v.intentPatterns // [])[] | [$sk, "2ip", ., ($v.intentWeight // 3 | tostring)] | @tsv)
' "$CONFIG")

current_skill=""
score=0
threshold=0
message=""
matched=""

emit_if_matched() {
  if [ -n "$current_skill" ] && [ "$score" -ge "$threshold" ]; then
    matched="${matched}${message}\n"
  fi
}

while IFS=$'\t' read -r skill typ val extra; do
  [ -z "$skill" ] && continue

  if [ "$skill" != "$current_skill" ]; then
    emit_if_matched
    current_skill="$skill"
    score=0
    threshold=0
    message=""
  fi

  case "$typ" in
    0meta)
      threshold="$val"
      message="$extra"
      ;;
    1kw)
      if echo "$prompt_lower" | grep -qiF -- "$val"; then
        score=$((score + extra))
      fi
      ;;
    2ip)
      if echo "$prompt_lower" | grep -qiE -- "$val" 2>/dev/null; then
        score=$((score + extra))
      fi
      ;;
  esac
done <<< "$rules"
emit_if_matched

if [ -z "$matched" ]; then
  exit 0
fi

# additionalContext injects into Claude's conversation context.
# Plain stdout also works but is more visible in the transcript.
context=$(printf '%b' "$matched" | sed '/^$/d')
json_context=$(echo "$context" | jq -Rs '.')

cat <<EOF
{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":${json_context}}}
EOF
