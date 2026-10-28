# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json

from odoo.tests import HttpCase, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBudgetDashboard(TransactionCase):
    def test_dashboard_only_uses_existing_fields(self):
        """A missing field only shows up as #ERROR cells in the dashboard."""
        dashboard = self.env.ref(
            "account_budget_analytic_dashboard.dashboard_analytic_budget"
        )
        data = json.loads(base64.b64decode(dashboard.spreadsheet_binary_data))
        action = self.env.ref(
            "account_budget_analytic_dashboard.action_analytic_budget_report"
        )
        for pivot in data["pivots"].values():
            fields = self.env[pivot["model"]]._fields
            used = (
                [dimension["fieldName"] for dimension in pivot["rows"]]
                + [dimension["fieldName"] for dimension in pivot["columns"]]
                + [measure["fieldName"] for measure in pivot["measures"]]
                + [leaf[0] for leaf in pivot["domain"] if isinstance(leaf, list)]
                + [match["chain"] for match in pivot["fieldMatching"].values()]
            )
            for fname in used:
                self.assertIn(fname, fields, f"Pivot {pivot['name']}: {fname}")
            self.assertEqual(self.env.ref(pivot["actionXmlId"]), action)


@tagged("post_install", "-at_install")
class TestBudgetDashboardTour(HttpCase):
    def test_dashboard_renders(self):
        self.env.ref("base.user_admin").groups_id += self.env.ref(
            "account.group_account_user"
        ) + self.env.ref("analytic.group_analytic_accounting")
        self.start_tour(
            "/odoo/action-spreadsheet_dashboard.ir_actions_dashboard_action",
            "budget_dashboard_tour",
            login="admin",
        )
