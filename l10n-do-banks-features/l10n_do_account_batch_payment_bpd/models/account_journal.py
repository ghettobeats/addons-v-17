from odoo import models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def is_bpd_bank(self):
        if not self.bank_id:
            return False
        return self.bank_id.bic == "BPDODOSX"

    def _is_BPDODOSX_bank(self):
        return self.is_bpd_bank()
