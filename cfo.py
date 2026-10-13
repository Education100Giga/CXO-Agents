"""CFO agent: P&L, cash runway, revenue forecast and unit economics."""
import data as d
from base import ExecAgent, Tool, money, pct, schema


def pnl_summary(months: int = 3):
    rows = d.monthly_pnl()[-months:]
    rev = sum(r["revenue"] for r in rows)
    gp = sum(r["gross_profit"] for r in rows)
    opex = {k: sum(r[k] for r in rows) for k in ("sales_marketing", "r_and_d", "g_and_a")}
    return {
        "months": [r["month"] for r in rows],
        "revenue": rev,
        "gross_margin": gp / rev,
        "opex": sum(opex.values()),
        "opex_breakdown": opex,
        "net_operating_income": sum(r["net"] for r in rows),
        "revenue_growth_first_to_last": rows[-1]["revenue"] / rows[0]["revenue"] - 1,
    }


def cash_runway():
    cash = d.cash_balance_series()[-1]
    last3 = d.monthly_pnl()[-3:]
    avg_burn = -sum(r["net"] for r in last3) / 3
    runway = round(cash / avg_burn, 1) if avg_burn > 0 else None
    return {
        "cash": cash,
        "avg_monthly_burn_3m": avg_burn,
        "latest_month_burn": -d.monthly_pnl()[-1]["net"],
        "runway_months": runway,
    }


def forecast_revenue(months_ahead: int = 3):
    rev = d.REVENUE
    growth = (rev[-1] / rev[-7]) ** (1 / 6) - 1  # average monthly growth, last 6 months
    year, month = map(int, d.LABELS[-1].split("-"))
    value, out = rev[-1], []
    for _ in range(months_ahead):
        value *= 1 + growth
        month += 1
        if month > 12:
            month, year = 1, year + 1
        out.append({"month": f"{year}-{month:02d}", "revenue": round(value)})
    return {"avg_monthly_growth": growth, "projection": out}


def unit_economics():
    spend = sum(c["spend"] for c in d.CHANNELS)
    customers = sum(c["customers"] for c in d.CHANNELS)
    cac = spend / customers
    gm = 1 - d.COGS_PCT
    ltv = d.AVG_ACV * gm / d.ANNUAL_CHURN
    return {
        "blended_cac": cac,
        "avg_acv": d.AVG_ACV,
        "gross_margin": gm,
        "ltv": ltv,
        "ltv_to_cac": ltv / cac,
        "cac_payback_months": cac / (d.AVG_ACV / 12 * gm),
    }


class CFOAgent(ExecAgent):
    title = "CFO"
    system_prompt = (
        "You are the CFO agent for Northwind Labs. Ground every number in tool results, "
        "state the period you are describing, and flag runway under 6 months. "
        "You give operating analysis, not personal investment advice."
    )
    routes = [
        (("runway", "burn", "cash"), "_runway"),
        (("forecast", "projection", "next quarter"), "_forecast"),
        (("cac", "ltv", "payback", "unit econ"), "_unit"),
        (("margin", "profit", "p&l", "expense", "opex", "spend"), "_pnl"),
    ]

    def __init__(self):
        super().__init__([
            Tool("pnl_summary",
                 "Revenue, gross margin, opex breakdown and net operating income for the last N months.",
                 schema({"months": {"type": "integer", "description": "Number of trailing months (default 3)"}}),
                 pnl_summary),
            Tool("cash_runway",
                 "Cash on hand, average monthly burn over the last 3 months, and runway in months.",
                 schema(), cash_runway),
            Tool("forecast_revenue",
                 "Project revenue forward using the trailing 6-month average growth rate.",
                 schema({"months_ahead": {"type": "integer", "description": "Months to project (default 3)"}}),
                 forecast_revenue),
            Tool("unit_economics",
                 "Blended CAC, LTV, LTV:CAC ratio and CAC payback period.",
                 schema(), unit_economics),
        ])

    def default_answer(self):
        return self._runway("") + "\n\n" + self._pnl("")

    def _runway(self, q):
        r = self.call_tool("cash_runway")
        if r["runway_months"] is None:
            runway_line = "No net burn, so runway is not a constraint right now."
        else:
            warn = " Warning: under 6 months, so start contingency planning now." if r["runway_months"] < 6 else ""
            runway_line = f"Estimated runway: {r['runway_months']} months.{warn}"
        return (
            f"Cash on hand: {money(r['cash'])}\n"
            f"Average burn (last 3 months): {money(r['avg_monthly_burn_3m'])} per month\n"
            f"Latest month burn: {money(r['latest_month_burn'])}\n"
            f"{runway_line}"
        )

    def _pnl(self, q):
        r = self.call_tool("pnl_summary", months=3)
        labels = {"sales_marketing": "Sales & marketing", "r_and_d": "R&D", "g_and_a": "G&A"}
        bd = r["opex_breakdown"]
        biggest = max(bd, key=bd.get)
        net_margin = r["net_operating_income"] / r["revenue"]
        spend_per_dollar = r["opex"] / r["revenue"]
        return (
            f"Last 3 months ({r['months'][0]} to {r['months'][-1]}):\n"
            f"- Revenue: {money(r['revenue'])}, up {pct(r['revenue_growth_first_to_last'])} across the period\n"
            f"- Gross margin: {pct(r['gross_margin'])}\n"
            f"- Operating expenses: {money(r['opex'])}, led by {labels[biggest]} "
            f"({pct(bd[biggest] / r['opex'])} of opex)\n"
            f"- Net operating income: {money(r['net_operating_income'])} (net margin {pct(net_margin)})\n\n"
            f"For every $1 of revenue, the company spends about ${spend_per_dollar:.2f} on opex. "
            "Closing that gap depends on sales productivity and opex discipline."
        )

    def _forecast(self, q):
        r = self.call_tool("forecast_revenue", months_ahead=3)
        lines = "\n".join(f"- {p['month']}: {money(p['revenue'])}" for p in r["projection"])
        total = sum(p["revenue"] for p in r["projection"])
        return (
            f"Revenue projection at the trailing growth rate of {pct(r['avg_monthly_growth'])} per month:\n"
            f"{lines}\n"
            f"Next-quarter total: {money(total)}\n\n"
            "This is a trend extrapolation. It does not model churn events, pricing changes or "
            "new large deals, so treat it as a base case."
        )

    def _unit(self, q):
        r = self.call_tool("unit_economics")
        verdict = "above" if r["ltv_to_cac"] >= 3 else "below"
        return (
            f"Blended CAC (October): {money(r['blended_cac'])}\n"
            f"Average ACV: {money(r['avg_acv'])} at {pct(r['gross_margin'])} gross margin\n"
            f"Customer lifetime value: {money(r['ltv'])}\n"
            f"LTV:CAC: {r['ltv_to_cac']:.1f}x, {verdict} the common 3x rule of thumb\n"
            f"CAC payback: {r['cac_payback_months']:.1f} months"
        )
