from odoo import models, fields, api


class L10ndoAccountBatchPaymentBPD(models.TransientModel):
    _inherit = "l10n_do.account.batch.payment"

    effective_date = fields.Date(
        default=fields.Date.context_today,
        help="Select the effectiveness date of all transactions",
    )
    is_bpd_bank = fields.Boolean(compute="_compute_is_bpd_bank")

    @api.depends("journal_id")
    def _compute_is_bpd_bank(self):
        for wizard in self:
            wizard.is_bpd_bank = wizard.journal_id.is_bpd_bank()

    def generate_bank_file(self):
        if not self.journal_id.is_bpd_bank():
            return super(L10ndoAccountBatchPaymentBPD, self).generate_bank_file()

        self.write(self.payment_ids._get_bpd_file(self.effective_date))
        return self._get_wizard_action()
