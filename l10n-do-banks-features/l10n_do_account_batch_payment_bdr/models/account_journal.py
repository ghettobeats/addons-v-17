from odoo import models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def is_bdr_bank(self):
        if not self.bank_id:
            return False
        return self.bank_id.bic == "BRRDDOSD"

    def _is_BRRDDOSD_bank(self):
        return self.is_bdr_bank()
