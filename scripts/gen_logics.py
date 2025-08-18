import os, re

ROOT = os.path.dirname(os.path.dirname(__file__))
LOGICS_DIR = os.path.join(ROOT, "logics")
os.makedirs(LOGICS_DIR, exist_ok=True)

logic_titles = [
    "Profit and Loss Summary",
    "Balance Sheet",
    "Trial Balance",
    "Capital Account Summary",
    "Partner Withdrawals",
    "Zone-wise Expenses",
    "Material Purchase Summary",
    "Salary Summary",
    "Vendor Payment Summary",
    "Receivables Summary",
    "Payables Summary",
    "Debtor Ageing Buckets",
    "Creditor Ageing Buckets",
    "Invoice Status",
    "Bill Status",
    "GSTR Filing Status",
    "TDS Filing Status",
    "Highest Selling Items",
    "Highest Revenue Clients",
    "Client-wise Profitability",
    "PO-wise Profitability",
    "Item-wise Sales Summary",
    "Item-wise Profitability",
    "Employee Cost Trends",
    "Purchase Returns Summary",
    "Sales Returns Summary",
    "Dead Stock Report",
    "Stock Movement Report",
    "Cash Flow Statement",
    "Bank Reconciliation Status",
    "Expense Category Trends",
    "Monthly Revenue Trend",
    "Monthly Expense Trend",
    "Budget vs Actual Report",
    "Year-on-Year Growth",
    "Month-on-Month Comparison",
    "Project-wise Profitability",
    "Vendor-wise Spend",
    "Tax Summary Report",
    "GST Reconciliation Status",
    "TDS Deducted vs Paid",
    "Credit Utilization Percentage",
    "Sales Conversion Ratio",
    "Revenue Forecast",
    "Expense Forecast",
    "Upcoming Invoice Dues",
    "Upcoming Bill Payments",
    "Receivable Alerts",
    "Payable Alerts",
    "Loan Outstanding Summary",
    "Interest Paid Summary",
    "Capital Invested Timeline",
    "Shareholder Equity Movement",
    "Depreciation Calculation",
    "Fixed Asset Register",
    "Inventory Valuation",
    "Raw Material Usage",
    "Bill of Materials Breakdown",
    "Overhead Cost Allocation",
    "Manufacturing Cost Sheet",
    "Production Efficiency Report",
    "Sales Team Performance",
    "Employee Productivity Analysis",
    "Client Acquisition Cost",
    "Lead to Client Ratio",
    "Marketing Spend Efficiency",
    "Campaign ROI Summary",
    "Departmental P&L",
    "Business Vertical Summary",
    "Inter-company Transactions",
    "Fund Transfer Logs",
    "Internal Audit Checklist",
    "Compliance Tracker",
    "Audit Trail Summary",
    "Error Detection Engine",
    "Anomaly Detection Report",
    "Vendor Duplication Check",
    "Client Duplication Check",
    "Data Entry Consistency",
    "Duplicate Invoice Detection",
    "Outlier Expenses Detection",
    "Salary vs Market Benchmark",
    "Tax Liability Estimator",
    "Input Tax Credit Reconciliation",
    "Late Filing Penalty Tracker",
    "Missed Payment Tracker",
    "Recurring Expenses Monitor",
    "Profit Leakage Detector",
    "Unbilled Revenue Tracker",
    "Advance Received Adjustment",
    "Advance Paid Adjustment",
    "Suspense Account Monitor",
    "Accounting Hygiene Score",
    "Business Health Score",
    "Scenario Simulation Engine",
    "Expense Optimization Engine",
    "Credit Rating Estimator",
    "Business Valuation Estimator",
    "Dividend Recommendation Engine",
    "Risk Assessment Matrix",
    "Cash Reserve Advisor",
    "Strategic Suggestion Engine",
    "Auto Reconciliation Suggestion",
    "Fabrication vs Billing Variance",
    "BOQ vs Actual Cost",
    "Material Rate Change Monitor",
    "Inter-Branch Transfer Log",
    "Employee Reimbursement Check",
    "Pending Approvals Summary",
    "Backdated Entry Detector",
    "Late Vendor Payment Penalty Alert",
    "Margin Pressure Tracker (Cost ↑ vs Price ↔)",
    "Contract Breach Detection",
    "Client Risk Profiling",
    "Invoice Bounce Predictor",
    "High Risk Vendor Pattern",
    "Multi-GSTIN Entity Aggregator",
    "Real-Time Working Capital Snapshot",
    "Invoice Duplication Prevention on Entry",
    "Cross-Period Adjustment Tracker",
    "Manual Journal Suspicion Detector",
    "Round-off Abuse Detector",
    "Loan Covenant Breach Alert",
    "Expense Inflation Flag (Employee-wise)",
    "Inventory Shrinkage Alert",
    "Transaction Volume Spike Alert",
    "Overdue TDS Deduction Cases",
    "Related Party Transaction Tracker",
    "Vendor Contract Expiry Alert",
    "Unverified GSTIN Alert",
    "HSN-SAC Mapping Auditor",
    "AI Error Suggestion Engine",
    "Report Consistency Verifier (across months)",
    "Audit-Ready Report Generator",
    "Internal Control Weakness Identifier",
    "Monthly Report Completeness Checker",
    "Suggested Journal Entry Fixes",
    "Pending JE Approvals",
    "Partial Payments Tracker",
    "Reverse Charge Monitor (GST)",
    "P&L Ratio Anomaly Finder",
    "Mismatch in Payment vs Invoice Timeline",
    "Free Resource Usage Estimator (Power, Tools, etc.)",
    "Industry Benchmark Comparison Report",
    "Vendor-side Carbon Emissions Estimator",
    "Zone-wise Carbon Score",
    "Green Vendor Scorecard",
    "Data Redundancy Detector",
    "Audit Flag Generator (AI Marked High Risk Areas)",
    "CA Review Ready Index",
    "Audit Automation Wizard (Step-by-step walkthrough)",
    "Auto-Fill for Common Journal Entries (AI trained on history)",
    "Period Lock & Unlock Tracker",
    "Custom Rule Builder (for clients using SaaS version)",
    "CFO Dashboard Generator",
    "Financial KPI Designer",
    "Self-learning Prediction Engine (for revenue/expense)",
    "Multi-company Consolidation Reports",
    "Alerts via Telegram/Slack/Email/WhatsApp",
    "Custom User Access Logs and Abuse Detection",
    "File Upload to Entry Mapper (e.g., Invoice PDF → JE)",
    "Voice-to-Entry (convert spoken input to journal)",
    "Advanced Filing Calendar Sync (GST, ROC, TDS)",
    "API-based Third Party Integration Framework",
    "Bank Feed Intelligence Layer",
    "Year-end Closure Guide",
    "Investment vs Working Capital Allocator",
    "Performance Linked Pay Analyzer",
    "Cross-company Loan Tracker",
    "Government Scheme Utilization Tracker",
    "Legal Case Cost Monitor",
    "Automation of Monthly Compliance Summary",
    "DSCR and ICR Calculators for Banking",
    "Auto CA Remarks Based on Reports",
    "User Behavior Based Module Suggestions",
    "Scoring System for Business Maturity Level",
    "CA Review Collaboration Toolkit",
    "AI-Powered Explanation Tool (Explain balance sheet in plain Hindi)",
    "Journal Trace Visualizer (graph view of entry relationships)",
    "Interlinked Report Mapper",
]

