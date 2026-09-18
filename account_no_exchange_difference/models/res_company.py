from odoo import models, fields


class Company(models.Model):
    _inherit = "res.company"

    exchange_difference_entry = fields.Boolean(default=True)
