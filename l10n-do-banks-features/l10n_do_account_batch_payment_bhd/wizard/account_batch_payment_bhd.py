from odoo import models


class L10ndoAccountBatchPaymentBHD(models.TransientModel):
    _inherit = "l10n_do.account.batch.payment"

    def generate_bank_file(self):
        if not self.journal_id.is_bhd_bank():
            return super(L10ndoAccountBatchPaymentBHD, self).generate_bank_file()

        self.write(self.payment_ids._get_bhd_file())
        return self._get_wizard_action()
