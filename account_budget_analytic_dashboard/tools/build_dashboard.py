"""Build ``data/files/budget_dashboard.json``, the analytic budget spreadsheet
dashboard.

The dashboard is generated instead of hand edited, so that its layout can be
changed and regenerated. Run it from anywhere:

    python3 account_budget_analytic_dashboard/tools/build_dashboard.py
"""

import json
from pathlib import Path

TARGET = Path(__file__).parent.parent / "data" / "files" / "budget_dashboard.json"
MODEL = "account.analytic.budget.report"
DOMAIN = [["analytic_plan_level_0_id", "!=", False]]
ACTION = "account_budget_analytic_dashboard.action_analytic_budget_report"
MENU = "account_budget_analytic_dashboard.menu_analytic_budget_report"
BUDGET_FILTER = "b1b2c3d4-0001-4a6e-9a51-6e7d0a7b0001"
PERIOD_FILTER = "b1b2c3d4-0002-4a6e-9a51-6e7d0a7b0002"
LINE_FILTER = "b1b2c3d4-0003-4a6e-9a51-6e7d0a7b0003"
LEVEL_1 = "analytic_plan_level_1_id"
MONTH = "#date:month"
MONTHS = 12
LINES = 15
POSITIONS = 10
BUDGETS = 5

FIELD_MATCHING = {
    BUDGET_FILTER: {"chain": "budget_id", "type": "many2one"},
    PERIOD_FILTER: {"chain": "date", "type": "date", "offset": 0},
    LINE_FILTER: {"chain": LEVEL_1, "type": "many2one"},
}
TITLE, HEADER, TOTAL, WARNING = 1, 2, 3, 4
AMOUNT, PERCENT = 1, 2
MEASURES = (
    "budget_revenue",
    "actual_revenue",
    "budget_expense",
    "actual_expense",
    "budget_amount",
    "actual_amount",
    "deviation_amount",
)


def col(index):
    return "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[index]


def text(value):
    return {"content": f'=_t("{value}")'}


def formula(value):
    return {"content": f"={value}"}


def header(value):
    """Pivot header, empty instead of an error out of the pivot range."""
    return formula(f'IFERROR({value},"")')


def guarded(condition_cells, value):
    """Value left empty when one of the given header cells is empty."""
    conditions = ",".join(f'{cell}=""' for cell in condition_cells)
    return formula(f'IF(OR({conditions}),"",{value})')


def pivot(pivot_id, name, rows=(), measures=MEASURES, domain=None, sorted_by=None):
    definition = {
        "type": "ODOO",
        "id": str(pivot_id),
        "formulaId": str(pivot_id),
        "name": name,
        "model": MODEL,
        "domain": domain or DOMAIN,
        "context": {},
        "rows": list(rows),
        "columns": [],
        "measures": [{"id": m, "fieldName": m} for m in measures],
        "fieldMatching": FIELD_MATCHING,
        "actionXmlId": ACTION,
    }
    if sorted_by:
        measure, order = sorted_by
        definition["sortedColumn"] = {
            "groupId": [[], []],
            "measure": measure,
            "order": order,
        }
    return definition


def scorecard(
    figure_id, x, title, key_cell, baseline_cell, mode="difference", inverse=False
):
    """Key figure against its budget. For costs (inverse), spending more than
    budgeted shows in red."""
    good, bad = "#00A04A", "#DC6965"
    return {
        "id": figure_id,
        "x": x,
        "y": 11,
        "width": 220,
        "height": 109,
        "tag": "chart",
        "data": {
            "type": "scorecard",
            "title": {"text": title, "color": "#434343", "bold": True},
            "keyValue": key_cell,
            "baseline": baseline_cell,
            "baselineMode": mode,
            "baselineDescr": "vs budget" if mode == "difference" else "",
            "background": "#FFFFFF",
            "humanize": False,
            "baselineColorUp": bad if inverse else good,
            "baselineColorDown": good if inverse else bad,
        },
    }


def sign_formats(ranges, prefix):
    return [
        {
            "id": f"{prefix}-{name}",
            "ranges": ranges,
            "rule": {
                "type": "CellIsRule",
                "operator": operator,
                "values": ["0"],
                "style": {"textColor": color},
            },
        }
        for name, operator, color in (
            ("positive", "GreaterThan", "#2E7D32"),
            ("negative", "LessThan", "#C62828"),
        )
    ]


