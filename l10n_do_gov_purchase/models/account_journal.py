from odoo import models, fields


class AccountJournal(models.Model):
    _inherit = "account.journal"

    allow_check_release = fields.Boolean(string="Allow check release",)
