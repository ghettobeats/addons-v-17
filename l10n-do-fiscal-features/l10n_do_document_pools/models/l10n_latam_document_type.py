from odoo import models, api


class L10nLatamDocumentType(models.Model):
    _inherit = "l10n_latam.document.type"

    def get_l10n_do_document_type_mapping(self):
        return {
            k: "out_invoice"
            if k.replace("e-", "") not in ("informal", "minor", "exterior")
            else "out_refund"
            if k.replace("e-", "") == "credit_note"
            else "in_invoice"
            for k, v in dict(self._get_l10n_do_ncf_types()).items()
        }

    @api.model
    def get_l10n_do_tax_payer_type_mapping(self):

        return {
            "fiscal": "taxpayer",
            "consumer": "non_payer",
            "debit_note": "taxpayer",
            "credit_note": "taxpayer",
            "informal": "non_payer",
            "unique": "non_payer",
            "minor": "non_payer",
            "special": "special",
            "governmental": "governmental",
            "export": "foreigner",
            "exterior": "foreigner",
            "e-fiscal": "taxpayer",
            "e-consumer": "non_payer",
            "e-debit_note": "taxpayer",
            "e-credit_note": "taxpayer",
            "e-informal": "non_payer",
            "e-minor": "non_payer",
            "e-special": "special",
            "e-governmental": "governmental",
            "e-export": "foreigner",
            "e-exterior": "foreigner",
            "in_fiscal": "taxpayer",
        }
