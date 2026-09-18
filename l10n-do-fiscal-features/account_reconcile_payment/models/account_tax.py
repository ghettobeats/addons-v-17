#  Copyright (c) 2019 - Indexa SRL. (https://www.indexa.do) <info@indexa.do>
#  See LICENSE file for full licensing details.

from odoo import models, fields


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_do_reconcile_tax_base = fields.Selection(
        [("line_tax", "Line tax"), ("line_subtotal", "Line subtotal")],
        default="line_tax",
        help="Select base amount for reconcile taxes calculation",
    )
