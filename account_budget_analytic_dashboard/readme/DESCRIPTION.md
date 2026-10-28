This module compares the budgets of `account_budget_oca` with the actual
analytic amounts, month by month, over the whole analytic plan hierarchy.

## Plan budgets are envelopes

With `account_budget_analytic_plan`, a budget line can target an analytic plan
instead of an analytic account, for instance when the revenue expected from a
business line is known before its projects are. Such a budget line is an
**envelope**: the budget lines on the analytic accounts and on the subplans
below it, in the same budget and budgetary position, identify part of it
instead of adding up. The rest of the envelope shows as a **Pending to
identify** item of the plan.

So the budget of a plan is its envelope (or the sum of its content when it has
none) and nothing is counted twice. As projects get sold and budgeted, their
budget moves from the pending item to their account and the total of the plan
does not change. When the identified budget exceeds the envelope, the pending
item becomes negative.

## Budget and actual amounts

- The budget lines are spread over the months of their period in proportion to
  their days, as their theoretical amount.
- The actual amounts are the analytic lines counted by the analytic reports
  (see the personnel cost source of `account_analytic_dashboard`), classified
  by the budgetary positions of each budget: an analytic line belongs to the
  position holding its financial account, or to no position.
- Revenue and expenses follow the sign of the budget lines and of the analytic
  lines.

Within a budget, the budgetary positions cannot share financial accounts, or
the actual amounts would be counted twice. Different budgets can use different
positions.

## Reports

- **Accounting > Reporting > Budget vs Actual**: a pivot with the plan
  hierarchy down to the budget items in rows, and the budget, actual and
  deviation of each budget in columns.
- **Dashboards > Budget**: key figures against the budget, budget and actual by
  month, by line (first level of the project plan, with the revenue pending to
  identify) and by budgetary position. Filter it by budget: the figures of
  several budgets add up, and the dashboard warns about it.
