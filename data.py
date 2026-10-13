"""Synthetic sample data for a fictional company, Northwind Labs.

Every number here is invented for demonstration. To use the agents on a real
business, replace these structures with exports from your accounting system,
CRM, ad platforms, helpdesk, HRIS and project tracker.
"""
from datetime import date

COMPANY = "Northwind Labs (sample data)"
AS_OF = date(2026, 10, 10)

# ---- finance ----------------------------------------------------------------
CASH_START = 4_200_000        # cash on hand at 1 Jan 2026, USD
COGS_PCT = 0.24               # cost of revenue as a share of revenue
ANNUAL_CHURN = 0.12
AVG_ACV = 24_000              # average annual contract value, USD

N_MONTHS = 10
LABELS = [f"2026-{m:02d}" for m in range(1, N_MONTHS + 1)]

REVENUE = [round(180_000 * 1.06 ** i) for i in range(N_MONTHS)]
SALES_MKT = [150_000 + 4_000 * i for i in range(N_MONTHS)]
R_AND_D = [220_000 + 5_000 * i for i in range(N_MONTHS)]
G_AND_A = [60_000 + 1_000 * i for i in range(N_MONTHS)]


def monthly_pnl():
    rows = []
    for i, label in enumerate(LABELS):
        rev = REVENUE[i]
        cogs = round(rev * COGS_PCT)
        opex = SALES_MKT[i] + R_AND_D[i] + G_AND_A[i]
        rows.append({
            "month": label,
            "revenue": rev,
            "cogs": cogs,
            "gross_profit": rev - cogs,
            "sales_marketing": SALES_MKT[i],
            "r_and_d": R_AND_D[i],
            "g_and_a": G_AND_A[i],
            "opex": opex,
            "net": rev - cogs - opex,
        })
    return rows


def cash_balance_series():
    balance, series = CASH_START, []
    for row in monthly_pnl():
        balance += row["net"]
        series.append(balance)
    return series


# ---- marketing (October) ----------------------------------------------------
CHANNELS = [
    {"channel": "Paid search",   "spend": 36_000, "leads": 640, "mqls": 210, "sqls": 58, "customers": 2},
    {"channel": "Paid social",   "spend": 22_000, "leads": 910, "mqls": 150, "sqls": 21, "customers": 1},
    {"channel": "Content / SEO", "spend": 10_000, "leads": 420, "mqls": 160, "sqls": 47, "customers": 2},
    {"channel": "Partnerships",  "spend": 14_000, "leads": 120, "mqls": 80,  "sqls": 38, "customers": 1},
    {"channel": "Events",        "spend": 40_000, "leads": 260, "mqls": 96,  "sqls": 31, "customers": 1},
    {"channel": "Outbound SDR",  "spend": 40_000, "leads": 300, "mqls": 140, "sqls": 52, "customers": 1},
]

# ---- operations -------------------------------------------------------------
TICKETS = [310, 325, 340, 362, 371, 398, 420, 441, 468, 490]
SUPPORT_SLA = [0.92, 0.90, 0.91, 0.88, 0.87, 0.85, 0.84, 0.82, 0.79, 0.78]
SLA_TARGET = 0.90             # share of tickets first-answered within 4 hours

INCIDENTS = [
    {"month": "2026-03", "severity": "SEV2", "minutes_down": 42},
    {"month": "2026-06", "severity": "SEV1", "minutes_down": 118},
    {"month": "2026-08", "severity": "SEV2", "minutes_down": 35},
    {"month": "2026-09", "severity": "SEV3", "minutes_down": 9},
]

HIRING = [
    {"role": "Senior backend engineer",    "days_open": 62, "stage": "Final interviews"},
    {"role": "Account executive",          "days_open": 47, "stage": "Offer out"},
    {"role": "Customer success manager",   "days_open": 21, "stage": "Sourcing"},
    {"role": "Data analyst",               "days_open": 8,  "stage": "Screening"},
]

PROJECTS = [
    {"name": "Billing v2 migration",   "owner": "Engineering", "start": date(2026, 7, 1), "due": date(2026, 11, 15), "pct_complete": 0.55},
    {"name": "SOC 2 Type II audit",    "owner": "Operations",  "start": date(2026, 6, 1), "due": date(2026, 10, 31), "pct_complete": 0.80},
    {"name": "EU data residency",      "owner": "Engineering", "start": date(2026, 8, 1), "due": date(2027, 1, 31),  "pct_complete": 0.20},
    {"name": "Partner portal launch",  "owner": "Marketing",   "start": date(2026, 9, 1), "due": date(2026, 10, 30), "pct_complete": 0.60},
]

VENDORS = [
    {"vendor": "Cloud hosting",        "category": "Infrastructure", "annual_cost": 264_000},
    {"vendor": "Recruiting agency",    "category": "People",         "annual_cost": 120_000},
    {"vendor": "CRM",                  "category": "Sales tools",    "annual_cost": 96_000},
    {"vendor": "Office & coworking",   "category": "G&A",            "annual_cost": 72_000},
    {"vendor": "Observability",        "category": "Infrastructure", "annual_cost": 60_000},
    {"vendor": "Ad platform fees",     "category": "Marketing",      "annual_cost": 48_000},
    {"vendor": "Analytics & BI",       "category": "Data",           "annual_cost": 36_000},
]
