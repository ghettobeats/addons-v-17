from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_do_sequence_manager = fields.Boolean(
        related="company_id.l10n_do_sequence_manager", readonly=False
    )
    l10n_do_sequence_left = fields.Integer(
        related="company_id.l10n_do_sequence_left", readonly=False
    )
    l10n_do_sequence_days_to_expire = fields.Integer(
        related="company_id.l10n_do_sequence_days_to_expire", readonly=False
    )
