#  Copyright (c) 2019 - Indexa SRL. (https://www.indexa.do) <info@indexa.do>
#  See LICENSE file for full licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_do_reconciled_payments_journal = fields.Boolean(
        help="Check this field if this journal will be used for reconciled "
        "payments entries."
    )

    @api.constrains("l10n_do_reconciled_payments_journal", "company_id", "type")
    def _check_l10n_do_reconciled_payments_journal(self):
        if (
            self.search_count(
                [
                    ("l10n_do_reconciled_payments_journal", "=", True),
                    ("company_id", "=", self.env.user.company_id.id),
                    ("type", "=", "general"),
                ]
            )
            > 1
        ):
            raise UserError(
                _("Only one reconciled payments journal is allowed per " "company")
            )

        if self.filtered(
            lambda j: j.l10n_do_reconciled_payments_journal and not j.type == "general"
        ):
            raise UserError(
                _(
                    "Only Miscellaneous type journal can be assigned as "
                    "reconciled payments journal"
                )
            )

    def write(self, values):
        l10n_do_reconciled_payments_journal = values.get(
            "l10n_do_reconciled_payments_journal", False
        )
        if l10n_do_reconciled_payments_journal:
            journals = self.search(
                [
                    ("l10n_do_reconciled_payments_journal", "=", True),
                    ("company_id", "=", self.env.user.company_id.id),
                    ("id", "!=", self.id),
                ]
            )
            journals.write({"l10n_do_reconciled_payments_journal": False})

        return super(AccountJournal, self).write(values)
