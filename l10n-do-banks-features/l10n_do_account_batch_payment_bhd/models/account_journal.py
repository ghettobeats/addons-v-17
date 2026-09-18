from odoo import models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def is_bhd_bank(self):
        if not self.bank_id:
            return False
        return self.bank_id.bic == "BCBHDOSDXXX"

    def _is_BCBHDOSDXXX_bank(self):
        return self.is_bhd_bank()
