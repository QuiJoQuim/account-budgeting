# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo.http import request
from odoo.tools.misc import format_date

from odoo.addons.account_analytic_searchpanel.controllers.main import (
    AnalyticPivotExporter,
)

BUDGET_REPORT = "account.analytic.budget.report"


class BudgetPivotExporter(AnalyticPivotExporter):
    def _get_export_info(self, jdata):
        lines = super()._get_export_info(jdata)
        if jdata.get("model") == BUDGET_REPORT:
            # Right after who exported it and when
            lines.insert(1, (request.env._("Budgets"), self._get_export_budgets(jdata)))
        return lines

    def _get_export_budgets(self, jdata):
        """The budgets the exported data comes from."""
        model, domain = self._get_export_records(jdata)
        budgets = model._read_group(domain, groupby=["budget_id"])
        return ", ".join(budget.display_name for (budget,) in budgets if budget)

    def _get_export_period(self, jdata):
        if jdata.get("model") != BUDGET_REPORT:
            return super()._get_export_period(jdata)
        # The report is by month: its dates are the first day of each month
        model, domain = self._get_export_records(jdata)
        [(date_from, date_to)] = model._read_group(
            domain, aggregates=["date:min", "date:max"]
        )
        if not date_from:
            return ""
        env = request.env
        date_to += relativedelta(months=1, days=-1)
        return f"{format_date(env, date_from)} - {format_date(env, date_to)}"
