#!/usr/bin/env bash

get_md5() {
    if command -v md5sum &>/dev/null; then
        md5sum | cut -d' ' -f1
    elif command -v md5 &>/dev/null; then
        md5 -q
    else
        echo "error: md5sum or md5 command not found" >&2
        exit 1
    fi
}

wait_idle() {
    local pane_id="$1"
    local idle_time="${2:-2}"
    local check_interval="${3:-0.5}"
    local timeout="${4:-30}"
    local socket="${5:-}"

    local elapsed=0
    local last_hash=""
    local stable_duration=0

    while (( $(echo "$elapsed < $timeout" | bc -l) )); do
        local current_hash
        if tmux_is_inside; then
            current_hash=$(tmux capture-pane -p -t "$pane_id" | get_md5)
        else
            if [[ -z "$socket" ]]; then
                local session
                session=$(state_get_sessions | head -1)
                if [[ -n "$session" ]]; then
                    socket=$(state_get_session_socket "$session")
                fi
            fi
            current_hash=$(tmux_run "$socket" capture-pane -p -t "$pane_id" | get_md5)
        fi

        if [[ "$current_hash" == "$last_hash" ]]; then
            stable_duration=$(echo "$stable_duration + $check_interval" | bc -l)
            if (( $(echo "$stable_duration >= $idle_time" | bc -l) )); then
                return 0
            fi
        else
            stable_duration=0
        fi

        last_hash="$current_hash"
        sleep "$check_interval"
        elapsed=$(echo "$elapsed + $check_interval" | bc -l)
    done

    echo "Error: Timeout waiting for idle" >&2
    return 1
}

wait_for_pattern() {
    local pattern="$1"
    local pane_id="$2"
    local timeout="${3:-30}"
    local check_interval="${4:-0.5}"
    local socket="${5:-}"

    local elapsed=0

    while (( $(echo "$elapsed < $timeout" | bc -l) )); do
        local content
        if tmux_is_inside; then
            content=$(tmux capture-pane -p -t "$pane_id")
        else
            if [[ -z "$socket" ]]; then
                local session
                session=$(state_get_sessions | head -1)
                if [[ -n "$session" ]]; then
                    socket=$(state_get_session_socket "$session")
                fi
            fi
            content=$(tmux_run "$socket" capture-pane -p -t "$pane_id")
        fi

        if echo "$content" | grep -q "$pattern"; then
            return 0
        fi

        sleep "$check_interval"
        elapsed=$(echo "$elapsed + $check_interval" | bc -l)
    done

    echo "Error: Timeout waiting for pattern '$pattern'" >&2
    return 1
}
