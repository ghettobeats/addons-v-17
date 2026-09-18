#  Copyright (c) 2019 - Indexa SRL. (https://www.indexa.do) <info@indexa.do>
#  See LICENSE file for full licensing details.

from odoo import models, _


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    def setup_document_layout(self):
        view_id = self.env.ref(
            "l10n_do_withholding_certification.withholding_layout_setup_wizard_form"
        )
        return {
            "name": _("Setup company Withholding Certification"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "context": {"default_company_id": self.company_id.id},
            "res_model": "withholding.layout.setup.wizard",
            "views": [(view_id.id, "form")],
            "view_id": view_id.id,
            "target": "new",
        }
