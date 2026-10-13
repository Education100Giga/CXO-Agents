"""COO agent: operations scorecard, support SLA, hiring, delivery risk and vendor spend."""
import data as d
from base import ExecAgent, Tool, money, pct, schema


def support_sla():
    below = [m for m, v in zip(d.LABELS, d.SUPPORT_SLA) if v < d.SLA_TARGET]
    return {
        "latest_month": d.LABELS[-1],
        "latest_sla": d.SUPPORT_SLA[-1],
        "target": d.SLA_TARGET,
        "first_month_below_target": below[0] if below else None,
        "months_below_target": len(below),
        "tickets_first_month": d.TICKETS[0],
        "tickets_latest_month": d.TICKETS[-1],
    }


def hiring_status():
    return {
        "open_roles": len(d.HIRING),
        "roles": d.HIRING,
        "open_over_45_days": [r["role"] for r in d.HIRING if r["days_open"] > 45],
    }


def project_risks(tolerance: float = 0.15):
    out = []
    for p in d.PROJECTS:
        total = (p["due"] - p["start"]).days
        elapsed = min(total, max(0, (d.AS_OF - p["start"]).days))
        expected = elapsed / total
        gap = expected - p["pct_complete"]
        out.append({
            "project": p["name"],
            "owner": p["owner"],
            "pct_complete": p["pct_complete"],
            "expected_pct": round(expected, 2),
            "gap": round(gap, 2),
            "days_left": (p["due"] - d.AS_OF).days,
            "at_risk": gap > tolerance,
        })
    return out


def vendor_spend():
    by_cat = {}
    for v in d.VENDORS:
        by_cat[v["category"]] = by_cat.get(v["category"], 0) + v["annual_cost"]
    return {
        "total_annual": sum(v["annual_cost"] for v in d.VENDORS),
        "by_category": dict(sorted(by_cat.items(), key=lambda kv: -kv[1])),
        "top_3": sorted(d.VENDORS, key=lambda v: -v["annual_cost"])[:3],
    }


def ops_scorecard():
    return {
        "support_sla_latest": d.SUPPORT_SLA[-1],
        "sla_target": d.SLA_TARGET,
        "tickets_latest_month": d.TICKETS[-1],
        "incidents_ytd": len(d.INCIDENTS),
        "downtime_minutes_ytd": sum(i["minutes_down"] for i in d.INCIDENTS),
        "sev1_incidents": sum(1 for i in d.INCIDENTS if i["severity"] == "SEV1"),
        "open_roles": len(d.HIRING),
        "projects_at_risk": [p["project"] for p in project_risks() if p["at_risk"]],
        "annual_vendor_spend": sum(v["annual_cost"] for v in d.VENDORS),
    }


class COOAgent(ExecAgent):
    title = "COO"
    system_prompt = (
        "You are the COO agent for Northwind Labs. Focus on execution: service levels, "
        "delivery risk, hiring velocity and cost. For every risk, name the owner and "
        "propose a concrete next step with a date. Use tool results for every figure."
    )
    routes = [
        (("sla", "support", "ticket", "customer"), "_support"),
        (("hire", "hiring", "recruit", "open role", "headcount"), "_hiring"),
        (("project", "roadmap", "deliver", "risk", "delay", "on track", "late"), "_projects"),
        (("vendor", "contract", "saas", "tool spend", "procure"), "_vendors"),
    ]

    def __init__(self):
        super().__init__([
            Tool("ops_scorecard",
                 "One-page operations summary: support SLA, incidents, hiring, project risk and vendor spend.",
                 schema(), ops_scorecard),
            Tool("support_sla",
                 "Support SLA trend against target, plus ticket volume trend.",
                 schema(), support_sla),
            Tool("hiring_status",
                 "Open roles with days open and stage; flags roles open longer than 45 days.",
                 schema(), hiring_status),
            Tool("project_risks",
                 "Each project's actual progress vs time-elapsed expectation; flags gaps above tolerance.",
                 schema({"tolerance": {"type": "number", "description": "Allowed gap, default 0.15"}}),
                 project_risks),
            Tool("vendor_spend",
                 "Annual vendor spend by category and the top three vendors.",
                 schema(), vendor_spend),
        ])

    def default_answer(self):
        r = self.call_tool("ops_scorecard")
        return (
            "Operations scorecard\n"
            f"- Support SLA: {pct(r['support_sla_latest'])} vs {pct(r['sla_target'])} target\n"
            f"- Tickets in latest month: {r['tickets_latest_month']}\n"
            f"- Incidents this year: {r['incidents_ytd']} "
            f"({r['downtime_minutes_ytd']} minutes down, {r['sev1_incidents']} SEV1)\n"
            f"- Open roles: {r['open_roles']}\n"
            f"- Projects at risk: {', '.join(r['projects_at_risk']) or 'none'}\n"
            f"- Annual vendor spend: {money(r['annual_vendor_spend'])}"
        )

    def _support(self, q):
        r = self.call_tool("support_sla")
        growth = r["tickets_latest_month"] / r["tickets_first_month"] - 1
        return (
            f"Support SLA in {r['latest_month']}: {pct(r['latest_sla'])} of tickets first-answered "
            f"within 4 hours, against a {pct(r['target'])} target.\n"
            f"It has been below target for {r['months_below_target']} months, since "
            f"{r['first_month_below_target']}. Ticket volume rose {pct(growth)} over the same period, "
            "so the slide tracks load rather than a single bad month.\n\n"
            "Next step: add first-response coverage or deflect routine questions with help-center "
            "content before hiring more agents."
        )

    def _hiring(self, q):
        r = self.call_tool("hiring_status")
        lines = "\n".join(
            f"- {x['role']}: {x['days_open']} days open, stage: {x['stage']}" for x in r["roles"]
        )
        stale = ", ".join(r["open_over_45_days"]) or "none"
        return (
            f"{r['open_roles']} open roles:\n{lines}\n\n"
            f"Open more than 45 days: {stale}. Set a decision date for each and confirm the offer "
            "pipeline before opening new reqs."
        )

    def _projects(self, q):
        rows = self.call_tool("project_risks")
        at_risk = [p for p in rows if p["at_risk"]]
        if not at_risk:
            return "No projects are behind their time-elapsed expectation beyond tolerance."
        lines = "\n".join(
            f"- {p['project']} ({p['owner']}): {pct(p['pct_complete'])} complete vs about "
            f"{pct(p['expected_pct'])} expected, {p['days_left']} days to due date"
            for p in at_risk
        )
        return (
            f"{len(at_risk)} of {len(rows)} projects are at risk:\n{lines}\n\n"
            "Ask each owner for a recovery plan by end of week, and decide whether to re-baseline "
            "the date or cut scope. Re-check progress in two weeks."
        )

    def _vendors(self, q):
        r = self.call_tool("vendor_spend")
        top = ", ".join(f"{v['vendor']} ({money(v['annual_cost'])})" for v in r["top_3"])
        return (
            f"Annual vendor spend: {money(r['total_annual'])}.\n"
            f"Top three: {top}.\n"
            "The recruiting agency fee is the most discretionary of these. Review its terms "
            "before the next search, since in-house sourcing may cover some roles."
        )
