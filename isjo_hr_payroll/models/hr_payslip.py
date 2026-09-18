# -*- coding: utf-8 -*-
# © 2024 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
import base64
import logging
_logger = logging.getLogger(__name__)


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    salary_computation_line_ids = fields.One2many(
        'hr.payslip.line', 'slip_id', 
        compute='_compute_line_ids',
        store=True, string='Salary Computation Lines', readonly=True,
        # states={'draft': [('readonly', False)], 'verify': [('readonly', False)]},
        domain=[('appears_on_payslip', '=', True)])

    def send_payslip_by_email(self):
        """Envía un correo con el recibo de nómina en PDF adjunto"""
        mail_template = self.env.ref('isjo_hr_payroll.payslip_email_template', raise_if_not_found=False)
        # mail_template = self.env.ref('hr_payroll.mail_template_new_payslip', raise_if_not_found=False)
        if not mail_template:
            raise UserError(_("No se encontró la plantilla de correo 'hr_payroll.mail_template_new_payslip'."))

        for payslip in self:
            mail_template.send_mail(payslip.id, force_send=True)

            _logger.info(f"Correo enviado con éxito a {payslip.employee_id.work_email}")

    def action_print_report(self):
        # Impresión del ticket de cuota
        return self.env.ref('isjo_hr_payroll.action_report_payslip').report_action(self)

    def _get_payslip_lines(self):
        res = super(HrPayslip, self)._get_payslip_lines()
        # remove salary rules with amount equal to zero
        res = [line for line in res if line['amount'] != 0]
        return res  

    @api.onchange('payslip_run_id')
    def _onchange_payslip_run_id(self):
        if self.payslip_run_id:
            self.date_from = self.payslip_run_id.date_start
            self.date_to = self.payslip_run_id.date_end
            if self.contract_id:
                contracts = self.employee_id._get_contracts(
                    self.date_from, self.date_to)
                contracts = contracts.filtered(
                    lambda r: r.id == self.contract_id.id)
                if not contracts.id:
                    self.contract_id = False

    @api.onchange('employee_id', 'struct_id', 'contract_id', 'date_from', 'date_to')
    def _onchange_employee(self):
        # Aquí puedes agregar lógica adicional si es necesaria
        if self.payslip_run_id:
            self.name = '%s - %s - %s' % (
                _('Salary Slip'),
                self.employee_id.name or '',
                self.payslip_run_id.name
            )
            if not self.struct_id or not self.struct_id == self.payslip_run_id.struct_id:
                self.struct_id = self.payslip_run_id.struct_id


