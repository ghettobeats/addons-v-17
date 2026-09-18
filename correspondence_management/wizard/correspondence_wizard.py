from odoo import fields, models, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class CorrespondenceWizard(models.TransientModel):
    _name = 'correspondence.wizard'
    _description = 'Description'

    name = fields.Char(string='Asunto')
    department_id = fields.Many2one('hr.department', string='Destino')
    employee_id = fields.Many2one('hr.employee', string='Destinatario')
    internal_messenger = fields.Many2one('hr.employee', string='Mensajero interno', required=True)
    delivery_date = fields.Datetime(string='Fecha de entrega')
    supported_attachment_ids = fields.Many2many(
        'ir.attachment', string="Documento de apoyo", required=True,)
    description = fields.Html(string='Notas extras')


    def action_done(self):
        record = self.env['correspondence'].browse(
            self._context.get('active_id'))
        if not self.supported_attachment_ids:
            raise ValidationError("Debe cargar el adjunto antes de proceder.")
        else:
            record.write({
                'supported_attachment_ids': self.supported_attachment_ids,
                'description': self.description,
                'delivery_date': self.delivery_date,
                'state': 'delivered',
            })
        return