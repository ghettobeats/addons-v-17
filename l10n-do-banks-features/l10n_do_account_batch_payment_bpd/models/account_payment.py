import base64
from odoo import models, fields, _
from odoo.exceptions import UserError
from datetime import date, datetime

from .bpd_fields import bpd_fields, bpd_header


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _get_header_data(self, bpd_file_sequence, effective_date, credits_total):
        if not self:
            return {}

        company_id = self[0].company_id

        if not company_id.vat:
            raise UserError(_("Banco Popular batch payment file needs company VAT"))

        header_vals = {
            "record_type": "H",
            "company_id": company_id.vat.ljust(15),
            "company_name": company_id.name[:34].ljust(35),
            "sequence": bpd_file_sequence,
            "service_type": "02",
            "effective_date": fields.Date.to_string(effective_date).replace("-", ""),
            "debits_qty": "".zfill(11),
            "debits_total": "".zfill(13),
            "credits_qty": str(len(self.ids)).zfill(11),
            "credits_total": f"{credits_total:.2f}".replace(".", "").zfill(15),
            "affiliation_number": "".zfill(13),
            "date": date.today().strftime("%Y%m%d"),
            "hour": datetime.now().strftime("%H%M"),
            "email": company_id.email.ljust(40) if company_id.email else "".ljust(40),
            "status": " ",
            "filler_2": "".ljust(136),
        }
        return header_vals

    def _get_transaction_data(self):
        payment_data = super(AccountPayment, self)._get_transaction_data()
        account_type_map = {"cheque": "1", "savings": "2"}
        transaction_code_map = {"1": "22", "2": "32"}
        for payment_vals in payment_data:
            payment_id = self.browse(payment_vals["payment_id"])
            partner_id = (
                payment_id.partner_id.commercial_partner_id
                if payment_id.payment_type != "transfer"
                else (
                    payment_id.partner_bank_id.partner_id
                    if payment_id.partner_bank_id.partner_id
                    else False
                )
            )
            if not partner_id or not partner_id.vat:
                raise UserError(
                    "Banco Popular batch payment file require %s VAT" % partner_id.name
                )
            if not payment_id.company_id.vat:
                raise UserError(_("Banco Popular batch payment file needs company VAT"))

            partner_vat = partner_id.vat

            account_type = payment_id.partner_bank_id.account_type
            if not account_type:
                raise UserError(
                    _("%s account type is required for generate batch file")
                    % payment_id.partner_bank_id
                )

            payment_vals.update(
                {
                    "record_type": "N",
                    "company_id": payment_id.company_id.vat.ljust(15),
                    "sequence": self.env.context.get("bpd_file_sequence", False),
                    "sequence_transaction": self.env["ir.sequence"].next_by_code(
                        "batch.payment.bpd.tx.sequence"
                    ),
                    "account_type": account_type_map[
                        payment_id.partner_bank_id.account_type
                    ],
                    "account_currency": payment_id.currency_id.l10n_do_bpd_currency_code,
                    "l10n_do_bpd_bank_code": payment_id.partner_bank_id.bank_id.l10n_do_bpd_bank_code,
                    "l10n_do_bpd_bank_digiver": str(
                        payment_id.partner_bank_id.bank_id.l10n_do_bpd_digiver_code
                    ),
                    "transaction_code": transaction_code_map[
                        account_type_map[account_type]
                    ],
                    "amount": str(payment_vals["amount"]).replace(".", "").zfill(13),
                    "identification_type": "CE"
                    if not partner_vat or len(partner_vat) == 11
                    else "RN",
                    "identification": partner_vat.ljust(15),
                    "ref": payment_id.name.ljust(12),
                    "description": payment_id.ref.ljust(40) if payment_id.ref else "",
                    "expiration_date": " " * 4,
                    "contact_via": "1",
                    "email": payment_id.get_recipient_email().ljust(40),
                    "phone": payment_id.get_partner_sanitized_phone().rjust(12)
                    if payment_id.get_partner_sanitized_phone()
                    else "".rjust(12),
                    "filler_1": "00",
                    "authorization_number": "".ljust(15),
                    "remote_return_code": "".ljust(3),
                    "remote_reason_code": "".ljust(3),
                    "internal_reason_code": "".ljust(3),
                    "transaction_processor": " ",
                    "transaction_status": "".ljust(2),
                    "filler_2": "".ljust(52),
                }
            )
        return payment_data

    def _get_bpd_filename(self, bpd_file_sequence):

        if not self[0].journal_id.company_id.l10n_do_bpd_bank_number:
            raise UserError(
                _("Company BPD Bank number is required for this operation.")
            )
        return (
            "PE"
            + self[0].journal_id.company_id.l10n_do_bpd_bank_number
            + "02"
            + fields.Date.from_string(fields.Date.context_today(self)).strftime("%m%d")
            + bpd_file_sequence
            + "E.txt"
        )

    def _get_bpd_file(self, effective_date):

        content = ""
        bpd_file_sequence = self.env["ir.sequence"].next_by_code(
            "batch.payment.bpd.sequence"
        )

        transaction_data = self.with_context(
            bpd_file_sequence=bpd_file_sequence
        )._get_transaction_data()

        credits_total = sum(float(p["amount"]) for p in transaction_data)

        # Header
        header_data = self._get_header_data(
            bpd_file_sequence, effective_date, credits_total
        )
        content += (
            "".join(header_data[header_field] for header_field in bpd_header) + "\n"
        )

        # Transactions
        for row in transaction_data:
            content += "".join([str(row[field]) for field in bpd_fields]) + "\n"

        # Batch file
        bpd_filename = self._get_bpd_filename(bpd_file_sequence)
        file_path = "/tmp/%s" % bpd_filename
        with open(file_path, "w") as f:
            f.write(str(content))

        file_binary = base64.b64encode(open(file_path, "rb").read())
        return {
            "file": file_binary,
            "filename": bpd_filename,
        }

    def _get_BPDODOSX_file(self):
        ctx = self.env.context
        effective_date = ctx.get("effective_date") or fields.Date.context_today(self)
        return self._get_bpd_file(effective_date)
