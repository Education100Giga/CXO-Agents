"""CMO agent: channel efficiency, funnel conversion and budget allocation."""
import re

import data as d
from base import ExecAgent, Tool, money, pct, schema


def channel_performance():
    rows = []
    for c in d.CHANNELS:
        cac = c["spend"] / c["customers"] if c["customers"] else None
        rows.append({
            "channel": c["channel"],
            "spend": c["spend"],
            "new_customers": c["customers"],
            "cac": cac,
            "sqls": c["sqls"],
            "cost_per_sql": c["spend"] / c["sqls"],
        })
    return sorted(rows, key=lambda r: (r["cac"] is None, r["cac"] or 0))


def funnel_metrics():
    leads = sum(c["leads"] for c in d.CHANNELS)
    mqls = sum(c["mqls"] for c in d.CHANNELS)
    sqls = sum(c["sqls"] for c in d.CHANNELS)
    customers = sum(c["customers"] for c in d.CHANNELS)
    return {
        "leads": leads, "mqls": mqls, "sqls": sqls, "customers": customers,
        "lead_to_mql": mqls / leads,
        "mql_to_sql": sqls / mqls,
        "sql_to_customer": customers / sqls,
    }


def allocate_budget(total_budget: float):
    """Weight channels by customers per dollar (square-rooted to soften extremes),
    capping any channel at 2x its current spend and redistributing the overflow."""
    current = {c["channel"]: c["spend"] for c in d.CHANNELS}
    eff = {c["channel"]: (c["customers"] / c["spend"]) ** 0.5 for c in d.CHANNELS}
    alloc, active, remaining = {}, set(current), float(total_budget)
    while active:
        w = sum(eff[ch] for ch in active)
        raw = {ch: remaining * eff[ch] / w for ch in active}
        over = [ch for ch in active if raw[ch] > 2 * current[ch]]
        if not over:
            alloc.update(raw)
            break
        for ch in over:
            alloc[ch] = 2 * current[ch]
            remaining -= alloc[ch]
            active.remove(ch)
    return [
        {"channel": ch, "current_spend": current[ch], "proposed": round(alloc[ch]),
         "change_pct": alloc[ch] / current[ch] - 1}
        for ch in sorted(current, key=lambda c: -alloc[c])
    ]


def _parse_amount(text: str, default: float) -> float:
    m = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*(k|m)?\b", text.lower())
    if not m:
        return default
    mult = {"k": 1_000, "m": 1_000_000}.get(m.group(2), 1)
    return float(m.group(1).replace(",", "")) * mult


class CMOAgent(ExecAgent):
    title = "CMO"
    system_prompt = (
        "You are the CMO agent for Northwind Labs. Judge channels on CAC and cost per "
        "qualified lead, not on volume. Use tool results for every figure, and recommend "
        "changes as tests with a cap on how far spend moves in one step."
    )
    routes = [
        (("budget", "allocate", "reallocate", "where should", "where to put"), "_budget"),
        (("funnel", "conversion", "pipeline", "mql", "sql"), "_funnel"),
        (("channel", "cac", "roi", "efficient", "best", "worst", "performing"), "_channels"),
    ]

    def __init__(self):
        super().__init__([
            Tool("channel_performance",
                 "Per-channel spend, new customers, CAC and cost per SQL, sorted by CAC (lowest first).",
                 schema(), channel_performance),
            Tool("funnel_metrics",
                 "Lead to MQL to SQL to customer totals and conversion rates.",
                 schema(), funnel_metrics),
            Tool("allocate_budget",
                 "Propose a channel budget split for a total monthly amount, capped at 2x current spend per channel.",
                 schema({"total_budget": {"type": "number", "description": "Total monthly budget in USD"}},
                        ["total_budget"]),
                 allocate_budget),
        ])

    def default_answer(self):
        return self._channels("") + "\n\n" + self._funnel("")

    def _channels(self, q):
        rows = self.call_tool("channel_performance")
        lines = "\n".join(
            f"- {r['channel']}: CAC {money(r['cac'])} on {money(r['spend'])} spend "
            f"({r['new_customers']} {'customer' if r['new_customers'] == 1 else 'customers'}, "
            f"{money(r['cost_per_sql'])} per SQL)"
            for r in rows
        )
        best, worst = rows[0], rows[-1]
        return (
            "Channels ranked by CAC, lowest first:\n"
            f"{lines}\n\n"
            f"{best['channel']} is the most efficient. {worst['channel']} costs about "
            f"{worst['cac'] / best['cac']:.0f}x as much per customer. Before cutting it, check "
            "whether it feeds brand or enterprise deals that take longer to convert."
        )

    def _funnel(self, q):
        f = self.call_tool("funnel_metrics")
        weakest = min(
            [("lead to MQL", f["lead_to_mql"]), ("MQL to SQL", f["mql_to_sql"]),
             ("SQL to customer", f["sql_to_customer"])],
            key=lambda x: x[1],
        )
        return (
            f"October funnel: {f['leads']:,} leads, {f['mqls']} MQLs, {f['sqls']} SQLs, "
            f"{f['customers']} new customers.\n"
            f"- Lead to MQL: {pct(f['lead_to_mql'])}\n"
            f"- MQL to SQL: {pct(f['mql_to_sql'])}\n"
            f"- SQL to customer: {pct(f['sql_to_customer'])}\n\n"
            f"The weakest step is {weakest[0]}. Sales is closing a small share of qualified "
            "pipeline, so improving close rate is worth more than adding leads."
        )

    def _budget(self, q):
        current_total = sum(c["spend"] for c in d.CHANNELS)
        total = _parse_amount(q, current_total)
        rows = self.call_tool("allocate_budget", total_budget=total)
        lines = "\n".join(
            f"- {r['channel']}: {money(r['proposed'])} "
            f"(now {money(r['current_spend'])}, {r['change_pct'] * 100:+.0f}%)"
            for r in rows
        )
        return (
            f"Proposed split for a {money(total)} monthly budget, weighted toward customers per dollar:\n"
            f"{lines}\n\n"
            "Every channel is capped at 2x its current spend. Move money in stages and check "
            "CAC after each month, since small channels can get noisy at higher spend."
        )
