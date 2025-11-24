#!/usr/bin/env bash

tmux_is_inside() {
    [[ -n "${TMUX:-}" ]]
}

tmux_get_current_session() {
    tmux display-message -p '#{session_name}' 2>/dev/null || echo ""
}

tmux_get_current_window() {
    tmux display-message -p '#{window_id}' 2>/dev/null || echo ""
}

tmux_get_current_pane() {
    tmux display-message -p '#{pane_id}' 2>/dev/null || echo ""
}

tmux_run() {
    local socket="$1"
    shift

    if [[ -n "$socket" ]]; then
        tmux -S "$socket" "$@"
    else
        tmux "$@"
    fi
}

tmux_ensure_session() {
    local session_name="$1"
    local socket="$2"

    if ! tmux_run "$socket" has-session -t "$session_name" 2>/dev/null; then
        tmux_run "$socket" new-session -d -s "$session_name"
        state_add_session "$session_name" "$socket"
        echo "Created session: $session_name" >&2
    fi
}
