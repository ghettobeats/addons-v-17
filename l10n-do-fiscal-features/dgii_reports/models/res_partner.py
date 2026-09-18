# Part of Domincana Premium.
# See LICENSE file for full copyright and licensing details.
# © 2018 José López <jlopez@indexa.do>

from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_do_related = fields.Selection(
        string="Related",
        selection=[("0", "Not Related"), ("1", "Related")],
        default="0",
    )
