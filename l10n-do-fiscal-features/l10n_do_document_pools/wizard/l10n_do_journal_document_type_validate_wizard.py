from odoo import models, fields, _
from odoo.exceptions import ValidationError


class DocumentTypeValidateWizard(models.TransientModel):
    """
    This Wizard purpose is to warn the user when attempt to change
    sequence state.
    """

    _name = "ir.sequence.validate_wizard"
    _description = "Fiscal Sequence Validate Wizard"

    name = fields.Char()
    journal_document_type_id = fields.Many2one(
        "l10n_do.account.journal.document_type",
        string="Fiscal sequence",
    )

    def confirm_cancel(self):
        self.ensure_one()
        if self.journal_document_type_id:
            action = self._context.get("action", False)
            if action == "confirm":
                self.journal_document_type_id._action_confirm()
            elif action == "cancel":
                self.journal_document_type_id._action_cancel()
        else:
            raise ValidationError(
                _("There is no Fiscal Sequence to perform this action.")
            )
