# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo.tools import SQL

PLAN_LEVELS = 5


class AccountAnalyticBudgetReport(models.Model):
    """Budget against actual of the analytic plan hierarchy, month by month.

    A budget line on an analytic plan is an envelope: the budget lines on the
    accounts and on the plans below it identify part of it instead of adding
    up. The rest of the envelope shows as a "Pending to identify" item, so that
    the budget of a plan is its envelope (or the sum of its content when it has
    none) and nothing is counted twice.

    The budget lines are spread over the months of their period in proportion
    to their days, as their theoretical amount. The actual amounts are the
    analytic lines counted by the analytic reports, classified by the
    budgetary positions of each budget."""

    _name = "account.analytic.budget.report"
    _description = "Analytic Budget vs Actual"
    _auto = False
    _order = "date, id"

    budget_id = fields.Many2one("crossovered.budget", string="Budget", readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    currency_id = fields.Many2one(related="company_id.currency_id")
    date = fields.Date(readonly=True)
    position_id = fields.Many2one(
        "account.budget.post", string="Budgetary Position", readonly=True
    )
    analytic_plan_id = fields.Many2one(
        "account.analytic.plan", string="Analytic Plan", readonly=True
    )
    analytic_plan_level_0_id = fields.Many2one(
        "account.analytic.plan", string="Analytic Plan (Root)", readonly=True
    )
    analytic_plan_level_1_id = fields.Many2one(
        "account.analytic.plan", string="Analytic Plan (Level 1)", readonly=True
    )
    analytic_plan_level_2_id = fields.Many2one(
        "account.analytic.plan", string="Analytic Plan (Level 2)", readonly=True
    )
    analytic_plan_level_3_id = fields.Many2one(
        "account.analytic.plan", string="Analytic Plan (Level 3)", readonly=True
    )
    analytic_plan_level_4_id = fields.Many2one(
        "account.analytic.plan", string="Analytic Plan (Level 4)", readonly=True
    )
    account_id = fields.Many2one(
        "account.analytic.account", string="Analytic Account", readonly=True
    )
    item = fields.Char(string="Budget Item", readonly=True)
    is_pending = fields.Boolean(string="Pending to Identify", readonly=True)
    budget_amount = fields.Monetary(string="Budget", readonly=True)
    actual_amount = fields.Monetary(string="Actual", readonly=True)
    deviation_amount = fields.Monetary(string="Deviation", readonly=True)
    budget_revenue = fields.Monetary(string="Budget Revenue", readonly=True)
    budget_expense = fields.Monetary(string="Budget Expenses", readonly=True)
    actual_revenue = fields.Monetary(string="Actual Revenue", readonly=True)
    actual_expense = fields.Monetary(string="Actual Expenses", readonly=True)

    def _get_plan_levels(self):
        """Plan of each level from the root, empty when the plan is not shown in
        the analytic search panel, as on the analytic lines."""
        return SQL(", ").join(
            SQL(
                "CASE WHEN plan.show_in_analytic_searchpanel THEN NULLIF("
                "split_part(plan.parent_path, '/', %s), '')::int END AS %s",
                level + 1,
                SQL.identifier(f"analytic_plan_level_{level}_id"),
            )
            for level in range(PLAN_LEVELS)
        )

    @property
    def _table_query(self):
        # Only the lines the user can read: the record rules do not apply to
        # the SQL view.
        budget_lines = self.env["crossovered.budget.lines"]._search([])
        actual_lines = self.env["account.analytic.line"]._search(
            [("account_id", "!=", False), ("analytic_report_included", "=", True)]
        )
        lang = self.env.lang or "en_US"
        return SQL(
            """
            WITH
            budget_line AS (
                SELECT
                    line.id,
                    line.crossovered_budget_id AS budget_id,
                    budget.company_id,
                    line.general_budget_id AS position_id,
                    line.analytic_account_id AS account_id,
                    COALESCE(line.analytic_plan_id, account.plan_id) AS plan_id,
                    line.analytic_plan_id IS NOT NULL AS is_envelope,
                    line.planned_amount > 0 AS is_revenue,
                    line.date_from,
                    line.date_to,
                    line.planned_amount::numeric AS planned_amount
                FROM crossovered_budget_lines line
                JOIN crossovered_budget budget
                    ON budget.id = line.crossovered_budget_id
                LEFT JOIN account_analytic_account account
                    ON account.id = line.analytic_account_id
                WHERE line.id IN %(budget_lines)s
                    AND line.date_to >= line.date_from
                    AND (
                        line.analytic_account_id IS NOT NULL
                        OR line.analytic_plan_id IS NOT NULL
                    )
            ),
            -- Spread over the months in proportion to the days
            budget_month AS (
                SELECT
                    line.id AS line_id,
                    month::date AS date,
                    line.planned_amount
                    * (
                        LEAST(
                            line.date_to,
                            (month + INTERVAL '1 month - 1 day')::date
                        )
                        - GREATEST(line.date_from, month::date)
                        + 1
                    )
                    / (line.date_to - line.date_from + 1) AS amount
                FROM budget_line line
                CROSS JOIN generate_series(
                    date_trunc('month', line.date_from),
                    line.date_to,
                    INTERVAL '1 month'
                ) AS month
            ),
            -- Closest envelope above every budget line, in the same budget and
            -- budgetary position
            budget_envelope AS (
                SELECT
                    line.id AS line_id,
                    (
                        SELECT envelope.plan_id
                        FROM budget_line envelope
                        JOIN account_analytic_plan envelope_plan
                            ON envelope_plan.id = envelope.plan_id
                        WHERE envelope.is_envelope
                            AND envelope.budget_id = line.budget_id
                            AND envelope.position_id = line.position_id
                            AND plan.parent_path LIKE envelope_plan.parent_path || %(wildcard)s
                            AND (NOT line.is_envelope OR envelope.plan_id != line.plan_id)
                        ORDER BY length(envelope_plan.parent_path) DESC
                        LIMIT 1
                    ) AS plan_id
                FROM budget_line line
                JOIN account_analytic_plan plan ON plan.id = line.plan_id
            ),
            budget_position AS (
                SELECT DISTINCT budget_id, position_id FROM budget_line
            ),
            report_row AS (
                -- Budget of the accounts
                SELECT
                    line.budget_id, line.company_id, line.position_id, month.date,
                    line.plan_id, line.account_id, FALSE AS is_pending,
                    line.is_revenue, month.amount AS budget_amount,
                    0.0 AS actual_amount
                FROM budget_line line
                JOIN budget_month month ON month.line_id = line.id
                WHERE NOT line.is_envelope

                UNION ALL

                -- Envelopes of the plans
                SELECT
                    line.budget_id, line.company_id, line.position_id, month.date,
                    line.plan_id, NULL, TRUE, line.is_revenue, month.amount, 0.0
                FROM budget_line line
                JOIN budget_month month ON month.line_id = line.id
                WHERE line.is_envelope

                UNION ALL

                -- What is identified below an envelope is not pending any more
                SELECT
                    line.budget_id, line.company_id, line.position_id, month.date,
                    envelope.plan_id, NULL, TRUE, line.is_revenue, -month.amount, 0.0
                FROM budget_line line
                JOIN budget_month month ON month.line_id = line.id
                JOIN budget_envelope envelope ON envelope.line_id = line.id
                WHERE envelope.plan_id IS NOT NULL

                UNION ALL

                -- Actual amounts, for every budget covering their date
                SELECT
                    budget.id, analytic_line.company_id,
                    (
                        SELECT position.position_id
                        FROM budget_position position
                        JOIN account_budget_rel rel
                            ON rel.budget_id = position.position_id
                        WHERE position.budget_id = budget.id
                            AND rel.account_id = analytic_line.general_account_id
                        LIMIT 1
                    ),
                    date_trunc('month', analytic_line.date)::date,
                    account.plan_id, analytic_line.account_id, FALSE,
                    analytic_line.amount > 0, 0.0, analytic_line.amount
                FROM account_analytic_line analytic_line
                JOIN crossovered_budget budget
                    ON budget.company_id = analytic_line.company_id
                    AND analytic_line.date
                        BETWEEN budget.date_from AND budget.date_to
                JOIN account_analytic_account account
                    ON account.id = analytic_line.account_id
                WHERE analytic_line.id IN %(actual_lines)s
                    AND budget.id IN (SELECT budget_id FROM budget_line)
            )
            SELECT
                -- Stable ids: the grouped columns identify the rows
                row_number() OVER (
                    ORDER BY row.date, row.budget_id, row.position_id NULLS FIRST,
                        row.plan_id, row.account_id NULLS FIRST, row.is_pending
                ) AS id,
                row.budget_id,
                row.company_id,
                row.position_id,
                row.date,
                row.plan_id AS analytic_plan_id,
                %(plan_levels)s,
                row.account_id,
                CASE
                    WHEN row.is_pending THEN %(pending)s
                    ELSE CONCAT(
                        '[' || account.code || '] ',
                        COALESCE(account.name->>%(lang)s, account.name->>'en_US')
                    )
                END AS item,
                row.is_pending,
                SUM(row.budget_amount) AS budget_amount,
                SUM(row.actual_amount) AS actual_amount,
                SUM(row.actual_amount) - SUM(row.budget_amount) AS deviation_amount,
                COALESCE(SUM(row.budget_amount) FILTER (WHERE row.is_revenue), 0.0)
                    AS budget_revenue,
                COALESCE(SUM(row.budget_amount) FILTER (WHERE NOT row.is_revenue), 0.0)
                    AS budget_expense,
                COALESCE(SUM(row.actual_amount) FILTER (WHERE row.is_revenue), 0.0)
                    AS actual_revenue,
                COALESCE(SUM(row.actual_amount) FILTER (WHERE NOT row.is_revenue), 0.0)
                    AS actual_expense
            FROM report_row row
            JOIN account_analytic_plan plan ON plan.id = row.plan_id
            LEFT JOIN account_analytic_account account ON account.id = row.account_id
            GROUP BY
                row.budget_id, row.company_id, row.position_id, row.date,
                row.plan_id, plan.parent_path, plan.show_in_analytic_searchpanel,
                row.account_id, account.code, account.name, row.is_pending
            """,
            budget_lines=budget_lines.subselect(),
            actual_lines=actual_lines.subselect(),
            plan_levels=self._get_plan_levels(),
            pending=self.env._("Pending to identify"),
            wildcard="%",
            lang=lang,
        )
