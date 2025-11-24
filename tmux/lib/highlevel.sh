#!/usr/bin/env bash

# Source dependencies
source "$(dirname "${BASH_SOURCE[0]}")/pane.sh"
source "$(dirname "${BASH_SOURCE[0]}")/wait.sh"
source "$(dirname "${BASH_SOURCE[0]}")/context.sh"
source "$(dirname "${BASH_SOURCE[0]}")/state.sh"

# Named panes tracking
NAMED_PANES_FILE=".claude/tmux/named_panes.json"

named_init() {
  if [[ ! -f "$NAMED_PANES_FILE" ]]; then
    mkdir -p "$(dirname "$NAMED_PANES_FILE")"
    echo '{}' > "$NAMED_PANES_FILE"
  fi
}

named_add() {
  local name="$1"
  local pane_id="$2"
  local command="$3"

  named_init
  local tmp=$(mktemp)
  jq --arg name "$name" --arg pane "$pane_id" --arg cmd "$command" \
    '.[$name] = {pane: $pane, command: $cmd, started_at: now | todate}' \
    "$NAMED_PANES_FILE" > "$tmp"
  mv "$tmp" "$NAMED_PANES_FILE"
}

named_get() {
  local name="$1"
  named_init
  jq -r --arg name "$name" '.[$name].pane // empty' "$NAMED_PANES_FILE"
}

named_remove() {
  local name="$1"
  named_init
  local tmp=$(mktemp)
  jq --arg name "$name" 'del(.[$name])' "$NAMED_PANES_FILE" > "$tmp"
  mv "$tmp" "$NAMED_PANES_FILE"
}

named_list() {
  named_init
  jq -r 'to_entries | .[] | "\(.key)\t\(.value.pane)\t\(.value.command)"' "$NAMED_PANES_FILE"
}

# High-level eval - run and return output
cmd_eval() {
  local command="$1"

  # Launch shell
  local pane_id=$(pane_launch "zsh")

  # Execute command
  pane_send "$command" "$pane_id"
  wait_idle "$pane_id" 2 0.5 60

  # Capture output
  local output=$(pane_capture "$pane_id")

  # Kill pane
  pane_kill "$pane_id"

  # Return output (skip the command echo)
  echo "$output" | tail -n +2
}

# Start named long-running process
cmd_start() {
  local command="$1"
  local name="$2"
  local wait_pattern="$3"
  local timeout="${4:-30}"

  # Launch shell
  local pane_id=$(pane_launch "zsh")

  # Add to named tracking
  if [[ -n "$name" ]]; then
    named_add "$name" "$pane_id" "$command"
  fi

  # Execute command
  pane_send "$command" "$pane_id"

  # Wait for pattern if specified
  if [[ -n "$wait_pattern" ]]; then
    wait_for_pattern "$wait_pattern" "$pane_id" "$timeout"
  else
    sleep 0.5
  fi

  echo "$pane_id"
}

# Stop named process(es)
cmd_stop() {
  local names=("$@")

  for name in "${names[@]}"; do
    local pane_id=$(named_get "$name")
    if [[ -z "$pane_id" ]]; then
      echo "Warning: No process named '$name'" >&2
      continue
    fi

    # Try interrupt first
    pane_interrupt "$pane_id" 2>/dev/null
    sleep 0.5

    # Then kill
    pane_kill "$pane_id" 2>/dev/null
    named_remove "$name"
  done
}

# List running processes
cmd_ps() {
  echo -e "NAME\tPANE\tCOMMAND"
  named_list
}

# Get logs from named process
cmd_logs() {
  local name="$1"
  local tail_lines="${2:-}"

  local pane_id=$(named_get "$name")
  if [[ -z "$pane_id" ]]; then
    echo "Error: No process named '$name'" >&2
    return 1
  fi

  local output=$(pane_capture "$pane_id")

  if [[ -n "$tail_lines" ]]; then
    echo "$output" | tail -n "$tail_lines"
  else
    echo "$output"
  fi
}

# Wait for named processes to finish
cmd_wait() {
  local names=("$@")
  local timeout="${WAIT_TIMEOUT:-300}"

  for name in "${names[@]}"; do
    local pane_id=$(named_get "$name")
    if [[ -z "$pane_id" ]]; then
      echo "Warning: No process named '$name'" >&2
      continue
    fi

    wait_idle "$pane_id" 2 0.5 "$timeout"
  done
}

# Use/switch to named process
cmd_use() {
  local name="$1"

  local pane_id=$(named_get "$name")
  if [[ -z "$pane_id" ]]; then
    echo "Error: No process named '$name'" >&2
    return 1
  fi

  context_set_current_pane "$pane_id"
  echo "Switched to '$name' ($pane_id)"
}
