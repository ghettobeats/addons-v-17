from odoo import models, fields, _
from odoo.exceptions import UserError


class AccountBatchPayment(models.Model):
    _inherit = "account.batch.payment"

    batch_type = fields.Selection(
        selection_add=[("transfer", "Internal Transfer")],
        ondelete={"transfer": "set default"},
    )

    def _get_methods_generating_files(self):
        res = super(AccountBatchPayment, self)._get_methods_generating_files()
        if self.journal_id.company_id.country_id.code == "DO":
            res.append(self.payment_method_id.code)
        return res

    def _generate_export_file(self):
        self.ensure_one()
        if self.journal_id.company_id.country_id.code == "DO":

            if (
                self.journal_id.bank_id
                and hasattr(
                    self.journal_id, "_is_%s_bank" % self.journal_id.bank_id.bic
                )
                and getattr(
                    self.journal_id, "_is_%s_bank" % self.journal_id.bank_id.bic
                )()
            ):
                return getattr(
                    self.payment_ids.with_context(effective_date=self.date),
                    "_get_%s_file" % self.journal_id.bank_id.bic,
                )()

            raise UserError(
                _(
                    "Could not generate any bank file.\n"
                    "Did you install the module to support %s bank?"
                    % self.journal_id.name
                )
            )
        return super(AccountBatchPayment, self)._generate_export_file()
