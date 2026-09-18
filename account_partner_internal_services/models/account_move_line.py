# Copyright 2020-Present Indexa - Manuel Marquez <mmarquez@indexacorp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_computed_account(self):
        computed_account = super()._get_computed_account()
        if (
            self.move_id.partner_id.internal_services
            and self.move_id.is_sale_document(include_receipts=True)
            and self.product_id.categ_id.internal_services_income_account_id
        ):
            return self.product_id.categ_id.internal_services_income_account_id
        return computed_account
