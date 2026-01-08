#!/usr/bin/env python3
"""Status line: chat/month/total cost + context usage."""
import json
import sys
from datetime import datetime
from pathlib import Path

TRACKING_FILE = Path.home() / ".claude" / "cost-tracking.json"


def load_tracking():
    if TRACKING_FILE.exists():
        try:
            return json.loads(TRACKING_FILE.read_text())
        except json.JSONDecodeError:
            pass
    return {"total": 0.0, "monthly": {}, "last_session": {"id": "", "cost": 0.0}}


def save_tracking(data):
    TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
    TRACKING_FILE.write_text(json.dumps(data))


def main():
    try:
        stdin_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        print("$0/$0/$0 | ctx: ?")
        return

    chat_cost = stdin_data.get("cost", {}).get("total_cost_usd", 0)
    session_id = stdin_data.get("session_id", "")
    month_key = datetime.now().strftime("%Y-%m")

    tracking = load_tracking()
    last = tracking["last_session"]

    if last["id"] and last["id"] != session_id:
        tracking["total"] += last["cost"]
        tracking["monthly"][month_key] = tracking["monthly"].get(month_key, 0) + last["cost"]

    tracking["last_session"] = {"id": session_id, "cost": chat_cost}
    save_tracking(tracking)

    month_cost = tracking["monthly"].get(month_key, 0) + chat_cost
    total_cost = tracking["total"] + chat_cost

    ctx = stdin_data.get("context_window", {})
    current = ctx.get("current_usage", {})
    used = (
        current.get("input_tokens", 0)
        + current.get("cache_creation_input_tokens", 0)
        + current.get("cache_read_input_tokens", 0)
    )
    total_ctx = ctx.get("context_window_size", 200000)
    pct = (used / total_ctx * 100) if total_ctx else 0

    print(f"${chat_cost:.2f}/${month_cost:.2f}/${total_cost:.2f} | {used//1000}k/{total_ctx//1000}k ({pct:.0f}%)")


if __name__ == "__main__":
    main()
