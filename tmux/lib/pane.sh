#!/usr/bin/env bash

pane_launch() {
    local command="$1"
    local socket="${2:-}"

    state_init

    local session window pane_id pane_index

    if tmux_is_inside; then
        session=$(tmux_get_current_session)
        window=$(tmux_get_current_window)
        local socket_path
        socket_path=$(tmux display-message -p '#{socket_path}')

        state_ensure_session "$session" "$socket_path"

        pane_id=$(tmux split-window -d -P -F '#{pane_id}' "$command")
        pane_index=$(tmux display-message -p -t "$pane_id" '#{pane_index}')
    else
        session=$(state_get_sessions | head -1)
        if [[ -z "$session" ]]; then
            session="claude-main"
            socket="${SOCKET_DIR}/${session}"
            tmux_ensure_session "$session" "$socket"
        else
            socket=$(state_get_session_socket "$session")
        fi

        pane_id=$(tmux_run "$socket" split-window -t "$session" -d -P -F '#{pane_id}' "$command")
        pane_index=$(tmux_run "$socket" display-message -p -t "$pane_id" '#{pane_index}')
        window=$(tmux_run "$socket" display-message -p -t "$pane_id" '#{window_id}')
    fi

    state_add_pane "$session" "$window" "$pane_id" "$pane_index" "$command"
    echo "$pane_id"
}

pane_capture() {
    local pane_id="$1"
    local socket="${2:-}"

    if tmux_is_inside; then
        tmux capture-pane -p -t "$pane_id"
    else
        if [[ -z "$socket" ]]; then
            local session
            session=$(state_get_sessions | head -1)
            if [[ -n "$session" ]]; then
                socket=$(state_get_session_socket "$session")
            fi
        fi
        tmux_run "$socket" capture-pane -p -t "$pane_id"
    fi
}

pane_list() {
    local socket="${1:-}"

    if tmux_is_inside; then
        tmux list-panes -F '{"id":"#{pane_id}","index":#{pane_index},"active":#{pane_active},"command":"#{pane_current_command}","width":#{pane_width},"height":#{pane_height}}' | jq -s .
    else
        if [[ -z "$socket" ]]; then
            local session
            session=$(state_get_sessions | head -1)
            if [[ -n "$session" ]]; then
                socket=$(state_get_session_socket "$session")
            fi
        fi
        if [[ -n "$socket" ]]; then
            local session
            session=$(state_get_sessions | head -1)
            tmux_run "$socket" list-panes -t "$session" -F '{"id":"#{pane_id}","index":#{pane_index},"active":#{pane_active},"command":"#{pane_current_command}","width":#{pane_width},"height":#{pane_height}}' | jq -s .
        else
            echo "[]"
        fi
    fi
}

pane_send() {
    local text="$1"
    local pane_id="$2"
    local enter="${3:-true}"
    local socket="${4:-}"

    if tmux_is_inside; then
        tmux send-keys -t "$pane_id" -l "$text"
        if [[ "$enter" == "true" ]]; then
            tmux send-keys -t "$pane_id" Enter
        fi
    else
        if [[ -z "$socket" ]]; then
            local session
            session=$(state_get_sessions | head -1)
            if [[ -n "$session" ]]; then
                socket=$(state_get_session_socket "$session")
            fi
        fi
        tmux_run "$socket" send-keys -t "$pane_id" -l "$text"
        if [[ "$enter" == "true" ]]; then
            tmux_run "$socket" send-keys -t "$pane_id" Enter
        fi
    fi
}

pane_kill() {
    local pane_id="$1"
    local socket="${2:-}"

    local current_pane
    current_pane=$(tmux_get_current_pane)

    if [[ "$pane_id" == "$current_pane" ]]; then
        echo "Error: Cannot kill current pane" >&2
        exit 1
    fi

    if tmux_is_inside; then
        tmux kill-pane -t "$pane_id"
    else
        if [[ -z "$socket" ]]; then
            local session
            session=$(state_get_sessions | head -1)
            if [[ -n "$session" ]]; then
                socket=$(state_get_session_socket "$session")
            fi
        fi
        tmux_run "$socket" kill-pane -t "$pane_id"
    fi

    state_remove_pane "$pane_id"
}

pane_interrupt() {
    local pane_id="$1"
    local socket="${2:-}"

    if tmux_is_inside; then
        tmux send-keys -t "$pane_id" C-c
    else
        if [[ -z "$socket" ]]; then
            local session
            session=$(state_get_sessions | head -1)
            if [[ -n "$session" ]]; then
                socket=$(state_get_session_socket "$session")
            fi
        fi
        tmux_run "$socket" send-keys -t "$pane_id" C-c
    fi
}

pane_escape() {
    local pane_id="$1"
    local socket="${2:-}"

    if tmux_is_inside; then
        tmux send-keys -t "$pane_id" Escape
    else
        if [[ -z "$socket" ]]; then
            local session
            session=$(state_get_sessions | head -1)
            if [[ -n "$session" ]]; then
                socket=$(state_get_session_socket "$session")
            fi
        fi
        tmux_run "$socket" send-keys -t "$pane_id" Escape
    fi
}
