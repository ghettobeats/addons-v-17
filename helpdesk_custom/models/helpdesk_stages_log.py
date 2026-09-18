from odoo import api, exceptions, fields, models


class HelpdeskStagesLog(models.Model):
    """
    Model for logging stage changes of tickets in the Helpdesk module.
    This model keeps a record of the stages, including the start date of each.
    """
    _name = 'helpdesk.stages.log'

    # Relational field: ID of the related ticket
    helpdesk_ticket_id = fields.Many2one(
        comodel_name='helpdesk.ticket',
        string=' helpdesk_ticket_id')

    # Relational field: ID of the stage
    stage_id = fields.Many2one(
        comodel_name='helpdesk.stage',
        string='Estado del Documento',
        required=False)


    # Field: Ticket Assigned user
    assign_user = fields.Many2one(
        comodel_name='res.users',
        string='Usuario asignado',
        required=False)

    # Field: Signature
    signature = fields.Binary(string="Firma")

    # Field: Start date & time of the stage
    stage_start_date = fields.Datetime(string='Fecha y Hora de Inicio', required=False)

    # Field: End date & time of the stage
    stage_end_date = fields.Datetime(string='Fecha y Hora Final', required=False)

    # Field: Time Spent on a stage
    stage_time_spent = fields.Float(
        string='Tiempo Consumido',
        store=True,
        compute='_compute_stage_time_spent')

    @api.depends('stage_start_date', 'stage_end_date')
    def _compute_stage_time_spent(self):
        for rec in self:
            if rec.stage_start_date and rec.stage_end_date:
                duration = (rec.stage_end_date - rec.stage_start_date).total_seconds() / 3600
                if duration >= 0.01:
                    rec.stage_time_spent = duration
                else:
                    rec.stage_time_spent = 0.01
            else:
                return 0.00
