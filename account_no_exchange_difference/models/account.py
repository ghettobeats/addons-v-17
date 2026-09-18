from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def check_full_reconcile(self):
        """
        Send no_exchange_difference through context. This key may prevent an exchange
        difference journal entry to be automatically created when a small amount is
        left as surplus/deficit in an invoice/payment reconcile action.
        See for further info: odoo/addons/account/models/account_move.py#L3750
        """
        create_entry = not self.company_id.exchange_difference_entry
        return super(
            AccountMoveLine,
            self.with_context(no_exchange_difference=create_entry),
        ).check_full_reconcile()
