from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    is_for_payroll = fields.Boolean(string="Payroll",)
