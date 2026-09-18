import base64
from odoo import models, fields, _
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _get_transaction_data(self):
        if self.filtered(
            lambda payment: payment.journal_id.is_bhd_bank()
            and not payment.journal_id.bank_account_id.bank_id
        ):
            raise UserError(_("BHD bank batch payment file needs account bank"))
        payment_data = super(AccountPayment, self)._get_transaction_data()
        account_type_map = {"cheque": "CA", "savings": "CC"}
        for payment_vals in payment_data:
            payment_id = self.browse(payment_vals["payment_id"])
            l10n_do_bhd_bank_code = (
                payment_id.partner_bank_id.bank_id.l10n_do_bhd_bank_code
            )
            payment_vals.update(
                {
                    "bank_code": l10n_do_bhd_bank_code,
                    "account_type": account_type_map[
                        payment_id.partner_bank_id.account_type
                    ],
                    "move_type": "C",
                    "ref": payment_id.name,
                    "email": payment_id.partner_id.commercial_partner_id.email,
                    "description": payment_id.ref or payment_id.name,
                    "phone": payment_id.get_partner_sanitized_phone(),
                }
            )
        return payment_data

    def _get_bhd_filename(self):
        fname = (
            "PE"
            + self[0].journal_id.bank_acc_number
            + fields.Date.from_string(fields.Date.context_today(self)).strftime("%m%d")
            + "E.txt"
        )
        return fname

    def _get_bhd_file(self):

        bhd_fields = [
            "destination_acc",
            "bank_code",
            "account_type",
            "supplier_name",
            "move_type",
            "amount",
            "ref",
            "description",
            "email",
            "phone",
        ]

        content = ""
        transaction_data = self._get_transaction_data()
        for row in transaction_data:
            content += ";".join([row[field] or "-" for field in bhd_fields]) + "\n"

        bhd_filename = self._get_bhd_filename()
        file_path = "/tmp/%s" % bhd_filename
        with open(file_path, "w") as f:
            f.write(str(content))

        file_binary = base64.b64encode(open(file_path, "rb").read())
        return {
            "file": file_binary,
            "filename": bhd_filename,
        }

    def _get_BCBHDOSDXXX_file(self):
        return self._get_bhd_file()
