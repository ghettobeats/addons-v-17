from odoo import models


class L10ndoAccountBatchPaymentBDR(models.TransientModel):
    _inherit = "l10n_do.account.batch.payment"

    def generate_bank_file(self):
        if not self.journal_id.is_bdr_bank():
            return super(L10ndoAccountBatchPaymentBDR, self).generate_bank_file()

        self.write(self.payment_ids._get_bdr_file())
        return self._get_wizard_action()
