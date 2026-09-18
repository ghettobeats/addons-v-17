import base64
from odoo import models, fields, _
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _get_transaction_data(self):
        if self.filtered(
            lambda payment: payment.journal_id.is_bdr_bank()
            and not payment.journal_id.bank_acc_number
        ):
            raise UserError(
                _("Reservas bank batch payment file needs an origin account"
                  "number")
            )

        payment_data = super(AccountPayment, self)._get_transaction_data()
        account_type_map = {"cheque": "CC", "savings": "CA"}
        for payment_vals in payment_data:
            payment_id = self.browse(payment_vals["payment_id"])
            payment_vals.update(
                {
                    "origin_acc_type": account_type_map[
                        payment_id.journal_id.bank_account_id.account_type
                    ],
                    "destination_acc_type": account_type_map[
                        payment_id.partner_bank_id.account_type
                    ],
                    "origin_acc_currency": payment_id.journal_id.currency_id.name or "DOP",
                    "destination_acc_currency": payment_id.currency_id.name,
                    "ref": self._get_sanitized_name(payment_id.name),
                    "email": payment_id.partner_id.commercial_partner_id.email,
                    "description": payment_id.ref or payment_id.name,
                }
            )
        return payment_data

    def _get_bdr_filename(self):
        fname = (
            "PE"
            + self[0].journal_id.bank_acc_number
            + fields.Date.from_string(fields.Date.context_today(self)).strftime("%m%d")
            + "E.txt"
        )
        return fname

    def _get_bdr_file(self):

        bdr_fields = [
            "origin_acc_type",
            "origin_acc_currency",
            "origin_acc",
            "destination_acc_type",
            "destination_acc_currency",
            "destination_acc",
            "amount",
            "ref",
        ]

        content = ""
        transaction_data = self._get_transaction_data()
        for row in transaction_data:
            content += ",".join([str(row[field]) for field in bdr_fields]) + "\n"

        bdr_filename = self._get_bdr_filename()
        file_path = "/tmp/%s" % bdr_filename
        with open(file_path, "w") as f:
            f.write(str(content))

        file_binary = base64.b64encode(open(file_path, "rb").read())
        return {
            "file": file_binary,
            "filename": bdr_filename,
        }

    def _get_BRRDDOSD_file(self):
        return self._get_bdr_file()
