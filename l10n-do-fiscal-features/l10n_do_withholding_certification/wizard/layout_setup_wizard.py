#  Copyright (c) 2019 - Indexa SRL. (https://www.indexa.do) <info@indexa.do>
#  See LICENSE file for full licensing details.

from odoo import models, fields


class WithholdingLayoutSetupWizard(models.TransientModel):
    _name = "withholding.layout.setup.wizard"
    _description = "Withholding Layout Setup Wizard"

    company_id = fields.Many2one(
        "res.company",
        "Company",
        required=True,
    )
    l10n_do_withholding_cert_type = fields.Selection(
        related="company_id.l10n_do_withholding_cert_type",
        readonly=False,
    )
    l10n_do_show_header = fields.Boolean(
        related="company_id.l10n_do_show_header",
        readonly=False,
    )
    l10n_do_show_footer = fields.Boolean(
        related="company_id.l10n_do_show_footer",
        readonly=False,
    )
    l10n_do_year_tag_line = fields.Html(
        related="company_id.l10n_do_year_tag_line",
        readonly=False,
    )
    l10n_do_sign_table = fields.Html(
        related="company_id.l10n_do_sign_table",
        readonly=False,
    )
