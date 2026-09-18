from odoo import models, fields


class Banks(models.Model):
    _inherit = "res.bank"

    l10n_do_bhd_bank_code = fields.Char("BHD Bank Code")
