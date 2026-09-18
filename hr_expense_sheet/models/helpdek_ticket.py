from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    expense_id = fields.Many2one(
        comodel_name='hr.expense.sheet',
        string='Viatico Relacionado',
        store=True)

    def write(self, values):
        """
            Override the `write` method to add custom logic when updating records.

            This method updates an existing `HelpdeskTicket` record with the provided `values`.
            If the `expense_id` field is updated and the related `expense_id` does not have a `ticket_id` set,
            it assigns the current ticket's ID to the `expense_id.ticket_id`.

            Args:
                values (dict): A dictionary of field names and their new values to update in the record.

            Returns:
                bool: `True` if the update is successful, otherwise `False`.

            Example:
                ticket.write({'expense_id': expense_record})
        """
        res = super(HelpdeskTicket, self).write(values)
        if 'expense_id' in values and self.expense_id:
            if not self.expense_id.ticket_id:
                self.expense_id.ticket_id = self.id
        return res
