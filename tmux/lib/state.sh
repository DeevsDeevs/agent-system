#!/usr/bin/env bash

STATE_DIR=".claude/tmux"
STATE_FILE="${STATE_DIR}/sessions.json"
SOCKET_DIR="${STATE_DIR}/sockets"

state_init() {
    mkdir -p "$STATE_DIR" "$SOCKET_DIR"

    if [[ ! -f "$STATE_FILE" ]]; then
        cat > "$STATE_FILE" << 'EOF'
{
  "project_path": "",
  "sessions": []
}
EOF
        local project_path
        project_path=$(pwd)
        state_set_project_path "$project_path"
    fi
}

state_set_project_path() {
    local path="$1"
    local tmp
    tmp=$(mktemp)
    jq --arg path "$path" '.project_path = $path' "$STATE_FILE" > "$tmp"
    mv "$tmp" "$STATE_FILE"
}

state_read() {
    if [[ ! -f "$STATE_FILE" ]]; then
        echo "{}"
        return
    fi
    cat "$STATE_FILE"
}

state_write() {
    local json="$1"
    echo "$json" > "$STATE_FILE"
}

state_add_session() {
    local name="$1"
    local socket="$2"
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    local tmp
    tmp=$(mktemp)
    jq --arg name "$name" \
       --arg socket "$socket" \
       --arg created "$timestamp" \
       --arg active "$timestamp" \
       '.sessions += [{
           "name": $name,
           "socket": $socket,
           "created_at": $created,
           "last_active": $active,
           "status": "active",
           "windows": []
       }]' "$STATE_FILE" > "$tmp"
    mv "$tmp" "$STATE_FILE"
}

state_remove_session() {
    local name="$1"
    local tmp
    tmp=$(mktemp)
    jq --arg name "$name" '.sessions = [.sessions[] | select(.name != $name)]' "$STATE_FILE" > "$tmp"
    mv "$tmp" "$STATE_FILE"
}

state_add_pane() {
    local session="$1"
    local window="$2"
    local pane_id="$3"
    local pane_index="$4"
    local command="$5"
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    local tmp
    tmp=$(mktemp)

    jq --arg session "$session" \
       --arg window "$window" \
       --arg pane_id "$pane_id" \
       --argjson pane_index "$pane_index" \
       --arg command "$command" \
       --arg created "$timestamp" \
       '.sessions = [.sessions[] |
         if .name == $session then
           .windows = (
             if (.windows | any(.id == $window)) then
               [.windows[] |
                 if .id == $window then
                   .panes += [{
                     "id": $pane_id,
                     "index": $pane_index,
                     "command": $command,
                     "created_at": $created,
                     "active": false
                   }]
                 else . end
               ]
             else
               .windows + [{
                 "id": $window,
                 "name": "main",
                 "panes": [{
                   "id": $pane_id,
                   "index": $pane_index,
                   "command": $command,
                   "created_at": $created,
                   "active": false
                 }]
               }]
             end
           )
         else . end
       ]' "$STATE_FILE" > "$tmp"
    mv "$tmp" "$STATE_FILE"
}

state_remove_pane() {
    local pane_id="$1"
    local tmp
    tmp=$(mktemp)

    jq --arg pane_id "$pane_id" \
       '.sessions = [.sessions[] |
         .windows = [.windows[] |
           .panes = [.panes[] | select(.id != $pane_id)]
         ]
       ]' "$STATE_FILE" > "$tmp"
    mv "$tmp" "$STATE_FILE"
}

state_get_sessions() {
    jq -r '.sessions[] | .name' "$STATE_FILE" 2>/dev/null || true
}

state_get_session_socket() {
    local name="$1"
    jq -r --arg name "$name" '.sessions[] | select(.name == $name) | .socket' "$STATE_FILE" 2>/dev/null || true
}

state_ensure_session() {
    local name="$1"
    local socket="${2:-}"

    local exists
    exists=$(jq --arg name "$name" '.sessions[] | select(.name == $name) | .name' "$STATE_FILE" 2>/dev/null || true)

    if [[ -z "$exists" ]]; then
        state_add_session "$name" "$socket"
    fi
}
