from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    national_provider_registry = fields.Char(string="National Provider Registry",)
