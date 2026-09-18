from odoo import models, fields


class AccountAbstractPayment(models.AbstractModel):
    _inherit = "account.abstract.payment"

    release_number = fields.Char(string="Release number",)
    allow_check_release = fields.Boolean(related="journal_id.allow_check_release",)


class AccountRegisterPayments(models.TransientModel):
    _inherit = "account.register.payments"

    def _prepare_payment_vals(self, invoices):

        res = super(AccountRegisterPayments, self)._prepare_payment_vals(invoices)
        res["release_number"] = self.release_number

        return res
