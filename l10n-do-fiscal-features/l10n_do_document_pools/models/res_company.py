from datetime import timedelta
from odoo import models, fields
from .journal_document_type import get_l10n_do_datetime


class Company(models.Model):
    _inherit = "res.company"

    l10n_do_sequence_manager = fields.Boolean(
        "Enable/disable advance fiscal sequence management"
    )
    l10n_do_sequence_left = fields.Integer("Sequence left for warning", default=10)
    l10n_do_sequence_days_to_expire = fields.Integer("Days to Expire", default=7)

    def get_expiring_sequences(self):
        self.ensure_one()
        # Use DO local time
        l10n_do_date = get_l10n_do_datetime().date()
        delta = timedelta(days=self.l10n_do_sequence_days_to_expire)
        fiscal_sequence_ids = self.env["l10n_do.account.journal.document_type"].search(
            [
                ("state", "=", "valid"),
                ("company_id", "=", self.id),
            ],
        )
        return fiscal_sequence_ids.filtered(
            lambda seq: seq.expiration_date - l10n_do_date <= delta
        )

    def _send_expire_notification_mail(self):
        template_id = self.env.ref(
            "l10n_do_document_pools.l10n_do_document_pools_expire_template",
            raise_if_not_found=False,
        )
        if template_id:
            template_id.send_mail(self.id, force_send=True)

    def _expire_notification_cron(self):
        """
        Function called from ir.cron which warns that sequences are
        about to expire
        """
        country_id = self.env.ref("base.do")
        company_ids = self.search(
            [
                ("partner_id.country_id", "=", country_id.id),
                ("l10n_do_sequence_days_to_expire", ">", 0),
                ("l10n_do_sequence_manager", "=", True),
            ],
        )
        for company in company_ids.filtered(
            lambda c: c.id in c.get_expiring_sequences().mapped("company_id").ids
        ):
            company._send_expire_notification_mail()
