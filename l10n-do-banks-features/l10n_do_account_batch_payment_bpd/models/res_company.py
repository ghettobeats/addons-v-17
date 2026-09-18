from odoo import models, fields, api, _
from odoo.exceptions import UserError


class Company(models.Model):
    _inherit = "res.company"

    l10n_do_bpd_bank_number = fields.Char("BPD Bank Number")

    @api.constrains("l10n_do_bpd_bank_number")
    def _check_l10n_do_bpd_bank_number(self):
        if self.filtered(
            lambda comp: comp.l10n_do_bpd_bank_number
            and not comp.l10n_do_bpd_bank_number.isdigit()
            or len(str(comp.l10n_do_bpd_bank_number)) != 5
        ):
            raise UserError(_("BPD Bank number must be a 5 digits value"))

    def _get_bpd_bank_batch_sequence_vals(self):
        return [
            {
                "name": "BPD Batch Payment File Sequence",
                "code": "batch.payment.bpd.sequence",
                "padding": 7,
                "number_increment": 1,
                "company_id": self.id,
            },
            {
                "name": "BPD Batch Payment TX Sequence",
                "code": "batch.payment.bpd.tx.sequence",
                "padding": 7,
                "number_increment": 1,
                "company_id": self.id,
            },
        ]

    def create_bpd_batch_sequences(self):
        vals_list = self._get_bpd_bank_batch_sequence_vals()
        for vals in vals_list:
            sequence = self.env["ir.sequence"].sudo()
            if not sequence.search(
                [("code", "=", vals["code"]), ("company_id", "=", vals["company_id"])]
            ):
                sequence.create(vals)

    @api.model
    def create(self, vals):
        company = super(Company, self).create(vals)
        company.create_bpd_batch_sequences()
        return company

    def init(self):
        for company in self.search([]):
            company.create_bpd_batch_sequences()
        super(Company, self).init()
