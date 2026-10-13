"""Demo runner for the CFO, CMO and COO agents.

    python3 demo.py                 # scripted walkthrough of all three agents
    python3 demo.py cfo             # chat with one agent interactively (cfo | cmo | coo)

Set ANTHROPIC_API_KEY to route questions through Claude with tool use.
Without a key, agents run offline using their built-in routing.
"""
import os
import sys

from cfo import CFOAgent
from cmo import CMOAgent
from coo import COOAgent

AGENTS = {"cfo": CFOAgent, "cmo": CMOAgent, "coo": COOAgent}

SCRIPT = {
    "cfo": [
        "How much runway do we have left?",
        "What are our unit economics and CAC payback?",
        "Give me a revenue forecast for next quarter.",
    ],
    "cmo": [
        "Which marketing channels are most efficient?",
        "Where should we put a 200K monthly budget?",
        "What does our funnel conversion look like?",
    ],
    "coo": [
        "How is support SLA performing?",
        "Which projects are at risk?",
        "Give me the operations scorecard.",
    ],
}


def mode_label() -> str:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return f"Claude API ({os.environ.get('EXEC_AGENTS_MODEL', 'claude-sonnet-5-5')}) with tool use"
    return "offline (rule-based routing over the same tools; set ANTHROPIC_API_KEY for Claude)"


def run_script():
    print(f"Mode: {mode_label()}\n")
    for role, questions in SCRIPT.items():
        agent = AGENTS[role]()
        print("=" * 72)
        print(f"{agent.title} agent")
        print("=" * 72)
        for q in questions:
            print(f"\nQ: {q}")
            print(agent.ask(q))
            used = ", ".join(c["tool"] for c in agent.calls) or "none"
            print(f"[tools: {used}]")
        print()


def run_chat(role: str):
    agent = AGENTS[role]()
    print(f"{agent.title} agent. Mode: {mode_label()}")
    print("Type a question, or 'exit' to quit.\n")
    while True:
        try:
            q = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if q.lower() in {"exit", "quit"}:
            break
        if not q:
            continue
        print(agent.ask(q))
        used = ", ".join(c["tool"] for c in agent.calls) or "none"
        print(f"[tools: {used}]\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        role = sys.argv[1].lower()
        if role not in AGENTS:
            sys.exit(f"Unknown agent '{role}'. Choose from: {', '.join(AGENTS)}")
        run_chat(role)
    else:
        run_script()
