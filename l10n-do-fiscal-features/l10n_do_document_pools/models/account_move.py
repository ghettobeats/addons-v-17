from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_do_sequence_message = fields.Char(
        "Sequence Warning Message", compute="_compute_l10n_do_sequence_message"
    )
    l10n_do_journal_document_type_id = fields.Many2one(
        "l10n_do.account.journal.document_type",
        string="Journal Document Type",
        compute="_compute_l10n_latam_available_document_types",
        compute_sudo=False,
        store=True,
    )

    def _get_last_sequence(self, relaxed=False, with_prefix=None, lock=True):
        result = super(AccountMove, self)._get_last_sequence(
            relaxed=relaxed, with_prefix=with_prefix, lock=lock
        )

        if self.company_id.l10n_do_sequence_manager:

            ctx = self.env.context
            next_sequence = ctx.get("next_sequence", False)
            is_l10n_do_seq = ctx.get("is_l10n_do_seq", False)
            journal_doc_type = self.l10n_do_journal_document_type_id
            if is_l10n_do_seq and not next_sequence:

                if journal_doc_type and journal_doc_type.state == "expired":
                    raise UserError(
                        _("%s Fiscal Sequence is expired")
                        % journal_doc_type.l10n_latam_document_type_id.name
                    )

                if (
                    self.state != "draft"  # allow to save new invoice
                    and journal_doc_type
                    and journal_doc_type.state not in ("valid", "expired")
                ):
                    raise UserError(
                        _("%s is not a valid fiscal sequence")
                        % journal_doc_type.l10n_latam_document_type_id.name
                    )

                # After consume a sequence, evaluate if sequence
                # is depleted and set state to depleted
                if (
                    journal_doc_type.sequence_end
                    == journal_doc_type.l10n_do_next_sequence
                    and journal_doc_type.state == "valid"
                ):

                    # Deplete main and queued sequence
                    journal_doc_type.state = "depleted"
                    if journal_doc_type.active_pool_id:
                        journal_doc_type.active_pool_id.state = "depleted"

                    # Get a new sequence, if exists
                    queued_sequence_id = journal_doc_type._get_queued_pool()
                    if queued_sequence_id:
                        queued_sequence_id._start_queued_pool()

            if (
                not next_sequence
                and is_l10n_do_seq
                and journal_doc_type.l10n_do_first_sequence
            ):
                doc_type_starting_sequence = (
                    journal_doc_type._get_document_type_starting_sequence()
                )
                if not result:
                    result = (
                        self._get_starting_sequence()[:3] + doc_type_starting_sequence
                    )
                else:
                    result = result[:3] + doc_type_starting_sequence

        return result

    def _post(self, soft=True):
        to_post = super(AccountMove, self)._post(soft)
        for move in self.filtered(
            lambda m: m.l10n_latam_use_documents
            and m.country_code == "DO"
            and m.l10n_do_journal_document_type_id
            and m.l10n_do_journal_document_type_id.l10n_do_first_sequence
            and m.company_id.l10n_do_sequence_manager
        ):
            move.l10n_do_journal_document_type_id.l10n_do_first_sequence = False
        return to_post

    @api.depends("journal_id", "partner_id", "company_id", "move_type")
    def _compute_l10n_latam_available_document_types(self):
        super(AccountMove, self)._compute_l10n_latam_available_document_types()
        l10n_do_invoices = self.filtered(
            lambda inv: inv.journal_id
            and inv.l10n_latam_use_documents
            and inv.country_code == "DO"
            and inv.company_id.l10n_do_sequence_manager
        )
        for invoice in l10n_do_invoices:
            invoice.l10n_do_journal_document_type_id = (
                invoice.journal_id.l10n_do_document_type_ids.filtered(
                    lambda doc: doc.l10n_latam_document_type_id
                    == invoice.l10n_latam_document_type_id
                )
            ).id
        (self - l10n_do_invoices).l10n_do_journal_document_type_id = False

    @api.depends(
        "journal_id.l10n_latam_use_documents",
        "l10n_latam_manual_document_number",
        "l10n_latam_document_type_id",
        "company_id",
    )
    def _compute_l10n_do_enable_first_sequence(self):
        """
        Disable first sequence manual input
        """
        sequence_manager_invoices = self.filtered(
            # sequence manager enable
            lambda inv: inv.company_id.l10n_do_sequence_manager
        )
        sequence_manager_invoices.l10n_do_enable_first_sequence = False

        super(
            AccountMove, self - sequence_manager_invoices
        )._compute_l10n_do_enable_first_sequence()

    @api.depends(
        "l10n_do_journal_document_type_id", "state", "l10n_latam_manual_document_number"
    )
    def _compute_l10n_do_sequence_message(self):
        l10n_do_invoices = self.filtered(
            lambda inv: inv.l10n_latam_use_documents
            and inv.l10n_latam_document_type_id
            and inv.country_code == "DO"
            and inv.state == "draft"
            and inv.company_id.l10n_do_sequence_manager
        )
        for invoice in l10n_do_invoices:
            journal_document_type_id = invoice.l10n_do_journal_document_type_id
            sequence_left = invoice.company_id.l10n_do_sequence_left
            remaining = (
                journal_document_type_id.sequence_end
                - journal_document_type_id.l10n_do_next_sequence
                + 1
            )
            if journal_document_type_id.state == "depleted":
                invoice.l10n_do_sequence_message = _("Fiscal Sequence depleted.")
            elif not journal_document_type_id.queued_pool_ids.filtered(
                lambda seq: seq.state == "queue"
            ) and (sequence_left > 0 and remaining <= sequence_left):
                invoice.l10n_do_sequence_message = _(
                    "Fiscal Sequence is about to run out."
                )
            else:
                invoice.l10n_do_sequence_message = False

        (self - l10n_do_invoices).l10n_do_sequence_message = False
