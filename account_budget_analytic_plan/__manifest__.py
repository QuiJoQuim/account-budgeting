# Copyright (C) 2026
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Budget Analytic Plan",
    "summary": "Manage budget lines by analytic plan",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "license": "LGPL-3",
    "author": "Quim Rebull (Coopdevs), Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-budgeting",
    "depends": ["account_budget_oca"],
    "data": [
        "views/account_budget_views.xml",
        "views/account_analytic_plan_views.xml",
    ],
    "installable": True,
    "application": False,
}
