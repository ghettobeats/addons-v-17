from odoo import models, fields


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    account_type = fields.Selection(
        [("cheque", "Check account"), ("savings", "Savings account")],
        string="Account type",
        default="cheque",
    )
