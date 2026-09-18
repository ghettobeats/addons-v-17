from odoo import models, fields, _


class ResCompany(models.Model):
    _inherit = "res.company"

    create_statement_draft = fields.Boolean(string="Create Bank Statement in Draft State")
