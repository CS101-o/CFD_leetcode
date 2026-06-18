"""
Chat interface test cases for FlowSense.
Tests: question sequencing, tool gating, ambiguity handling, MC flow.
"""
import json
import requests

BASE = "http://127.0.0.1:8000/api/v1"
PID  = "solar-uav-pareto-001"
SID  = "test-session-001"

def ask(message, history):
    r = requests.post(f"{BASE}/flowsense/message", json={
        "problem_id": PID,
        "message": message,
        "conversation_history": history,
        "session_id": SID,
        "participant_id": "tester",
    }, timeout=120)
    r.raise_for_status()
    data = r.json()
    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": data["response"]},
    ]
    return data, history


def show(tc_id, description, user_msg, data):
    sim = "TOOL CALLED" if data.get("simulation_triggered") else "no tool"
    tools = data.get("tools_called", [])
    print(f"\n{'='*60}")
    print(f"TC{tc_id}: {description}")
    print(f"  USER : {user_msg}")
    print(f"  SIM  : {sim} {tools}")
    print(f"  REPLY: {data['response'][:400]}")


CASES = [
    # (description, user_message, expect_tool, expect_in_reply)
    ("First message — should ask Q1, not explain",
     "not much",
     False, "which of the two targets"),

    ("Baseline confirmation — should run polar on NACA 2412",
     "yes please run the baseline",
     True, "RESULTS"),

    ("No NACA code — should ask which airfoil",
     "try something with more camber",
     False, "which airfoil"),

    ("Valid NACA code — should run sweep and ask Q2",
     "run NACA 4412",
     True, "RESULTS"),

    ("Copy-pasted interview question as message — no tool",
     "Try a candidate that addresses your primary concern. Did the other metric move in the direction you expected?",
     False, "which airfoil"),

    ("Conceptual question — brief answer + probe, no tool",
     "what is camber and why does it matter?",
     False, "?"),

    ("Re-run prevention — already in history",
     "run baseline again on NACA 2412",
     False, None),

    ("Monte Carlo — should trigger MC and list candidates",
     "run monte carlo on NACA 4412",
     True, "CANDIDATE"),
]

history = []
passed = 0
failed = 0

for i, (desc, msg, expect_tool, expect_text) in enumerate(CASES, 1):
    try:
        data, history = ask(msg, history)
        show(i, desc, msg, data)

        ok = True
        if data.get("simulation_triggered") != expect_tool:
            print(f"  FAIL : expected tool={expect_tool}, got {data.get('simulation_triggered')}")
            ok = False
        if expect_text and expect_text.lower() not in data["response"].lower():
            print(f"  FAIL : expected '{expect_text}' in reply")
            ok = False
        if ok:
            print(f"  PASS")
            passed += 1
        else:
            failed += 1
    except Exception as e:
        print(f"\nTC{i} ERROR: {e}")
        failed += 1

print(f"\n{'='*60}")
print(f"RESULTS: {passed} passed / {failed} failed / {len(CASES)} total")
