# Copyright 2021-Present Indexa - Manuel Marquez <mmarquez@indexacorp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models, _


class generic_tax_report(models.AbstractModel):
    _inherit = "account.generic.tax.report"

    filter_tax_grids = None

    def _get_columns_name(self, options):
        res = super()._get_columns_name(options)
        for column_data in res:
            if isinstance(column_data.get("name"), str):
                column_data["name"] = column_data["name"].replace(
                    _("NET"), _("TAX BASE")
                )
        return res

    @api.model
    def _get_purchase_tax_lines(self, purchase_lines):
        total_purchase_tax_base = sum(
            [
                float(purchase_line["columns"][0]["name"].split()[1].replace(",", ""))
                for purchase_line in purchase_lines[1:]
            ]
        )
        total_purchase_tax = sum(
            [
                float(purchase_line["columns"][1]["name"].split()[1].replace(",", ""))
                for purchase_line in purchase_lines[1:]
            ]
        )
        total_purchase_columns = [
            {
                "name": self.format_value(total_purchase_tax_base),
                "style": "white-space:nowrap;",
            },
            {
                "name": self.format_value(total_purchase_tax),
                "style": "white-space:nowrap;",
            },
        ]
        purchase_lines.append(
            {
                "id": "purchase_total",
                "name": "Total",
                "unfoldable": False,
                "columns": total_purchase_columns,
                "level": 2,
            }
        )
        return purchase_lines

    def _get_lines_by_tax(self, options, line_id, taxes):
        lines = super()._get_lines_by_tax(options, line_id, taxes)
        sale_lines = []
        purchase_lines = []

        if lines and lines[0].get("id") == "sale":
            purchase_line_index = 0
            has_purchase_lines = False
            for line in lines:
                if line.get("id") == "purchase":
                    has_purchase_lines = True
                    break
                elif line.get("id") != "sale":
                    sale_lines.append(line)
                purchase_line_index += 1
            if has_purchase_lines:
                purchase_lines = lines[purchase_line_index + 1 :]
        elif lines and lines[0].get("id") == "purchase":
            purchase_lines = lines[1:]

        lines_with_totals = lines
        if sale_lines:
            lines_with_totals = [lines[0]] + sale_lines
            total_sale_tax_base = sum(
                [
                    float(sale_line["columns"][0]["name"].split()[1].replace(",", ""))
                    for sale_line in sale_lines
                ]
            )
            total_sale_tax = sum(
                [
                    float(sale_line["columns"][1]["name"].split()[1].replace(",", ""))
                    for sale_line in sale_lines
                ]
            )
            total_sales_columns = [
                {
                    "name": self.format_value(total_sale_tax_base),
                    "style": "white-space:nowrap;",
                },
                {
                    "name": self.format_value(total_sale_tax),
                    "style": "white-space:nowrap;",
                },
            ]
            lines_with_totals.append(
                {
                    "id": "sale_total",
                    "name": "Total",
                    "unfoldable": False,
                    "columns": total_sales_columns,
                    "level": 2,
                }
            )
            if purchase_lines:
                purchase_lines = [lines[purchase_line_index]] + purchase_lines
                lines_with_totals += self._get_purchase_tax_lines(purchase_lines)
        elif purchase_lines:
            purchase_lines = [lines[purchase_line_index]] + purchase_lines
            lines_with_totals += self._get_purchase_tax_lines(purchase_lines)

        return lines_with_totals
