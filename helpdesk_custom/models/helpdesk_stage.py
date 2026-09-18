from odoo import models, fields, api

class HelpdeskStage(models.Model):
    _inherit = "helpdesk.stage"

    # Field to mark a stage as the final one
    isFinalStage = fields.Boolean(
        string='Etapa final',
        required=False)