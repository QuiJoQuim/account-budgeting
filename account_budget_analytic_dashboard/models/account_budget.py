# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.exceptions import ValidationError


class CrossoveredBudget(models.Model):
    _inherit = "crossovered.budget"

    def action_open_budget_report(self):
        """Budget vs actual of this budget, month by month."""
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "account_budget_analytic_dashboard.action_analytic_budget_report"
        )
        action["display_name"] = self.display_name
        action["context"] = {
            "searchpanel_default_budget_id": self.id,
            "pivot_column_groupby": ["date:month"],
        }
        return action

    def _check_disjoint_budget_positions(self):
        """The actual amounts are classified by budgetary position: within a
        budget, an account in two positions would be counted twice."""
        for budget in self:
            positions = budget.crossovered_budget_line_ids.general_budget_id
            seen = {}
            for position in positions:
                for account in position.account_ids:
                    if account in seen:
                        raise ValidationError(
                            self.env._(
                                "The budgetary positions of a budget cannot share "
                                "accounts.\n\nBudget: %(budget)s\nAccount: "
                                "%(account)s\nPositions: %(first)s, %(second)s",
                                budget=budget.display_name,
                                account=account.display_name,
                                first=seen[account].display_name,
                                second=position.display_name,
                            )
                        )
                    seen[account] = position


class CrossoveredBudgetLines(models.Model):
    _inherit = "crossovered.budget.lines"

    @api.constrains("general_budget_id", "crossovered_budget_id")
    def _check_disjoint_budget_positions(self):
        self.crossovered_budget_id._check_disjoint_budget_positions()


class AccountBudgetPost(models.Model):
    _inherit = "account.budget.post"

    @api.constrains("account_ids")
    def _check_disjoint_budget_positions(self):
        budgets = self.crossovered_budget_line_ids.crossovered_budget_id
        budgets._check_disjoint_budget_positions()
