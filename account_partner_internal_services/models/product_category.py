# Copyright 2020-Present Indexa - Manuel Marquez <mmarquez@indexacorp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    internal_services_income_account_id = fields.Many2one(
        "account.account",
        company_dependent=True,
        string="Income Account (Internal Services)",
        domain="['&', ('deprecated', '=', False), ('company_id', '=', current_company_id)]",
        help="This account will be used when validating a customer invoice "
        "from a contact marked as internal services.",
    )
    internal_services_expense_account_id = fields.Many2one(
        "account.account",
        company_dependent=True,
        string="Expense Account (Internal Services)",
        domain="['&', ('deprecated', '=', False), ('company_id', '=', current_company_id)]",
        help="This account will be used when validating a supplier invoice "
        "from a contact marked as internal services.",
    )
