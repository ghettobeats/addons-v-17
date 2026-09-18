from odoo import models, api, fields

class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    # Relational field to log stage changes
    stage_log_ids = fields.One2many(
        comodel_name='helpdesk.stages.log',
        inverse_name='helpdesk_ticket_id',
        string='Cierre de Etapas')

    # Field to store the ticket's completion date
    ticket_end_date = fields.Datetime(
        string='Fecha de finalización del ticket',
        required=False)

    # Field to store the date of the official document (Oficio)
    official_document_date = fields.Date(
        string='Fecha Oficio',
        required=False)

    # Field to store the requesting area
    requesting_area = fields.Many2one(
        comodel_name='hr.department',
        string='Área solicitante',
        required=False)

    # Field to store the beneficiary
    beneficiary = fields.Many2one(
        comodel_name='res.partner',
        string='Beneficiario',
        required=False)
    
    # Boolean field to indicate if signatures are missing
    signature_missing = fields.Boolean(
        string='Falta Firma',
        compute='_compute_signature_missing',
        default=True)

    # Many2many field to associate related invoices with the ticket
    related_invoices = fields.Many2many(
        comodel_name='account.move',
        string='Facturas Relacionadas',
        help=('Permite asociar facturas relacionadas con el ticket actual. '
              'Esto puede ser útil para rastrear y gestionar documentos contables vinculados al caso.'))

    # Many2many field to associate related payments with the ticket
    related_payments = fields.Many2many(
        comodel_name='account.payment',
        string='Pagos Relacionados',
        help='Permite asociar pagos relacionados con el ticket actual. Esto ayuda a rastrear y administrar '
             'transacciones financieras vinculadas al caso.')

    def setLastStageConclusionDate(self,vals):
        """     Sets the completion date of the ticket to match the conclusion date
                of the final stage logged for the ticket.

                Args:
                    vals (dict): Dictionary of values to update the ticket.

                Returns:
                    dict: Updated values including the ticket_end_date if applicable.
                """
        # Find the final stage with the 'isFinalStage' flag
        final_stage = self.env['helpdesk.stage'].search([('isFinalStage', '=', True)])

        # Check if the final stage is already logged for this ticket
        alreadyInLog = self.env['helpdesk.stages.log'].search([
            ('helpdesk_ticket_id', '=', self.id),
            ('stage_id', '=', final_stage.id)])

        # Update the ticket_end_date with the final stage's conclusion date
        if alreadyInLog:
            vals["ticket_end_date"] = alreadyInLog.stage_conclusion_date
        return vals

    @api.model
    def create(self, vals):
        """
        Overrides the `create` method to log the initial stage and its creation date.

        Args:
            vals (dict): Values for creating the ticket.

        Returns:
            record: The created ticket record.
        """
        # Create the ticket
        ticket = super(HelpdeskTicket, self).create(vals)

        # Log the initial stage if defined
        if ticket.stage_id:  # Si el ticket tiene una etapa inicial definida
            self.env['helpdesk.stages.log'].create({
                'helpdesk_ticket_id': ticket.id,
                'stage_id': ticket.stage_id.id,
                'stage_start_date': ticket.create_date,  # Fecha de creación del ticket
            })
        return ticket

    def write(self, vals):
        """
        Overrides the `write` method to handle stage changes:
        - Logs the start date of a new stage.
        - Logs the end date of the current stage when transitioning.
        - Updates the start date of an existing stage if revisited.
        - Updates the ticket completion date when reaching the final stage.

        Args:
            vals (dict): Values to update the ticket.

        Returns:
            bool: Result of the `write` operation.
        """
        # Check if the stage had changed
        if 'stage_id' in vals and vals['stage_id'] != self.stage_id.id:
            # Log the end date of the current stage
            current_stage_log = self.env['helpdesk.stages.log'].search([
                ('helpdesk_ticket_id', '=', self.id),
                ('stage_id', '=', self.stage_id.id),
            ], limit=1)

            if current_stage_log:
                current_stage_log.write({
                    'stage_end_date': fields.Datetime.now()
                })

            # Check if the new stage is already logged
            stage_in_log = self.env['helpdesk.stages.log'].search([
                ('helpdesk_ticket_id', '=', self.id),
                ('stage_id', '=', vals['stage_id']),
            ], limit=1)

            if stage_in_log:
                # Update the start date if the stage is revisited
                stage_in_log.write({
                    'stage_start_date': fields.Datetime.now(),
                    'stage_end_date': False  # Clear any previous end date
                })
            else:
                # Log a new stage with the current start date
                self.env['helpdesk.stages.log'].create({
                    'helpdesk_ticket_id': self.id,
                    'stage_id': vals['stage_id'],
                    'stage_start_date': fields.Datetime.now(),
                })

            # Update the ticket completion date if the new stage is the final stage
            final_stage = self.env['helpdesk.stage'].search([
                ('id', '=', vals['stage_id']), ('isFinalStage', '=', True)
            ])
            if final_stage:
                vals['ticket_end_date'] = fields.Datetime.now()

        return super(HelpdeskTicket, self).write(vals)

    @api.depends('stage_log_ids.signature')
    def _compute_signature_missing(self):
        for ticket in self:
            # Check if all related stage logs have a signature
            if ticket.stage_log_ids and all(log.signature for log in ticket.stage_log_ids):
                ticket.signature_missing = False
            else:
                ticket.signature_missing = True