from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    exchange_difference_entry = fields.Boolean(
        related="company_id.exchange_difference_entry",
        readonly=False,
    )
