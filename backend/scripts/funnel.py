#!/usr/bin/env python3
"""
Module 01 funnel report — reads the JSONL event logs and prints the
land -> brief -> requirements -> estimate -> runs -> checkpoint -> submit -> claim
funnel, per unique session.

Usage:
    python scripts/funnel.py [log_dir]

Defaults to $DATA_DIR/logs when DATA_DIR is set (Railway volume), else ../logs.
"""
import json
import os
import sys
from collections import Counter


def load_sessions(log_dir: str) -> dict:
    sessions = {}
    for fname in sorted(os.listdir(log_dir)):
        if not fname.endswith(".jsonl"):
            continue
        events = []
        with open(os.path.join(log_dir, fname)) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        if events:
            sessions[fname[:-6]] = events
    return sessions


def main():
    if len(sys.argv) > 1:
        log_dir = sys.argv[1]
    elif os.environ.get("DATA_DIR"):
        log_dir = os.path.join(os.environ["DATA_DIR"], "logs")
    else:
        log_dir = os.path.join(os.path.dirname(__file__), "../../logs")

    sessions = load_sessions(log_dir)
    # Only module 01 sessions (the research study logs share the directory)
    m01 = {
        sid: ev for sid, ev in sessions.items()
        if any(e.get("event") == "module_start" for e in ev)
    }

    def has(events, pred):
        return any(pred(e) for e in events)

    stages = [
        ("landed (module_start)", lambda ev: True),
        ("read the brief", lambda ev: has(ev, lambda e: e["event"] == "brief_read")),
        ("passed requirements", lambda ev: has(ev, lambda e: e["event"] == "requirements_checked" and e.get("all_correct"))),
        ("made an estimate", lambda ev: has(ev, lambda e: e["event"] == "prediction_made")),
        ("ran 1st simulation", lambda ev: sum(1 for e in ev if e["event"] in ("simulation_run", "polar_sweep", "table_compare")) >= 1),
        ("ran 3+ simulations", lambda ev: sum(1 for e in ev if e["event"] in ("simulation_run", "polar_sweep", "table_compare")) >= 3),
        ("answered checkpoint", lambda ev: has(ev, lambda e: e["event"] == "checkpoint_answer")),
        ("submitted design review", lambda ev: has(ev, lambda e: e["event"] == "review_submitted")),
        ("opened their artifact", lambda ev: has(ev, lambda e: e["event"] == "artifact_viewed")),
        ("left an email (claim)", lambda ev: has(ev, lambda e: e["event"] == "artifact_claimed")),
    ]

    n = len(m01)
    print(f"\nMODULE 01 FUNNEL — {n} sessions ({log_dir})")
    print("=" * 62)
    if n == 0:
        print("No module 01 sessions found.")
        return

    prev = n
    for label, pred in stages:
        count = sum(1 for ev in m01.values() if pred(ev))
        pct = 100 * count / n
        drop = "" if count >= prev else f"  (-{prev - count} dropped)"
        print(f"{label:<28} {count:>4}  {pct:5.1f}%{drop}")
        prev = count

    returning = sum(
        1 for ev in m01.values()
        if any(e.get("event") == "module_start" and e.get("returning") for e in ev)
    )
    wrong_re = sum(
        1 for ev in m01.values()
        if any(e["event"] == "simulation_run" and abs(e.get("reynolds", 500000) - 500000) > 25000 for e in ev)
    )
    signed_off = Counter(
        e.get("would_sign_off")
        for ev in m01.values() for e in ev
        if e["event"] == "checkpoint_answer"
    )
    runs = [
        sum(1 for e in ev if e["event"] in ("simulation_run", "polar_sweep", "table_compare"))
        for ev in m01.values()
    ]

    print("-" * 62)
    print(f"return visits: {returning} · median runs/session: {sorted(runs)[len(runs)//2]}")
    print(f"sessions with off-condition runs: {wrong_re}")
    print(f"intern checkpoint: {signed_off.get(False, 0)} refused sign-off, {signed_off.get(True, 0)} signed off")

    # Written reasoning — the founder reads every one
    print("\nCHECKPOINT REASONING (read these):")
    for sid, ev in m01.items():
        for e in ev:
            if e["event"] == "checkpoint_answer":
                verdict = "REFUSED" if not e.get("would_sign_off") else "SIGNED OFF"
                print(f"  [{sid[:8]} · {verdict}] {e.get('reasoning', '')[:160]}")


if __name__ == "__main__":
    main()
