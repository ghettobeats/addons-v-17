from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    ticket_id = fields.Many2one('helpdesk.ticket', 'Ticket Relacionado', store=True)

    # def write(self, values):
    #     res = super(HrExpenseSheet, self).write(values)
    #     if 'ticket_id' in values and self.ticket_id:
    #         if not self.ticket_id.expense_id:
    #             self.ticket_id.expense_id = self.id
    #     return res

    @api.constrains('state')
    def check_state_validity(self):
        """
        This method checks if the 'state' field is set to 'desemb' and if the
        related ticket's stage is 'Realizado'. If both conditions are met,
        it sends a status notification.

        Conditions:
        - The 'x_ticket_id' must be set.
        - The 'state' must be 'desemb'.
        - The related ticket's 'stage_id.display_name' must be 'Realizado'.

        If these conditions are met, it calls the 'send_status_notification' method.

        Args:
            None.
        Returns:
            None.
        """
        if self.ticket_id and self.state == 'desemb':
            if self.ticket_id.stage_id.display_name == 'Realizado':
                self.send_status_notification()
            else:
                pass

    def send_status_notification(self):
        """
        Sends an email notification to the employee regarding the status of their expense.

        This method uses the email template 'hr_expense_sheet.email_template_status_notification'
        to generate an email with the subject and body. If the employee has a work email, the email is sent to them.
        If no work email is available, no email is sent.

        Steps:
        1. Retrieve the email template by its reference.
        2. Get the "from" email address.
        3. Generate the subject and body from the template.
        4. Send the email to the employee's work email if available.
        5. Do nothing if the work email is missing.
        """
        template_id = self.env.ref('hr_expense_sheet.email_template_status_notification', raise_if_not_found=False)
        if template_id:
            email_from = self.env.ref('base.partner_root').email
            email_template = self.env['mail.template'].browse(template_id.id)
            mail_values = email_template.with_context(object=self).generate_email(self.ids,
                                                                                  fields=['subject',
                                                                                          'body_html'])
            email_to = self.employee_id.work_email
            if email_to:
                for res_id, values in mail_values.items():
                    mail = self.env['mail.mail'].create({
                        'email_from': email_from,
                        'email_to': email_to,
                        'subject': mail_values[res_id]['subject'],
                        'body_html': mail_values[res_id]['body_html'],
                    })
                    mail.send()
            else:
                _logger.info(f"El empleado {self.employee_id.name} {self.employee_id.last_name} had no work email")
                pass

    beneficiary_type = fields.Selection(
        string='Tipo de beneficiario',
        selection=[('employee', 'Empleado'),
                   ('guest', 'Invitado'), ],
        required=False, default='employee')

    guest_id = fields.Many2one(
        comodel_name='res.partner',
        string='Invitado',
        required=False)

    # Redefinimos el campo para quitarle las restricciones de Odoo base
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string="Empleado",
        required=False,  # Lo ponemos False aquí para que el XML decida
        readonly=False,  # Quitamos el readonly estático
        tracking=True,
        check_company=True,
        # Mantenemos la lógica de dominio original
        domain=lambda self: self.env['hr.expense']._get_employee_id_domain()
    )