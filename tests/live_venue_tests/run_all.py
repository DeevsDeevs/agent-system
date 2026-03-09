"""Run all venue tests in parallel (each is its own process). Captures logs via file redirect."""
import subprocess
import sys
import json
import tempfile
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

TESTS = [
    ("Binance Futures", "test_binance_futures.py"),
    ("Binance Spot", "test_binance_spot.py"),
    ("Bybit Linear", "test_bybit_linear.py"),
    ("OKX Swap", "test_okx_swap.py"),
    ("dYdX v4", "test_dydx_v4.py"),
]

VENV_PYTHON = Path(__file__).resolve().parent.parent.parent / ".venv" / "bin" / "python"
TEST_DIR = Path(__file__).resolve().parent
LOGS_DIR = TEST_DIR / "logs"
TIMEOUT = 90


def run_test(args: tuple[str, str]) -> dict:
    name, script = args
    script_path = TEST_DIR / script
    log_out = LOGS_DIR / f"{script.replace('.py', '')}_stdout.log"
    log_err = LOGS_DIR / f"{script.replace('.py', '')}_stderr.log"

    with open(log_out, "w") as fout, open(log_err, "w") as ferr:
        try:
            proc = subprocess.Popen(
                [str(VENV_PYTHON), "-u", str(script_path)],
                cwd=str(TEST_DIR),
                stdout=fout,
                stderr=ferr,
            )
            proc.wait(timeout=TIMEOUT)
            return {"name": name, "returncode": proc.returncode,
                    "status": "COMPLETED" if proc.returncode == 0 else "ERROR"}
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            return {"name": name, "returncode": -1, "status": "TIMEOUT"}
        except Exception as e:
            return {"name": name, "returncode": -1, "status": f"EXCEPTION: {e}"}


def main():
    filter_arg = sys.argv[1] if len(sys.argv) > 1 else None
    tests_to_run = [(n, s) for n, s in TESTS if not filter_arg or filter_arg.lower() in n.lower()]

    print(f"Running {len(tests_to_run)} tests in parallel (timeout={TIMEOUT}s)...\n")
    results = []
    with ProcessPoolExecutor(max_workers=len(tests_to_run)) as pool:
        futures = {pool.submit(run_test, t): t[0] for t in tests_to_run}
        for future in as_completed(futures):
            r = future.result()
            results.append(r)
            print(f"  {r['name']:25s} {r['status']}")

    print(f"\n{'='*60}")
    print("DETAILED REPORTS")
    print(f"{'='*60}")

    for rf in sorted(LOGS_DIR.glob("*_report.json")):
        data = json.loads(rf.read_text())
        venue = data.get("venue", rf.stem)
        success = data.get("success", False)
        print(f"\n  {venue}: {'PASS' if success else 'FAIL'}")
        for phase, info in data.get("phases", {}).items():
            s = info["status"]
            d = info.get("detail", info.get("error", ""))
            print(f"    {phase:25s} {s:6s} {d}")
        print(f"    data: {data.get('data_counts', {})}")
        bal = data.get("balance", "N/A")
        if bal:
            print(f"    balance: {bal[:80]}{'...' if len(bal) > 80 else ''}")
        for e in data.get("errors", []):
            print(f"    ERROR: {e}")

    # Show key errors from stderr logs for timed-out tests
    print(f"\n{'='*60}")
    print("KEY ERRORS FROM LOGS")
    print(f"{'='*60}")
    for f in sorted(LOGS_DIR.glob("*_stdout.log")):
        content = f.read_text()
        import re
        clean = re.sub(r'\x1b\[[0-9;]*m', '', content)
        errors = [l.strip() for l in clean.splitlines() if 'ERROR' in l or 'STRATEGY' in l]
        if errors:
            print(f"\n  {f.stem}:")
            for e in errors[:5]:
                print(f"    {e[:120]}")

    print(f"\n{'='*60}")


if __name__ == "__main__":
    main()
