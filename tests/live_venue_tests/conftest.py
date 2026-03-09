import os
import json
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = Path(__file__).resolve().parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

load_dotenv(PROJECT_ROOT / ".env")


def get_env(key: str) -> str:
    val = os.environ.get(key)
    if not val or val == "***":
        raise EnvironmentError(f"Missing or placeholder env var: {key}")
    return val


class TestReport:
    def __init__(self, venue: str):
        self.venue = venue
        self.started_at = datetime.utcnow().isoformat()
        self.phases: dict[str, dict] = {}
        self.errors: list[str] = []
        self.data_counts: dict[str, int] = {
            "order_book_deltas": 0,
            "trade_ticks": 0,
            "quote_ticks": 0,
            "bars": 0,
            "custom_data": 0,
        }
        self.order_events: list[str] = []
        self.instruments_loaded: int = 0
        self.sample_instruments: list[str] = []
        self.balance: str = ""

    def phase_ok(self, phase: str, detail: str = ""):
        self.phases[phase] = {"status": "OK", "detail": detail}

    def phase_fail(self, phase: str, error: str):
        self.phases[phase] = {"status": "FAIL", "error": error}
        self.errors.append(f"[{phase}] {error}")

    def save(self):
        report = {
            "venue": self.venue,
            "started_at": self.started_at,
            "finished_at": datetime.utcnow().isoformat(),
            "phases": self.phases,
            "data_counts": self.data_counts,
            "order_events": self.order_events,
            "instruments_loaded": self.instruments_loaded,
            "sample_instruments": self.sample_instruments,
            "balance": self.balance,
            "errors": self.errors,
            "success": len(self.errors) == 0,
        }
        path = LOGS_DIR / f"{self.venue.lower()}_report.json"
        path.write_text(json.dumps(report, indent=2))
        print(f"\n{'='*60}")
        print(f"REPORT: {self.venue}")
        print(f"{'='*60}")
        for phase, info in self.phases.items():
            status = info["status"]
            detail = info.get("detail", info.get("error", ""))
            print(f"  {phase:30s} {status:6s} {detail}")
        print(f"  Data counts: {self.data_counts}")
        print(f"  Order events: {self.order_events}")
        print(f"  Instruments: {self.instruments_loaded}")
        print(f"  Balance: {self.balance}")
        if self.errors:
            print(f"  ERRORS:")
            for e in self.errors:
                print(f"    - {e}")
        print(f"  Overall: {'PASS' if not self.errors else 'FAIL'}")
        print(f"{'='*60}")
        return report
