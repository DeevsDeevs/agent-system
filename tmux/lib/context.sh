#!/usr/bin/env bash

CONTEXT_FILE=".claude/tmux/context.json"

context_init() {
  if [[ ! -f "$CONTEXT_FILE" ]]; then
    mkdir -p "$(dirname "$CONTEXT_FILE")"
    echo '{"current_pane": null}' > "$CONTEXT_FILE"
  fi
}

context_get() {
  context_init
  cat "$CONTEXT_FILE"
}

context_get_current_pane() {
  context_init
  jq -r '.current_pane // empty' "$CONTEXT_FILE"
}

context_set_current_pane() {
  local pane_id="$1"
  context_init
  local tmp=$(mktemp)
  jq --arg pane "$pane_id" '.current_pane = $pane' "$CONTEXT_FILE" > "$tmp"
  mv "$tmp" "$CONTEXT_FILE"
}

context_clear() {
  context_init
  echo '{"current_pane": null}' > "$CONTEXT_FILE"
}
