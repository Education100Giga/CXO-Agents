"""Shared scaffolding for the executive agents.

Each agent has:
  * tools         - plain Python functions that read the company data
  * routes        - keyword routing used by the offline (no-API-key) mode
  * system_prompt - used when ANTHROPIC_API_KEY is set: the Claude API drives
                    the same tools through a standard tool-use loop
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable

MODEL = os.environ.get("EXEC_AGENTS_MODEL", "claude-sonnet-5-5")
MAX_TOOL_ROUNDS = 6


@dataclass
class Tool:
    name: str
    description: str
    schema: dict
    fn: Callable[..., Any]


def schema(properties: dict | None = None, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": properties or {}, "required": required or []}


def money(x: float | None) -> str:
    if x is None:
        return "n/a"
    sign = "-" if x < 0 else ""
    x = abs(x)
    if x >= 1_000_000:
        return f"{sign}${x / 1_000_000:.2f}M"
    if x >= 1_000:
        return f"{sign}${x / 1_000:,.0f}K"
    return f"{sign}${x:,.0f}"


def pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x * 100:.1f}%"


class ExecAgent:
    title = "Executive"
    system_prompt = ""
    # (keywords, method name) pairs, checked in order by the offline router
    routes: list[tuple[tuple[str, ...], str]] = []

    def __init__(self, tools: list[Tool]):
        self.tools = {t.name: t for t in tools}
        self.calls: list[dict] = []

    # ------------------------------------------------------------------ public
    def ask(self, question: str) -> str:
        self.calls = []
        if os.environ.get("ANTHROPIC_API_KEY"):
            return self._ask_llm(question)
        return self._ask_offline(question)

    # ---------------------------------------------------------------- internals
    def call_tool(self, name: str, **kwargs):
        result = self.tools[name].fn(**kwargs)
        self.calls.append({"tool": name, "input": kwargs})
        return result

    def _ask_offline(self, question: str) -> str:
        q = question.lower()
        for keywords, method in self.routes:
            if any(k in q for k in keywords):
                return getattr(self, method)(question)
        return self.default_answer()

    def default_answer(self) -> str:
        raise NotImplementedError

    def _ask_llm(self, question: str) -> str:
        try:
            import anthropic
        except ImportError as exc:
            raise SystemExit("Install the SDK first: pip install anthropic") from exc

        workspace_id = os.environ.get("ANTHROPIC_WORKSPACE_ID")
        headers = {"anthropic-workspace-id": workspace_id} if workspace_id else None
        client = anthropic.Anthropic(default_headers=headers)
        tool_specs = [
            {"name": t.name, "description": t.description, "input_schema": t.schema}
            for t in self.tools.values()
        ]
        messages = [{"role": "user", "content": question}]
        for _ in range(MAX_TOOL_ROUNDS):
            resp = client.messages.create(
                model=MODEL,
                max_tokens=1200,
                system=self.system_prompt,
                tools=tool_specs,
                messages=messages,
            )
            if resp.stop_reason != "tool_use":
                return "\n".join(b.text for b in resp.content if b.type == "text").strip()

            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for block in resp.content:
                if block.type == "tool_use":
                    out = self.call_tool(block.name, **block.input)
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(out, default=str),
                    })
            messages.append({"role": "user", "content": results})
        return "Stopped after too many tool rounds."
