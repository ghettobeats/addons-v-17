# Copyright 2020-Present Indexa - Manuel Marquez <mmarquez@indexacorp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def get_product_accounts(self, fiscal_pos=None):
        res = super().get_product_accounts(fiscal_pos=fiscal_pos)
        if self.env.context.get("move_type") == "out_invoice" and self.env.context.get(
            "partner_internal_services"
        ):
            if self.categ_id.internal_services_expense_account_id:
                res["expense"] = self.categ_id.internal_services_expense_account_id
        return res
