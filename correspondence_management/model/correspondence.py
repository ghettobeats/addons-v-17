from odoo import models, fields, api
import logging
import pytz
from datetime import datetime
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class Correspondence(models.Model):
    _name = 'correspondence'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string='Asunto', required=True)
    description = fields.Html(string='Notas extras',copy=False)
    employee_id = fields.Many2one('hr.employee', string='Destinatario', required=True)
    department_id = fields.Many2one('hr.department', string='Destino', compute="_compute_departament", store=True)
    sender_id = fields.Many2one('res.partner', string='Remitente', required=True)
    internal_messenger = fields.Many2one('hr.employee', string='Mensajero interno',
                                         default=lambda self: self.get_default_sender(),
                                         domain=lambda self: self._get_domain())
    external_messenger = fields.Many2one('res.partner', string='Mensajero externo')
    received_date = fields.Datetime(string='Fecha de recepcion ', required=True, default=fields.Datetime.now())
    delivery_date = fields.Datetime(string='Fecha de entrega ',copy=False)
    state = fields.Selection([('draft', 'Borrador'),
                              ('received', 'Recibido'),
                              ('delivered', 'Entregado'),
                              ('cancel', 'Cancelado')
                              ], default='draft', string='Estado', required=True, tracking=True)

    supported_attachment_ids = fields.Many2many(
        'ir.attachment', string="Documento de apoyo", copy=False)

    correspondence_type = fields.Many2many(
        "correspondence.types", string='Tipo'
    )

    color = fields.Integer("Índice de Colores", related="correspondence_type.color")

    def get_default_sender(self):
        return self.env["correspondence.internal.messenger"].search([], limit=1).employee_id.id

    def _get_domain(self):
        default_id = self.env["correspondence.internal.messenger"].search([], limit=1)
        if default_id.job_id:
            return [('job_id.id', '=', default_id.job_id.id)]
        return []

    @api.depends('employee_id')
    def _compute_departament(self):
        for rec in self:
            rec.department_id = rec.employee_id.department_id

    def action_receive(self):
        for rec in self:
            if rec.state in ['delivered', 'cancel', 'received']:
                raise ValidationError(
                    f"No es posible recibir una correspondencia que ya ha sido {'entregada' if rec.state == 'delivered' else 'cancelada' if rec.state == 'cancel' else 'recibida'}.")
            else:
                rec.state = 'received'

    def action_cancel(self):
        for rec in self:
            if not self.env.user.has_group('correspondence_management.correspondence_manager_group'):
                if rec.state == 'received':
                    raise UserError("No tienes los permisos necesarios para realizar esta acción.")
                elif rec.state in ['delivered', 'cancel']:
                    raise ValidationError(
                        f"No es posible cancelar una correspondencia que ya ha sido {'cancelada' if rec.state == 'cancel' else 'entregada'}.")
            else:
                rec.state = 'cancel'

    def action_draft(self):
        for rec in self:
            if not self.env.user.has_group('correspondence_management.correspondence_manager_group'):
                if rec.state in ['delivered', 'cancel','received']:
                    raise ValidationError(
                        f"No es posible devolver a borrador una correspondencia que ya ha sido {'cancelada' if rec.state == 'cancel' else 'recibida'if rec.state == 'received' else 'entregada'}.")
            else:
                rec.state = 'draft'

    def action_delivery(self):
        if len(self) > 1:
            raise UserError("No puede seleccionar multiples registros para marcar como entregado.")
        elif self.state in ['delivered', 'cancel','draft']:
            raise ValidationError(
                f"No es posible entregar una correspondencia que ya ha sido {'entregada' if self.state == 'delivered' else 'cancelada' if self.state == 'cancel' else 'recibida'}.")
        return {
            'name': 'Entregas',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'correspondence.wizard',
            'context': {
                'default_name': self.name,
                'default_description': self.description,
                'default_internal_messenger': self.internal_messenger.id,
                'default_department_id': self.department_id.id,
                'default_delivery_date': fields.Datetime.now()
            }
        }

    def action_print(self):
        return {
            'type': 'ir.actions.report',
            'report_name': 'correspondence_management.correspondence_delivery_ticket',
            'report_type': 'qweb-pdf',
        }

    @api.model
    def get_local_time(self, tz):
        local_tz = pytz.timezone(tz)
        local_time = datetime.now(local_tz)
        return local_time.strftime('%d/%m/%Y - %I:%M:%S')