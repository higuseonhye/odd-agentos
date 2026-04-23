"""
dashboard.py — Terminal live dashboard for odd-agentos
--------------------------------------------------------
Prometheus 없이도 터미널에서 실시간 metrics를 볼 수 있는 경량 대시보드.

Usage:
    # 별도 터미널에서:
    python dashboard.py

    # 또는 앱 안에서 백그라운드로:
    from dashboard import start_dashboard_thread
    start_dashboard_thread(interval_seconds=5)
"""

import os
import sys
import time
import threading
from datetime import datetime


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def render(stats: dict):
    now = datetime.now().strftime("%H:%M:%S")
    total = stats.get("llm_calls_total", 0)
    errors = stats.get("llm_errors_total", 0)
    decisions = stats.get("decisions_total", 0)
    low_conf = stats.get("low_confidence_total", 0)
    active = stats.get("active_runs", 0)
    p50 = stats.get("p50_ms", 0)
    p95 = stats.get("p95_ms", 0)
    p99 = stats.get("p99_ms", 0)

    error_rate = (errors / total * 100) if total > 0 else 0
    low_conf_rate = (low_conf / decisions * 100) if decisions > 0 else 0

    def bar(value, max_val, width=20, fill="█", empty="░"):
        filled = int((value / max_val) * width) if max_val > 0 else 0
        return fill * filled + empty * (width - filled)

    def status_color(rate, warn=5, danger=15):
        if rate >= danger:
            return "\033[91m"
        elif rate >= warn:
            return "\033[93m"
        return "\033[92m"

    reset = "\033[0m"
    bold = "\033[1m"
    dim = "\033[2m"

    print(f"{bold}┌─ odd-agentos observability ─────────────────────── {now} ─┐{reset}")
    print()

    print(f"  {bold}LLM Calls{reset}")
    print(f"  total      {bold}{total:>6}{reset}    active now  {bold}{active:>3}{reset}")
    print(f"  errors     {status_color(error_rate)}{errors:>6}{reset}    error rate  {status_color(error_rate)}{error_rate:>5.1f}%{reset}")
    print()

    print(f"  {bold}Latency (ms){reset}")
    print(f"  p50   {p50:>7.0f}   {dim}{bar(p50, max(p99, 1000))}{reset}")
    print(f"  p95   {p95:>7.0f}   {dim}{bar(p95, max(p99, 1000))}{reset}")
    print(f"  p99   {p99:>7.0f}   {dim}{bar(p99, max(p99, 1000))}{reset}")
    print()

    print(f"  {bold}Decisions{reset}")
    print(f"  total      {bold}{decisions:>6}{reset}")
    lc_color = status_color(low_conf_rate, warn=10, danger=25)
    print(f"  low conf   {lc_color}{low_conf:>6}{reset}    rate        {lc_color}{low_conf_rate:>5.1f}%{reset}")
    print()

    if low_conf_rate > 25:
        print(f"  \033[91m[!] High low-confidence rate — check policy logic{reset}")
    elif error_rate > 15:
        print(f"  \033[91m[!] High error rate — check LLM connectivity / rate limits{reset}")
    elif p95 > 3000:
        print(f"  \033[93m[~] p95 latency > 3s — consider timeout / retry policy{reset}")
    else:
        print(f"  \033[92m[ok] All systems nominal{reset}")
    print()
    print(f"{dim}  q to quit  ·  refreshes every 3s{reset}")
    print(f"{bold}└──────────────────────────────────────────────────────────┘{reset}")


def run_dashboard(interval: float = 3.0):
    """Blocking dashboard loop — run in main thread or a dedicated thread."""
    try:
        from observability import obs
    except ImportError:
        print("observability.py not found in path. Place it alongside dashboard.py.")
        sys.exit(1)

    print("Starting dashboard... (q + Enter to quit)")
    time.sleep(0.5)

    while True:
        clear()
        render(obs.summary())
        time.sleep(interval)


def start_dashboard_thread(interval_seconds: float = 3.0) -> threading.Thread:
    """Non-blocking: launch dashboard in background thread."""
    t = threading.Thread(target=run_dashboard, args=(interval_seconds,), daemon=True)
    t.start()
    return t


# ---------------------------------------------------------------------------
# Quick smoke test — simulates some calls to demo the dashboard
# ---------------------------------------------------------------------------

def _smoke_test():
    from observability import obs, track_llm_call, track_decision
    import random

    print("Running smoke test — simulating 20 LLM calls + decisions...")

    for i in range(20):
        latency = random.gauss(350, 120)
        status = "error" if random.random() < 0.08 else "success"
        obs.record_llm_call(
            model="claude-sonnet-4-6",
            policy="pmf-analysis",
            latency_ms=max(50, latency),
            status=status,
        )
        if status == "success":
            confidence = random.uniform(0.45, 0.98)
            obs.record_decision(
                decision_id=f"run-{i:03d}",
                outcome="approved" if confidence > 0.6 else "needs_review",
                confidence=confidence,
                policy="pmf-analysis",
                latency_ms=max(50, latency) + random.uniform(10, 50),
            )
        time.sleep(0.05)

    print("\nSmoke test complete. Summary:")
    import json
    print(json.dumps(obs.summary(), indent=2))
    print("\nLaunching dashboard (Ctrl+C to exit)...")
    time.sleep(1)
    run_dashboard()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        _smoke_test()
    else:
        run_dashboard()
