# Copyright 2020-Present Indexa - Manuel Marquez <mmarquez@indexacorp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    stock_move_origin_id = fields.Many2one(
        "stock.move",
        "Stock Move Origin",
        help="Technical field to know the stock move that origined this COGS move line.",
    )
