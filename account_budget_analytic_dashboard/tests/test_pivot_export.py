# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date

from odoo.tests import tagged

from odoo.addons.account_analytic_searchpanel.tests.test_pivot_export import (
    PivotExportCase,
    export_table,
)


@tagged("post_install", "-at_install")
class TestPivotExport(PivotExportCase):
    def test_export_shows_budgets_and_period(self):
        # The budget report is for accountants
        self.env.ref("base.user_admin").groups_id += self.env.ref(
            "account.group_account_user"
        )
        Plan = self.env["account.analytic.plan"]
        root, _other_plans = Plan._get_all_plans()
        plan = Plan.create({"name": "Export Budget Plan", "parent_id": root.id})
        position = self.env["account.budget.post"].create(
            {
                "name": "Export Sales",
                "account_ids": [
                    (0, 0, {"name": "Export Sales", "code": "700777",
                            "account_type": "income"})
                ],
            }
        )
        budgets = self.env["crossovered.budget"]
        for name in ("Export Budget A", "Export Budget B"):
            budget = budgets.create(
                {"name": name, "date_from": date(2026, 1, 1),
                 "date_to": date(2026, 12, 31)}
            )
            self.env["crossovered.budget.lines"].create(
                {
                    "crossovered_budget_id": budget.id,
                    "general_budget_id": position.id,
                    "analytic_plan_id": plan.id,
                    "planned_amount": 1200.0,
                    "date_from": date(2026, 3, 1),
                    "date_to": date(2026, 6, 30),
                }
            )
            budgets |= budget
        table = export_table(
            "account.analytic.budget.report",
            {
                "domain": [("budget_id", "in", budgets.ids)],
                "facets": [],
                "panel": [],
            },
        )
        strings, _styles = self.export(table)

        for text in (
            "Budgets",
            "Export Budget A, Export Budget B",
            "03/01/2026 - 06/30/2026",
        ):
            self.assertIn(text, strings)