class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    category_id_code = fields.Char(
        'Category Rule Code', related="category_id.code")

    # input_id = fields.Many2one('hr.payslip.input', string="Entrada Relacionada",
    #                            help="Referencia a la entrada de nómina si aplica")
    # 
    # @api.model
    # def create(self, vals):
    #     """
    #     Asigna la entrada de nómina correspondiente (input_id) en input_line_ids del mismo payslip,
    #     asegurando que cada entrada se use correctamente en las líneas de pago.
    #     """
    #     if 'slip_id' in vals and 'name' in vals and 'code' in vals:
    #         payslip = self.env['hr.payslip'].browse(vals['slip_id'])  # Obtener el recibo
    #         code = vals['code']
    # 
    #         # Obtener todas las entradas disponibles para este código en el payslip
    #         available_inputs = payslip.input_line_ids.filtered(
    #             lambda i: i.input_type_id.code == code and i.code in ['SOSSG', 'INCSG']
    #         ).sorted(lambda i: i.id)  # Ordenar por ID para asignar secuencialmente
    # 
    #         if available_inputs:
    #             # Obtener todas las líneas existentes que ya tienen input_id asignado
    #             used_inputs = payslip.line_ids.mapped('input_id')
    # 
    #             # Filtrar la primera entrada disponible que aún no ha sido asignada
    #             for input_entry in available_inputs:
    #                 if input_entry not in used_inputs:
    #                     vals['input_id'] = input_entry.id
    #                     break  # Asignamos solo una vez y salimos del bucle
    # 
    #             # Si todas las entradas ya fueron asignadas, usamos la primera disponible
    #             if 'input_id' not in vals:
    #                 vals['input_id'] = available_inputs[0].id  # Reutilizamos la primera entrada
    # 
    #     return super(HrPayslipLine, self).create(vals)
    # 
    # def write(self, vals):
    #     """
    #     Al actualizar una línea de nómina (hr.payslip.line), verificar si debe asociarse a una entrada
    #     en input_line_ids, asegurando que cada entrada se use correctamente.
    #     """
    #     for line in self:
    #         slip_id = vals.get('slip_id', line.slip_id.id)
    #         code = vals.get('code', line.code)
    #         payslip = self.env['hr.payslip'].browse(slip_id)
    # 
    #         # Obtener todas las entradas disponibles para este código en el payslip
    #         available_inputs = payslip.input_line_ids.filtered(
    #             lambda i: i.input_type_id.code == code and i.code in ['SOSSG', 'INCSG']
    #         ).sorted(lambda i: i.id)
    # 
    #         if available_inputs:
    #             used_inputs = payslip.line_ids.mapped('input_id')
    # 
    #             for input_entry in available_inputs:
    #                 if input_entry not in used_inputs:
    #                     vals['input_id'] = input_entry.id
    #                     break
    # 
    #             if 'input_id' not in vals:
    #                 vals['input_id'] = available_inputs[0].id  # Reutilizamos la primera entrada
    # 
    #     return super(HrPayslipLine, self).write(vals)

    # @api.model
    # def update_existing_payslip_lines(self, payslip_id=3297):
    #     """
    #     Relaciona cada línea de nómina con su entrada correspondiente en hr.payslip.input,
    #     asegurando que se distribuya correctamente cuando hay múltiples entradas con el mismo nombre.
    #     """
    # 
    #     def normalize_name(name):
    #         """ Normaliza el nombre: mayúsculas y correcciones """
    #         name = name.strip().upper()  # Convertir a mayúsculas y eliminar espacios extra
    #         name = name.replace("SALARIOS", "SALARIO").replace("INCENTIVOS", "INCENTIVO")  # Normalización
    #         return name
    # 
    #     # Obtener entradas de nómina (usando payslip_id correcto)
    #     inputs = self.env['hr.payslip.input'].search([('payslip_id', '=', payslip_id)])
    #     # Obtener líneas de nómina sin input_id
    #     lines = self.search([('slip_id', '=', payslip_id), ('input_id', '=', False)])
    # 
    #     # Diccionario con listas de IDs de input disponibles por nombre
    #     input_dict = {}
    #     for inp in inputs:
    #         norm_name = normalize_name(inp.name)
    #         if norm_name not in input_dict:
    #             input_dict[norm_name] = []
    #         input_dict[norm_name].append(inp.id)
    # 
    #     updated_count = 0
    #     for line in lines:
    #         norm_line_name = normalize_name(line.name)  # Normalizar nombre de la línea
    #         if norm_line_name in input_dict and input_dict[norm_line_name]:
    #             # Tomar el primer input disponible y eliminarlo de la lista
    #             line.input_id = input_dict[norm_line_name].pop(0)
    #             updated_count += 1
    # 
    #     self.env.cr.commit()  # Guardar cambios en la base de datos
    #     return f"Se actualizaron {updated_count} líneas de nómina."
    

    @api.depends('quantity', 'amount', 'rate')
    def _compute_total(self):
        for line in self:
            line.total = float(line.quantity) * line.amount * line.rate / 100
            # set to zero the amount of the salary rules belonging to the categories: BASIC, GROSS or NET
            line.amount = 0.0 if line.category_id.code \
                in ('BASIC', 'GROSS', 'NET') else line.amount


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    struct_id = fields.Many2one(
        comodel_name='hr.payroll.structure',
        string='Structure',
        required=True
    )

    def button_generate_payslips(self):
        _logger.info("Entrando en _generate_payslips")
        action = self.env["ir.actions.actions"]._for_xml_id("hr_payroll.action_hr_payslip_by_employees")
        action['context'] = dict(self.env.context, structure_id=self.struct_id.id if self.struct_id else False)
        return action

    def _get_report_base_filename(self):
        self.ensure_one()
        if self.state == 'close':
            return '%s - %s' % (_('Nómina Cerrada'), self.name.replace('/', ''))
        else:
            return '%s - %s' % (_('Nómina para Fines de Revisión'), self.name.replace('/', ''))

class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    structure_id = fields.Many2one(
        'hr.payroll.structure',
        string='Salary Structure',
        default=lambda self: self._get_structure_default()
    )

    def _get_structure_default(self):
        structure_id = self.env.context.get('structure_id')
        _logger.info(f"Valor de structure_id por defecto: {structure_id}")
        return structure_id
