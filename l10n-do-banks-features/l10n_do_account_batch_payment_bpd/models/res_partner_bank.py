from odoo import models, fields


class ResPartnerBank(models.Model):
    _inherit = "res.bank"

    l10n_do_bpd_bank_code = fields.Char(string="Bank Code")
    l10n_do_bpd_digiver_code = fields.Integer(string="Digit Destiny Bank")
