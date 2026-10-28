# Copyright (C) 2026
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, fields, models


class AccountAnalyticPlan(models.Model):
    _inherit = "account.analytic.plan"

    budget_line_ids = fields.One2many(
        comodel_name="crossovered.budget.lines",
        inverse_name="analytic_plan_id",
        string="Budget Lines",
    )
    budget_line_count = fields.Integer(compute="_compute_budget_amounts")
    budget_planned_amount = fields.Float(compute="_compute_budget_amounts")
    budget_practical_amount = fields.Float(compute="_compute_budget_amounts")
    budget_theoretical_amount = fields.Float(compute="_compute_budget_amounts")
    budget_percentage = fields.Float(
        string="Budget Achievement",
        compute="_compute_budget_amounts",
    )

    def _compute_budget_amounts(self):
        for plan in self:
            lines = plan.budget_line_ids
            planned_amount = sum(lines.mapped("planned_amount"))
            practical_amount = sum(lines.mapped("practical_amount"))
            theoretical_amount = sum(lines.mapped("theoretical_amount"))
            plan.budget_line_count = len(lines)
            plan.budget_planned_amount = planned_amount
            plan.budget_practical_amount = practical_amount
            plan.budget_theoretical_amount = theoretical_amount
            plan.budget_percentage = (
                practical_amount / theoretical_amount * 100
                if theoretical_amount
                else 0.0
            )

    def action_view_budget_lines(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Budget Lines"),
            "res_model": "crossovered.budget.lines",
            "view_mode": "list,form",
            "domain": [("analytic_plan_id", "=", self.id)],
            "context": {
                "default_analytic_plan_id": self.id,
                "search_default_group_by_budget": 1,
            },
        }
