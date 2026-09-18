#  Copyright (c) 2019 - Indexa SRL. (https://www.indexa.do) <info@indexa.do>
#  See LICENSE file for full licensing details.

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_do_withholding_cert_type = fields.Selection(
        [("private", "Private Company"), ("gov", "Public Sector")],
        string="Certification Type",
        default="private",
    )
    l10n_do_show_header = fields.Boolean(
        default=True,
    )
    l10n_do_show_footer = fields.Boolean(
        default=True,
    )
    l10n_do_year_tag_line = fields.Html()
    l10n_do_sign_table = fields.Html()