def build():
    month_row = {"fieldName": "date", "granularity": "month", "order": "asc"}
    level_1_row = {"fieldName": LEVEL_1}
    pivots = {
        "1": pivot(1, "Totals"),
        "2": pivot(2, "By month", rows=[month_row]),
        "3": pivot(
            3, "By line", rows=[level_1_row], sorted_by=("budget_revenue", "desc")
        ),
        "4": pivot(
            4,
            "Pending by line",
            rows=[level_1_row],
            measures=("budget_revenue", "budget_expense"),
            domain=["&", *DOMAIN, ["is_pending", "=", True]],
        ),
        "5": pivot(
            5,
            "By position",
            rows=[{"fieldName": "position_id"}],
            measures=("budget_amount", "actual_amount", "deviation_amount"),
        ),
        "6": pivot(
            6, "Budgets", rows=[{"fieldName": "budget_id"}], measures=("budget_amount",)
        ),
    }

    # Data sheet: key figures, the monthly series and the number of budgets
    data = {
        "A1": text("Actual revenue"),
        "B1": formula('PIVOT.VALUE(1,"actual_revenue")'),
        "A2": text("Budget revenue"),
        "B2": formula('PIVOT.VALUE(1,"budget_revenue")'),
        "A3": text("Actual expenses"),
        "B3": formula('-PIVOT.VALUE(1,"actual_expense")'),
        "A4": text("Budget expenses"),
        "B4": formula('-PIVOT.VALUE(1,"budget_expense")'),
        "A5": text("Actual result"),
        "B5": formula('PIVOT.VALUE(1,"actual_amount")'),
        "A6": text("Budget result"),
        "B6": formula('PIVOT.VALUE(1,"budget_amount")'),
        "A7": text("Pending revenue"),
        "B7": formula('PIVOT.VALUE(4,"budget_revenue")'),
        "A8": text("Pending expenses"),
        "B8": formula('-PIVOT.VALUE(4,"budget_expense")'),
        "A12": text("Budgets"),
        "B12": formula(
            "+".join(
                f'IF(IFERROR(PIVOT.HEADER(6,"#budget_id",{n}),"")="",0,1)'
                for n in range(1, BUDGETS + 1)
            )
        ),
    }
    for row in range(1, 9):
        data[f"C{row}"] = formula(f"FORMAT.LARGE.NUMBER(B{row})")
    data["D7"] = formula('CONCAT(_t("Expenses: "),TEXT(B8,"#,##0"))')

    series_header = 14
    for index, title in enumerate(
        (
            "Month",
            "Actual revenue",
            "Actual expenses",
            "Budget revenue",
            "Budget expenses",
        )
    ):
        data[f"{col(index)}{series_header}"] = text(title)
    for n in range(1, MONTHS + 1):
        row = series_header + n
        data[f"A{row}"] = header(f'PIVOT.HEADER(2,"{MONTH}",{n})')
        for index, (sign, measure) in enumerate(
            (
                ("", "actual_revenue"),
                ("-", "actual_expense"),
                ("", "budget_revenue"),
                ("-", "budget_expense"),
            ),
            start=1,
        ):
            data[f"{col(index)}{row}"] = guarded(
                [f"A{row}"], f'{sign}PIVOT.VALUE(2,"{measure}","{MONTH}",{n})'
            )
    last_month_row = series_header + MONTHS

    cells, styles, formats, borders = {}, {}, {}, {}
    conditional_formats = []

    # Warning when the figures of several budgets add up
    cells["F7"] = formula(
        'IF(Data!B12>1,_t("Choose one budget in the Budget filter: '
        'the figures of several budgets add up."),"")'
    )
    styles["F7"] = WARNING

    cells["A7"] = text("Budget and actual by month")
    styles["A7"] = TITLE
    borders["A7:K7"] = 1

    # By line
    top = 23
    cells[f"A{top}"] = text("Budget and actual by line")
    styles[f"A{top}"] = TITLE
    borders[f"A{top}:K{top}"] = 1
    header_row = top + 1
    titles = (
        "Line",
        "Revenue budget",
        "Revenue",
        "Achieved",
        "Pending",
        "Expense budget",
        "Expenses",
        "Spent",
        "Result budget",
        "Result",
        "Deviation",
    )
    for index, title in enumerate(titles):
        cells[f"{col(index)}{header_row}"] = text(title)
    styles[f"A{header_row}:K{header_row}"] = HEADER
    first = header_row + 1
    for n in range(1, LINES + 1):
        row = header_row + n
        position = f'"#{LEVEL_1}",{n}'
        cells[f"A{row}"] = header(f"PIVOT.HEADER(3,{position})")

        def value(measure, sign="", pivot_id=3, row=row, position=position):
            return guarded(
                [f"A{row}"], f'{sign}PIVOT.VALUE({pivot_id},"{measure}",{position})'
            )

        cells[f"B{row}"] = value("budget_revenue")
        cells[f"C{row}"] = value("actual_revenue")
        cells[f"D{row}"] = formula(f'IF(OR(B{row}="",B{row}=0),"",IFERROR(C{row}/B{row},""))')
        cells[f"E{row}"] = guarded(
            [f"A{row}"],
            f'IFERROR(PIVOT.VALUE(4,"budget_revenue",{position}),0)',
        )
        cells[f"F{row}"] = value("budget_expense", "-")
        cells[f"G{row}"] = value("actual_expense", "-")
        cells[f"H{row}"] = formula(f'IF(OR(F{row}="",F{row}=0),"",IFERROR(G{row}/F{row},""))')
        cells[f"I{row}"] = value("budget_amount")
        cells[f"J{row}"] = value("actual_amount")
        cells[f"K{row}"] = value("deviation_amount")
    total = header_row + LINES + 1
    cells[f"A{total}"] = text("Total")
    for column, content in (
        ("B", 'PIVOT.VALUE(3,"budget_revenue")'),
        ("C", 'PIVOT.VALUE(3,"actual_revenue")'),
        ("D", f'IF(OR(B{total}="",B{total}=0),"",IFERROR(C{total}/B{total},""))'),
        ("E", 'IFERROR(PIVOT.VALUE(4,"budget_revenue"),0)'),
        ("F", '-PIVOT.VALUE(3,"budget_expense")'),
        ("G", '-PIVOT.VALUE(3,"actual_expense")'),
        ("H", f'IF(OR(F{total}="",F{total}=0),"",IFERROR(G{total}/F{total},""))'),
        ("I", 'PIVOT.VALUE(3,"budget_amount")'),
        ("J", 'PIVOT.VALUE(3,"actual_amount")'),
        ("K", 'PIVOT.VALUE(3,"deviation_amount")'),
    ):
        cells[f"{column}{total}"] = formula(content)
    styles[f"A{total}:K{total}"] = TOTAL
    borders[f"A{total}:K{total}"] = 2
    for columns in ("B{}:C{}", "E{}:G{}", "I{}:K{}"):
        formats[columns.format(first, total)] = AMOUNT
    for column in "DH":
        formats[f"{column}{first}:{column}{total}"] = PERCENT
    conditional_formats += sign_formats(
        [f"J{first}:K{total}"], "line"
    )

    # By budgetary position
    top = total + 3
    cells[f"A{top}"] = text("Budget and actual by budgetary position")
    styles[f"A{top}"] = TITLE
    borders[f"A{top}:E{top}"] = 1
    header_row = top + 1
    for index, title in enumerate(
        ("Budgetary position", "Budget", "Actual", "Deviation", "Achieved")
    ):
        cells[f"{col(index)}{header_row}"] = text(title)
    styles[f"A{header_row}:E{header_row}"] = HEADER
    first = header_row + 1
    for n in range(1, POSITIONS + 1):
        row = header_row + n
        position = f'"#position_id",{n}'
        cells[f"A{row}"] = header(f"PIVOT.HEADER(5,{position})")
        for column, measure in (
            ("B", "budget_amount"),
            ("C", "actual_amount"),
            ("D", "deviation_amount"),
        ):
            cells[f"{column}{row}"] = guarded(
                [f"A{row}"], f'PIVOT.VALUE(5,"{measure}",{position})'
            )
        cells[f"E{row}"] = formula(f'IF(OR(B{row}="",B{row}=0),"",IFERROR(C{row}/B{row},""))')
    last = header_row + POSITIONS
    formats[f"B{first}:D{last}"] = AMOUNT
    formats[f"E{first}:E{last}"] = PERCENT
    conditional_formats += sign_formats([f"D{first}:D{last}"], "position")
    last_row = last + 2

    chart_id = "b1b2c3d4-1000-4a6e-9a51-6e7d0a7b1000"
    figures = [
        scorecard(
            "b1b2c3d4-1001-4a6e-9a51-6e7d0a7b1001", 0, "Revenue", "Data!B1", "Data!B2"
        ),
        scorecard(
            "b1b2c3d4-1002-4a6e-9a51-6e7d0a7b1002",
            230,
            "Expenses",
            "Data!B3",
            "Data!B4",
            inverse=True,
        ),
        scorecard(
            "b1b2c3d4-1003-4a6e-9a51-6e7d0a7b1003", 460, "Result", "Data!B5", "Data!B6"
        ),
        scorecard(
            "b1b2c3d4-1004-4a6e-9a51-6e7d0a7b1004",
            690,
            "Pending to identify",
            "Data!B7",
            "Data!D7",
            mode="text",
        ),
        {
            "id": chart_id,
            "x": 0,
            "y": 178,
            "width": 1100,
            "height": 345,
            "tag": "chart",
            "data": {
                "type": "combo",
                "title": {"text": ""},
                "background": "#FFFFFF",
                "legendPosition": "top",
                "dataSetsHaveTitle": True,
                "dataSets": [
                    {
                        "dataRange": f"Data!B{series_header}:B{last_month_row}",
                        "type": "bar",
                    },
                    {
                        "dataRange": f"Data!C{series_header}:C{last_month_row}",
                        "type": "bar",
                    },
                    {
                        "dataRange": f"Data!D{series_header}:D{last_month_row}",
                        "type": "line",
                    },
                    {
                        "dataRange": f"Data!E{series_header}:E{last_month_row}",
                        "type": "line",
                    },
                ],
                "labelRange": f"Data!A{series_header + 1}:A{last_month_row}",
                "aggregated": False,
                "showValues": False,
            },
        },
    ]

    dashboard = {
        "version": 21,
        "odooVersion": 12,
        "revisionId": "START_REVISION",
        "uniqueFigureIds": True,
        "settings": {
            "locale": {
                "name": "English (US)",
                "code": "en_US",
                "thousandsSeparator": ",",
                "decimalSeparator": ".",
                "dateFormat": "mm/dd/yyyy",
                "timeFormat": "hh:mm:ss",
                "formulaArgSeparator": ",",
                "weekStart": 7,
            }
        },
        "styles": {
            str(TITLE): {"textColor": "#01666b", "bold": True, "fontSize": 16},
            str(HEADER): {"textColor": "#434343", "bold": True, "fontSize": 11},
            str(TOTAL): {"bold": True, "fillColor": "#f8f9fa"},
            str(WARNING): {"textColor": "#C62828", "bold": True},
        },
        "formats": {str(AMOUNT): "#,##0", str(PERCENT): "0.0%"},
        "borders": {
            "1": {"bottom": {"style": "thin", "color": "#CCCCCC"}},
            "2": {"top": {"style": "thin", "color": "#CCCCCC"}},
        },
        "customTableStyles": {},
        "pivots": pivots,
        "pivotNextId": len(pivots) + 1,
        "lists": {},
        "listNextId": 1,
        "globalFilters": [
            {
                "id": BUDGET_FILTER,
                "type": "relation",
                "label": "Budget",
                "modelName": "crossovered.budget",
                "defaultValue": [],
                "defaultValueDisplayNames": [],
            },
            {
                "id": PERIOD_FILTER,
                "type": "date",
                "label": "Period",
                "defaultValue": "year_to_date",
                "rangeType": "relative",
            },
            {
                "id": LINE_FILTER,
                "type": "relation",
                "label": "Line",
                "modelName": "account.analytic.plan",
                "defaultValue": [],
                "defaultValueDisplayNames": [],
            },
        ],
        "chartOdooMenusReferences": {chart_id: MENU},
        "sheets": [
            sheet(
                "dashboard",
                "Dashboard",
                cells,
                styles=styles,
                formats=formats,
                borders=borders,
                figures=figures,
                conditional_formats=conditional_formats,
                rows=last_row,
                cols={
                    "0": {"size": 220},
                    **{str(i): {"size": 105} for i in range(1, 11)},
                },
                row_sizes={"6": {"size": 40}},
            ),
            sheet(
                "data",
                "Data",
                data,
                formats={
                    "B1:B8": AMOUNT,
                    f"B{series_header + 1}:E{last_month_row}": AMOUNT,
                },
                rows=last_month_row + 2,
                visible=False,
            ),
        ],
    }
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(dashboard, indent=1, ensure_ascii=False) + "\n")


def sheet(
    sheet_id,
    name,
    cells,
    styles=None,
    formats=None,
    borders=None,
    figures=None,
    conditional_formats=None,
    rows=50,
    cols=None,
    row_sizes=None,
    visible=True,
):
    return {
        "id": sheet_id,
        "name": name,
        "colNumber": 26,
        "rowNumber": rows,
        "rows": row_sizes or {},
        "cols": cols or {},
        "merges": [],
        "cells": cells,
        "styles": styles or {},
        "formats": formats or {},
        "borders": borders or {},
        "conditionalFormats": conditional_formats or [],
        "figures": figures or [],
        "tables": [],
        "areGridLinesVisible": False,
        "isVisible": visible,
        "headerGroups": {"ROW": [], "COL": []},
        "dataValidationRules": [],
        "comments": {},
    }


if __name__ == "__main__":
    build()
