from odoo import models, fields, api, _
from odoo.tools import remove_accents
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def get_partner_sanitized_phone(self):
        """
        Some banks batch payment files may need partners phone.
        This function returns partner phone number with only digits.
        """
        self.ensure_one()
        phone_number = self.partner_id.commercial_partner_id.phone
        if not phone_number:
            return ""
        return "".join([digit for digit in phone_number if digit and digit.isdigit()])

    def get_recipient_email(self):
        """
        Gets recipient email depending on payment type.
        Internal transfers uses payments bank account holder email.
        """
        self.ensure_one()
        if self.payment_type != "transfer":
            return self.partner_id.email or ""
        elif self.partner_bank_id:
            return self.partner_bank_id.partner_id.email or ""
        return ""

    @api.model
    def _get_sanitized_name(self, name):
        """
        remove special characters
        remove accents
        set uppercase
        """
        return remove_accents(
            "".join(x for x in name if x.isalnum() or x.isspace())
        ).upper()

    def get_recipient_name(self):
        """
        Gets recipient name depending on payment type.
        Internal transfers uses payments bank account holder name.
        """
        self.ensure_one()
        name = ""
        if self.payment_type != "transfer":
            name = self.partner_id.name
        elif self.partner_bank_id:
            name = self.partner_bank_id.partner_id.name
        return self._get_sanitized_name(name)

    def _get_currency_payment_amount(self):
        """
        Returns company currency payment amount
        """
        aml_id = self.line_ids.filtered(
            lambda aml: aml.account_id.user_type_id.type == "liquidity"
            and aml.journal_id == self.journal_id
        )
        return sum([aml_id.credit, aml_id.debit])

    def _get_transaction_data(self):
        """
        Base method of minimal payment transaction data.
        Inherit this from each bank module.
        """

        if self.filtered(lambda p: not p.partner_bank_id):
            raise UserError(
                _("Recipient Bank Account is required to generate batch payment file")
            )

        return [
            {
                "payment_id": payment.id,
                "origin_acc": payment.journal_id.bank_account_id.sanitized_acc_number,
                "destination_acc": payment.partner_bank_id.sanitized_acc_number,
                "amount": "{0:.2f}".format(payment.amount),
                "supplier_name": payment.partner_id.name,
            }
            for payment in self
        ]
