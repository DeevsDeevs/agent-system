#!/usr/bin/env bash
set -euo pipefail

TRACKING_FILE="$HOME/.claude/cost-tracking.json"
STALE_THRESHOLD=3600

read_stdin() {
    cat
}

load_tracking() {
    if [[ -f "$TRACKING_FILE" ]]; then
        cat "$TRACKING_FILE" 2>/dev/null || echo '{}'
    else
        echo '{}'
    fi
}

save_tracking() {
    local data="$1"
    mkdir -p "$(dirname "$TRACKING_FILE")"
    echo "$data" > "$TRACKING_FILE"
}

main() {
    local stdin_data
    stdin_data=$(read_stdin)

    if ! echo "$stdin_data" | jq -e . >/dev/null 2>&1; then
        echo '$0/$0/$0 | ctx: ?'
        return
    fi

    local chat_cost session_id month_key now
    chat_cost=$(echo "$stdin_data" | jq -r '.cost.total_cost_usd // 0')
    session_id=$(echo "$stdin_data" | jq -r '.session_id // ""')
    month_key=$(date '+%Y-%m')
    now=$(date '+%s')

    local tracking
    tracking=$(load_tracking)

    if ! echo "$tracking" | jq -e '.sessions' >/dev/null 2>&1; then
        local old_total old_monthly
        old_total=$(echo "$tracking" | jq -r '.total // 0')
        old_monthly=$(echo "$tracking" | jq -r ".monthly[\"$month_key\"] // 0")
        tracking=$(jq -n \
            --argjson total "$old_total" \
            --argjson monthly "$old_monthly" \
            --arg month_key "$month_key" \
            '{total: $total, monthly: {($month_key): $monthly}, sessions: {}}')
    fi

    tracking=$(echo "$tracking" | jq \
        --arg sid "$session_id" \
        --argjson cost "$chat_cost" \
        --argjson now "$now" \
        '.sessions[$sid] = {cost: $cost, last_seen: $now}')

    local stale_cost
    stale_cost=$(echo "$tracking" | jq -r \
        --argjson threshold "$STALE_THRESHOLD" \
        --argjson now "$now" \
        '[.sessions | to_entries[] | select(($now - .value.last_seen) > $threshold) | .value.cost] | add // 0')

    if [[ "$stale_cost" != "0" ]] && [[ "$stale_cost" != "null" ]]; then
        tracking=$(echo "$tracking" | jq \
            --argjson stale_cost "$stale_cost" \
            --arg month_key "$month_key" \
            --argjson threshold "$STALE_THRESHOLD" \
            --argjson now "$now" \
            '.total += $stale_cost |
             .monthly[$month_key] = ((.monthly[$month_key] // 0) + $stale_cost) |
             .sessions |= with_entries(select(($now - .value.last_seen) <= $threshold))')
    fi

    save_tracking "$tracking"

    local active_sum monthly_base total_base
    active_sum=$(echo "$tracking" | jq '[.sessions[].cost] | add // 0')
    monthly_base=$(echo "$tracking" | jq -r ".monthly[\"$month_key\"] // 0")
    total_base=$(echo "$tracking" | jq -r '.total // 0')

    local month_cost total_cost
    month_cost=$(awk "BEGIN {printf \"%.2f\", $monthly_base + $active_sum}")
    total_cost=$(awk "BEGIN {printf \"%.2f\", $total_base + $active_sum}")

    local ctx_current used total_ctx pct
    ctx_current=$(echo "$stdin_data" | jq '.context_window.current_usage // {}')
    used=$(echo "$ctx_current" | jq '(.input_tokens // 0) + (.cache_creation_input_tokens // 0) + (.cache_read_input_tokens // 0)')
    total_ctx=$(echo "$stdin_data" | jq '.context_window.context_window_size // 200000')
    pct=$(awk "BEGIN {printf \"%.0f\", ($used / $total_ctx) * 100}")

    local used_k total_k
    used_k=$((used / 1000))
    total_k=$((total_ctx / 1000))

    printf '$%.2f/$%s/$%s | %dk/%dk (%s%%)\n' "$chat_cost" "$month_cost" "$total_cost" "$used_k" "$total_k" "$pct"
}

main
