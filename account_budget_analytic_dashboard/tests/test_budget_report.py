# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBudgetReport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Dedicated company, so that other data does not get in the report
        cls.company = cls.env["res.company"].create({"name": "Budget Company"})
        cls.env.user.company_ids |= cls.company
        cls.env = cls.env(
            context=dict(cls.env.context, allowed_company_ids=[cls.company.id])
        )
        cls.Report = cls.env["account.analytic.budget.report"]
        Plan = cls.env["account.analytic.plan"]
        cls.root, _other_plans = Plan._get_all_plans()
        cls.odoo = Plan.create({"name": "Budget Odoo", "parent_id": cls.root.id})
        cls.odoo_dev = Plan.create(
            {"name": "Budget Odoo Developments", "parent_id": cls.odoo.id}
        )
        Account = cls.env["account.analytic.account"]
        cls.project_x = Account.create(
            {"name": "Project X", "plan_id": cls.odoo.id, "company_id": cls.company.id}
        )
        cls.project_y = Account.create(
            {
                "name": "Project Y",
                "plan_id": cls.odoo_dev.id,
                "company_id": cls.company.id,
            }
        )
        GeneralAccount = cls.env["account.account"].with_company(cls.company)
        cls.sales_account = GeneralAccount.create(
            {"name": "Sales", "code": "700100", "account_type": "income"}
        )
        cls.payroll_account = GeneralAccount.create(
            {"name": "Salaries", "code": "640100", "account_type": "expense"}
        )
        cls.other_account = GeneralAccount.create(
            {"name": "Other", "code": "629100", "account_type": "expense"}
        )
        Position = cls.env["account.budget.post"]
        cls.sales = Position.create(
            {
                "name": "Sales",
                "account_ids": [(6, 0, cls.sales_account.ids)],
                "company_id": cls.company.id,
            }
        )
        cls.payroll = Position.create(
            {
                "name": "Payroll",
                "account_ids": [(6, 0, cls.payroll_account.ids)],
                "company_id": cls.company.id,
            }
        )
        cls.budget = cls._create_budget("Budget 2026")

    @classmethod
    def _create_budget(cls, name):
        return cls.env["crossovered.budget"].create(
            {
                "name": name,
                "date_from": date(2026, 1, 1),
                "date_to": date(2026, 12, 31),
                "company_id": cls.company.id,
            }
        )

    def _budget_line(self, amount, position, plan=None, account=None, budget=None,
                     date_from=date(2026, 1, 1), date_to=date(2026, 12, 31)):
        return self.env["crossovered.budget.lines"].create(
            {
                "crossovered_budget_id": (budget or self.budget).id,
                "general_budget_id": position.id,
                "analytic_plan_id": plan.id if plan else False,
                "analytic_account_id": account.id if account else False,
                "planned_amount": amount,
                "date_from": date_from,
                "date_to": date_to,
            }
        )

    def _actual(self, amount, account, general_account=None, line_date=date(2026, 3, 10)):
        return self.env["account.analytic.line"].create(
            {
                "name": "Actual",
                "account_id": account.id,
                "amount": amount,
                "date": line_date,
                "company_id": self.company.id,
                "general_account_id": general_account.id if general_account else False,
            }
        )

    def _sum(self, field, domain=None):
        self.env.flush_all()
        # The report is a view: its rows change with the data and the settings
        self.Report.invalidate_model()
        rows = self.Report.search(domain or [])
        return sum(rows.mapped(field))

    def test_plan_budget_is_an_envelope(self):
        self._budget_line(1200.0, self.sales, plan=self.odoo)
        self._budget_line(
            300.0, self.sales, account=self.project_x,
            date_from=date(2026, 3, 1), date_to=date(2026, 5, 31),
        )

        # The identified project is part of the envelope, not added to it
        self.assertAlmostEqual(self._sum("budget_amount"), 1200.0)
        self.assertAlmostEqual(
            self._sum("budget_amount", [("is_pending", "=", True)]), 900.0
        )
        self.assertAlmostEqual(
            self._sum("budget_amount", [("account_id", "=", self.project_x.id)]), 300.0
        )
        self.assertAlmostEqual(self._sum("budget_revenue"), 1200.0)
        self.assertAlmostEqual(self._sum("budget_expense"), 0.0)

    def test_budget_is_spread_by_month(self):
        self._budget_line(1200.0, self.sales, plan=self.odoo)
        self._budget_line(
            300.0, self.sales, account=self.project_x,
            date_from=date(2026, 3, 1), date_to=date(2026, 5, 31),
        )
        january = [("date", "=", date(2026, 1, 1))]
        march = [("date", "=", date(2026, 3, 1))]

        self.assertAlmostEqual(
            self._sum("budget_amount", january), 1200.0 * 31 / 365
        )
        self.assertAlmostEqual(
            self._sum("budget_amount", march), 1200.0 * 31 / 365
        )
        self.assertAlmostEqual(
            self._sum("budget_amount", march + [("account_id", "=", self.project_x.id)]),
            300.0 * 31 / 92,
        )

    def test_nested_envelopes_are_not_counted_twice(self):
        self._budget_line(1000.0, self.sales, plan=self.odoo)
        self._budget_line(400.0, self.sales, plan=self.odoo_dev)
        self._budget_line(100.0, self.sales, account=self.project_y)

        self.assertAlmostEqual(self._sum("budget_amount"), 1000.0)
        dev = [("analytic_plan_level_2_id", "=", self.odoo_dev.id)]
        self.assertAlmostEqual(self._sum("budget_amount", dev), 400.0)
        self.assertAlmostEqual(
            self._sum(
                "budget_amount",
                [("is_pending", "=", True), ("analytic_plan_id", "=", self.odoo.id)],
            ),
            600.0,
        )

    def test_identifying_more_than_the_envelope_leaves_negative_pending(self):
        self._budget_line(100.0, self.sales, plan=self.odoo)
        self._budget_line(150.0, self.sales, account=self.project_x)

        self.assertAlmostEqual(self._sum("budget_amount"), 100.0)
        self.assertAlmostEqual(
            self._sum("budget_amount", [("is_pending", "=", True)]), -50.0
        )
        # Still revenue, it comes from revenue budget lines
        self.assertAlmostEqual(self._sum("budget_revenue"), 100.0)

    def test_envelopes_are_per_position(self):
        self._budget_line(1000.0, self.sales, plan=self.odoo)
        self._budget_line(-200.0, self.payroll, account=self.project_x)

        self.assertAlmostEqual(self._sum("budget_revenue"), 1000.0)
        self.assertAlmostEqual(self._sum("budget_expense"), -200.0)
        self.assertAlmostEqual(
            self._sum("budget_amount", [("is_pending", "=", True)]), 1000.0
        )

    def test_actual_is_classified_by_position(self):
        self._budget_line(1000.0, self.sales, plan=self.odoo)
        self._budget_line(-500.0, self.payroll, plan=self.odoo)
        self._actual(300.0, self.project_x, self.sales_account)
        self._actual(-80.0, self.project_x, self.payroll_account)
        self._actual(-20.0, self.project_y, self.other_account)
        # Timesheet: no financial account, ignored by default
        self._actual(-50.0, self.project_x)

        self.assertAlmostEqual(self._sum("actual_amount"), 200.0)
        self.assertAlmostEqual(
            self._sum("actual_amount", [("position_id", "=", self.sales.id)]), 300.0
        )
        self.assertAlmostEqual(
            self._sum("actual_amount", [("position_id", "=", self.payroll.id)]), -80.0
        )
        self.assertAlmostEqual(
            self._sum("actual_amount", [("position_id", "=", False)]), -20.0
        )
        self.assertAlmostEqual(self._sum("actual_revenue"), 300.0)
        self.assertAlmostEqual(self._sum("actual_expense"), -100.0)

        self.company.analytic_report_personnel_cost = "all"
        self.assertAlmostEqual(self._sum("actual_amount"), 150.0)

    def test_each_budget_is_compared_on_its_own(self):
        revised = self._create_budget("Budget 2026 revised")
        self._budget_line(1000.0, self.sales, plan=self.odoo)
        self._budget_line(1500.0, self.sales, plan=self.odoo, budget=revised)
        self._actual(300.0, self.project_x, self.sales_account)

        for budget, amount in ((self.budget, 1000.0), (revised, 1500.0)):
            domain = [("budget_id", "=", budget.id)]
            self.assertAlmostEqual(self._sum("budget_amount", domain), amount)
            self.assertAlmostEqual(self._sum("actual_amount", domain), 300.0)

    def test_budget_positions_cannot_share_accounts(self):
        self._budget_line(1000.0, self.sales, plan=self.odoo)
        overlapping = self.env["account.budget.post"].create(
            {
                "name": "Sales and payroll",
                "account_ids": [
                    (6, 0, (self.sales_account + self.payroll_account).ids)
                ],
                "company_id": self.company.id,
            }
        )
        with self.assertRaises(ValidationError):
            self._budget_line(-100.0, overlapping, plan=self.odoo)
        # Fine in another budget
        self._budget_line(
            -100.0, overlapping, plan=self.odoo, budget=self._create_budget("Other")
        )
        self._budget_line(-100.0, self.payroll, plan=self.odoo)
        with self.assertRaises(ValidationError):
            self.payroll.account_ids |= self.sales_account

    def test_budget_opens_its_report(self):
        action = self.budget.action_open_budget_report()

        self.assertEqual(action["res_model"], "account.analytic.budget.report")
        self.assertEqual(
            action["context"]["searchpanel_default_budget_id"], self.budget.id
        )
