# Copyright (C) 2026
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class CrossoveredBudgetLines(models.Model):
    _inherit = "crossovered.budget.lines"

    analytic_plan_id = fields.Many2one(
        comodel_name="account.analytic.plan",
        string="Analytic Plan",
    )

    @api.constrains("analytic_account_id", "analytic_plan_id")
    def _check_analytic_account_or_plan(self):
        for line in self:
            if line.analytic_account_id and line.analytic_plan_id:
                raise ValidationError(
                    _(
                        "A budget line cannot be linked to both an analytic "
                        "account and an analytic plan."
                    )
                )

    @api.depends(
        "general_budget_id.account_ids",
        "date_from",
        "date_to",
        "analytic_account_id",
        "analytic_plan_id",
    )
    def _compute_practical_amount(self):
        account_lines = self.filtered(lambda line: not line.analytic_plan_id)
        super(CrossoveredBudgetLines, account_lines)._compute_practical_amount()

        for line in self - account_lines:
            result = 0.0
            account_ids = line.general_budget_id.account_ids.ids
            date_from = line.date_from
            date_to = line.date_to
            if line.analytic_plan_id and date_from and date_to and account_ids:
                plan_ids = self.env["account.analytic.plan"].search(
                    [("id", "child_of", line.analytic_plan_id.id)]
                ).ids
                self.env.cr.execute(
                    """
                    SELECT SUM(aal.amount)
                      FROM account_analytic_line aal
                      JOIN account_analytic_account aaa
                        ON aal.account_id = aaa.id
                     WHERE aaa.plan_id = ANY(%s)
                       AND aal.date BETWEEN %s AND %s
                       AND aal.general_account_id = ANY(%s)
                    """,
                    (plan_ids, date_from, date_to, account_ids),
                )
                result = self.env.cr.fetchone()[0] or 0.0
            line.practical_amount = result
