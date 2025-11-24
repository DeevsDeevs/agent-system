#!/usr/bin/env bash

# Source dependencies
source "$(dirname "${BASH_SOURCE[0]}")/pane.sh"
source "$(dirname "${BASH_SOURCE[0]}")/wait.sh"
source "$(dirname "${BASH_SOURCE[0]}")/context.sh"

# REPL configuration - returns launch_cmd|prompt|exit_cmd
repl_get_config() {
  local repl_type="$1"

  case "$repl_type" in
    python|python3)
      echo "PYTHON_BASIC_REPL=1 python3|>>>|exit()"
      ;;
    node|nodejs)
      echo "node|>|.exit"
      ;;
    psql)
      echo "psql|=#|\\q"
      ;;
    *)
      return 1
      ;;
  esac
}

# One-shot REPL execution
repl_oneshot() {
  local repl_type="$1"
  local command="$2"

  local config=$(repl_get_config "$repl_type")
  if [[ -z "$config" ]]; then
    echo "Error: Unknown REPL type: $repl_type" >&2
    return 1
  fi

  IFS='|' read -r launch_cmd prompt exit_cmd <<< "$config"

  # Launch shell first for safety
  local pane_id=$(pane_launch "zsh")

  # Start REPL
  pane_send "$launch_cmd" "$pane_id"
  wait_for_pattern "$prompt" "$pane_id" 10

  # Execute command
  pane_send "$command" "$pane_id"
  wait_idle "$pane_id" 1 0.5 30

  # Capture output
  local output=$(pane_capture "$pane_id")

  # Exit REPL
  pane_send "$exit_cmd" "$pane_id"
  sleep 0.2

  # Kill pane
  pane_kill "$pane_id"

  # Parse and clean output (remove echo and prompts)
  echo "$output" | grep -v "^$prompt" | grep -v "^$command$" | grep -v "^$exit_cmd$" | tail -n +2
}

# Start persistent REPL session
repl_start() {
  local repl_type="$1"
  shift
  local extra_args="$@"

  local config=$(repl_get_config "$repl_type")
  if [[ -z "$config" ]]; then
    echo "Error: Unknown REPL type: $repl_type" >&2
    return 1
  fi

  IFS='|' read -r launch_cmd prompt exit_cmd <<< "$config"

  # Add extra args (e.g., database name for psql)
  if [[ -n "$extra_args" ]]; then
    launch_cmd="$launch_cmd $extra_args"
  fi

  # Launch shell first
  local pane_id=$(pane_launch "zsh")

  # Start REPL
  pane_send "$launch_cmd" "$pane_id"
  wait_for_pattern "$prompt" "$pane_id" 10

  # Set as current context
  context_set_current_pane "$pane_id"

  echo "$pane_id"
}

# Execute in current REPL context
repl_exec() {
  local command="$1"
  local pane_id="${2:-$(context_get_current_pane)}"

  if [[ -z "$pane_id" ]]; then
    echo "Error: No active REPL session. Use 'tmux-ctl repl <type>' first" >&2
    return 1
  fi

  pane_send "$command" "$pane_id"
  wait_idle "$pane_id" 1 0.5 30
  pane_capture "$pane_id" | tail -n +2
}

# Close current REPL
repl_close() {
  local pane_id="${1:-$(context_get_current_pane)}"

  if [[ -z "$pane_id" ]]; then
    echo "Error: No active REPL session" >&2
    return 1
  fi

  pane_kill "$pane_id"
  context_clear
}
