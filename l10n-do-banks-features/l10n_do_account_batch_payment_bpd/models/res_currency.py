from odoo import models, fields


class Currency(models.Model):
    _inherit = "res.currency"

    l10n_do_bpd_currency_code = fields.Integer("BPD Currency Code")
