# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Analytic Budget Dashboard",
    "summary": "Budget against actual of the analytic plan hierarchy",
    "version": "18.0.1.0.0",
    "category": "Accounting/Analytic",
    "website": "https://github.com/OCA/account-budgeting",
    "author": "Quim Rebull (Coopdevs), Odoo Community Association (OCA)",
    "maintainers": ["QuiJoQuim"],
    "license": "AGPL-3",
    "development_status": "Alpha",
    "depends": [
        "account_budget_analytic_plan",
        "account_analytic_dashboard",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/budget_report_security.xml",
        "views/budget_report_views.xml",
        "data/dashboards.xml",
    ],
    "assets": {
        "web.assets_tests": [
            "account_budget_analytic_dashboard/static/tests/tours/*.js",
        ],
    },
    "installable": True,
    "application": False,
}