TEMPLATE = '''"""
Title: {title}
ID: L-{id3}
Tags: ["mis"]
Required Inputs: {{org_id, start_date, end_date}}
Outputs: {{result, provenance, confidence, alerts, meta}}
Assumptions: Placeholder compute
Evolution Notes: Strategies to be learned from usage
"""

from __future__ import annotations
from typing import Any, Dict
from helpers.learning_hooks import score_confidence
from helpers.history_store import write_event

LOGIC_META = {{
    "id": "L-{id3}",
    "title": "{title_escaped}",
    "tags": ["mis"],
}}

def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {{}}
    provenance = {{"sources": []}}
    alerts: list[str] = []
    confidence = score_confidence(result)

    write_event("logic_L-{id3}", {{
        "inputs": {{k: payload.get(k) for k in ["org_id", "start_date", "end_date"]}},
        "outputs": result,
        "alerts": alerts,
    }})

    return {{
        "result": result,
        "provenance": provenance,
        "confidence": confidence,
        "alerts": alerts,
        "meta": {{"strategy": "v0"}},
    }}
'''


def snake_case(title: str) -> str:
    t = title.lower()
    t = t.replace("&", " and ").replace("+", " plus ")
    t = re.sub(r"[^a-z0-9]+", "_", t).strip("_")
    t = re.sub(r"_+", "_", t)
    return t


def main():
    for idx, title in enumerate(logic_titles, start=1):
        id3 = f"{idx:03d}"
        fname = f"logic_{id3}_{snake_case(title)}.py"
        path = os.path.join(LOGICS_DIR, fname)
        if os.path.exists(path):
            print(f"skip exists: {fname}")
            continue
        with open(path, "w") as f:
            f.write(
                TEMPLATE.format(
                    id3=id3, title=title, title_escaped=title.replace('"', '\\\\"')
                )
            )
        print(f"created: {fname}")


if __name__ == "__main__":
    main()
