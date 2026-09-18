# -*- coding: utf-8 -*-
# © 2024 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models, fields, api
import base64
from datetime import datetime
import io
import pandas as pd
from itertools import groupby
from odoo.exceptions import UserError

class WizardInputImport(models.TransientModel):
    _name = 'wizard.input.import'
    _description = 'Wizard Input Import Batch News'
    
    hide = fields.Boolean(string='Cargar por Archivo', default=False)
    employee_ids = fields.Many2many(comodel_name='hr.employee', string='Empleados')
    input_id = fields.Many2one(comodel_name='hr.payslip.input.type', string='Novedad')
    amount = fields.Float(string='Importe')
    
    frecuency_type = fields.Selection(
        selection=[
            ('fixed', 'Fijo'),
            ('variable', 'Variable')
        ],
        string='Tipo de frecuencia',
        default='fixed'
    )
    
    apply_in = fields.Many2one(
        comodel_name='hr.payslip.run',
        string='Aplicar en',
        domain="[('state', '=', 'verify')]"
    )

    start_date = fields.Date(string='Fecha inicial')
    end_date = fields.Date(string='Fecha final')
    file_name = fields.Char()
    file_binary = fields.Binary(string='Archivo Excel')

    def action_process_excel(self):
        if not self.file_binary:
            raise UserError("Debe cargar un archivo Excel antes de procesarlo.")

        try:
            # Decodificar el archivo
            file_data = base64.b64decode(self.file_binary)
            # Leer el archivo con pandas
            excel_file = pd.read_excel(io.BytesIO(file_data))
    
            payslip_input_model = self.env['payslip.input.import']
    
            for index, row in excel_file.iterrows():
                # Validar el valor de going_to_lote
                going_to_lote = str(row.get('going_to_lote')).strip().lower()
                if going_to_lote not in ['verdadero', 'falso', 'true', 'false', 'True', 'False']:
                    raise UserError(
                        f"Error con la línea {index + 1} cargando el archivo Excel [{row.get('code_emp')}] - {row.get('employee')}, "
                        "referente a la frecuencia. Debe especificar si es 'verdadero' o 'falso'. Revíselos antes de procesar."
                    )
                
                emp = self.env['hr.employee'].search([('emp_id', '=', row.get('code_emp'))], limit=1)
                if not emp:
                    raise UserError(
                        f"Error con la linea {index + 1} cargando el archivo Excel [{row.get('code_emp')}] - {row.get('employee')} referente al empleado no fue encontrado, revisarlo antes de procesarlo ó remover la linea y vuelva a intentarlo.")
                input = self.env['hr.payslip.input.type'].search([('code', '=', row.get('code_input'))], limit=1)
                if not input:
                    raise UserError(
                        f"Error con la linea {index + 1} cargando el archivo Excel [{row.get('code_emp')}] - {row.get('employee')} referente a la entrada no fue encontrada, revisarlo antes de procesarlo ó remover la linea y vuelva a intentarlo.")
                # Validar datos requeridos
                if not row.get('date_start') or not row.get('date_end'):
                    raise UserError(f"Las fechas son obligatorias en la fila {index + 1}")
    
                # Convertir fechas a formato correcto
                # Asignar a end_date dependiendo de si la fecha es válida o no
                start_date = (
                    pd.to_datetime(row.get('date_start'), errors='coerce').date()  # Convertir a datetime si es válido
                    if row.get('date_start') and pd.notna(row.get('date_start'))  # Verificar que no sea None o NaT
                    else None  # Asignar None si está vacío o no es válido
                )
                end_date = (
                    pd.to_datetime(row.get('date_end'), errors='coerce').date()  # Convertir a datetime si es válido
                    if row.get('date_end') and pd.notna(row.get('date_end'))  # Verificar que no sea None o NaT
                    else None  # Asignar None si está vacío o no es válido
                )
    
                vals = {
                    'employee_id': emp.id,
                    'input_id': input.id,
                    'amount': row.get('amount'),
                    'frecuency_type': 'variable' if going_to_lote in ['verdadero', 'true'] else 'fixed',
                    'start_date': start_date,
                    'end_date': end_date,
                    'state': 'draft',  # Estado inicial
                }

                payslip_input_model_id = payslip_input_model.create(vals)

                # Verificar si el modelo creado tiene "apply_in" y la frecuencia es "variable"
                if vals.get('frecuency_type') == 'variable':
                    # Buscar todos los lotes en estado 'verify' o 'draft'
                    payslip_run_ids = self.env['hr.payslip.run'].search([('state', 'in', ('verify', 'draft'))])

                    for batch in payslip_run_ids:
                        # Verificar que todos los payslips del lote estén en estado 'verify' o 'draft'
                        if any(slip.state not in ('verify', 'draft') for slip in batch.slip_ids):
                            # Si hay un payslip no procesable, saltar este batch
                            continue

                        # Verificar si el batch contiene un payslip del empleado correspondiente
                        employee_slips = batch.slip_ids.filtered(
                            lambda slip: slip.employee_id.id == vals.get('employee_id'))
                        if not employee_slips:
                            # Si no hay un slip para este empleado, pasar al siguiente batch
                            continue

                        # Asignar el batch al campo 'apply_in' del modelo de entrada
                        payslip_input_model_id.apply_in = batch.id
                        payslip_input_model_id.action_confirm()
                        payslip_input_model_id.assign_rule_in_lote()

                        # Procesar los payslips relacionados con el empleado
                        for slip in employee_slips:
                            slip._remove_invalid_inputs(payslip=slip)
                            slip._add_fixed_inputs(payslip=slip)
                            slip.compute_sheet()
                else:
                    payslip_input_model_id.action_confirm()
                    payslip_input_model_id.assign_rule_in_lote()

        except Exception as e:
            raise UserError(f"Error al procesar el archivo: {str(e)}")

        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_create_massive_news(self):
        """Crea registros de `payslip.input.import` para los empleados seleccionados y verifica si están en el batch."""
        if not self.apply_in and self.frecuency_type == 'variable':
            raise UserError("Debe seleccionar un batch en el cual aplicar las novedades.")

        batch_employee_ids = None

        if self.apply_in and self.frecuency_type == 'variable':
            # Obtener los IDs de los empleados que están en el batch especificado
            batch_employee_ids = self.env['hr.payslip'].search([
                ('payslip_run_id', '=', self.apply_in.id),
                ('employee_id', 'in', self.employee_ids.ids)
            ]).mapped('employee_id.id')

            # Verificar si hay empleados seleccionados que no están en el batch
            non_batch_employees = self.employee_ids.filtered(lambda e: e.id not in batch_employee_ids)

            if non_batch_employees:
                employee_names = ', '.join(non_batch_employees.mapped('name'))
                raise UserError(f"Los siguientes empleados no están en el batch seleccionado: {employee_names}. "
                                "Asegúrese de agregarlos al batch antes de continuar.")

        # Crear las novedades para los empleados que están en el batch
        payslip_input_model = self.env['payslip.input.import']
        if batch_employee_ids:
            for employee in self.employee_ids:
                if employee.id in batch_employee_ids:
                    vals = {
                        'employee_id': employee.id,
                        'input_id': self.input_id.id,
                        'amount': self.amount,
                        'apply_in': self.apply_in.id,
                        'frecuency_type': self.frecuency_type,
                        'start_date': self.start_date,
                        'end_date': self.end_date,
                        'state': 'draft',  # Estado inicial
                    }
                    payslip_input_model.create(vals)
        else:
            for employee in self.employee_ids:
                vals = {
                    'employee_id': employee.id,
                    'input_id': self.input_id.id,
                    'amount': self.amount,
                    'frecuency_type': self.frecuency_type,
                    'start_date': self.start_date,
                    'end_date': self.end_date,
                    'state': 'draft',  # Estado inicial
                }
                payslip_input_model.create(vals)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',  # Para refrescar la vista actual una vez se complete el proceso
        }


# class WizardPayslipReportXlsx(models.TransientModel):
#     _name = 'wizard.payroll_report.xlsx'
#     _description = 'Wizard Payroll Report XLSX'
# 
#     payslip_run_ids = fields.One2many('wizard.payroll_report_line.xlsx', 'wizard_id',
#                                       string='Payslip Run',
#                                       required=1)
# 
#     num_document = fields.Boolean(default=1, string="Num. Document")
#     department = fields.Boolean(default=1, string="Department")
#     job = fields.Boolean(default=1, string="Job Position")
#     wage = fields.Boolean(default=1, string="Wage")
# 
#     filter_by = fields.Selection([
#         ('department', 'Department'),
#         ('job', 'Job'),
#     ], string='Filter BY')
# 
#     department_id = fields.Many2one('hr.department', string='By Department')
#     job_id = fields.Many2one('hr.job', string='By Job position')
# 
#     def _get_column_header(self, run_ids):
#         query = '''
#           select distinct l.code
#           from hr_payslip_line l, hr_salary_rule s
#           where l.salary_rule_id = s.id and slip_id in (
#             select id from hr_payslip where payslip_run_id in %s)
#           and l.total > 0
#         '''
#         self.env.cr.execute(query, (tuple(run_ids),))
# 
#         cols = self.env.cr.fetchall()
# 
#         return [col[0] for col in cols]
# 
#     def _get_data_line(self, run_ids, header):
# 
#         query = """
#           select contract_id, code, SUM(total)
#             from hr_payslip_line
#             where contract_id in (
#                 select contract_id from hr_payslip where payslip_run_id in %s)
#              and slip_id in (select id from hr_payslip where payslip_run_id in %s)
#              and code in %s group by contract_id, code
#             order by contract_id;
#         """
# 
#         self.env.cr.execute(query, (tuple(run_ids), tuple(run_ids), tuple(header)))
# 
#         return self.env.cr.fetchall()
# 
#     def _get_employee_info(self, run_ids):
#         extra = ''
#         if self.filter_by == 'department':
#             extra = 'and d.id = %d' % self.department_id.id
#         elif self.filter_by == 'job':
#             extra = 'and j.id = %d' % self.job_id.id
# 
#         query = """
#           SELECT DISTINCT c.id, e.name, e.identification_id, 
#             COALESCE(d.id, 0), COALESCE(d.name, '"Indefinido"'),
#             COALESCE(j.id, 0), COALESCE(j.name, '"Indefinido"'), c.wage
#           FROM hr_contract AS c 
#               INNER JOIN hr_employee AS e ON c.employee_id = e.id
#               INNER JOIN hr_payslip AS s ON s.contract_id = c.id
#               LEFT JOIN hr_job AS j ON j.id = c.job_id
#               LEFT JOIN hr_department AS d ON d.id = c.department_id
#           WHERE c.id IN (
#               SELECT contract_id FROM hr_payslip WHERE payslip_run_id in %s )
# 
#           ORDER BY e.name
#         """
#         self.env.cr.execute(query, (tuple(run_ids),))
# 
#         employees = self.env.cr.fetchall()
#         info = {
#             e[0]: {
#                 'employee_name': e[1],
#                 'num_document': e[2],
#                 'wage': e[7],
#                 'department_id': {'id': e[3], 'name': e[4]},
#                 'job_id': {'id': e[5], 'name': e[6]},
#                 'none': {'id': '', 'name': ' '},  # When not GroupBy
#             } for e in employees
#         }
#         return info
# 
#     def _get_data(self, run_ids):
#         filter = False
#         if self.filter_by == 'department':
#             filter = self.department_id.id
#         elif self.filter_by == 'job':
#             filter = self.job_id.id
# 
#         header = self._get_column_header(run_ids)
#         lines = self._get_data_line(run_ids, header)
#         info = self._get_employee_info(run_ids)
# 
#         # Default Dict with All Rule Salary in 0 (ZERO)
#         ddict = {k: 0 for k in header}
# 
#         data_lines = {}
#         for line in lines:
#             # contract_id
#             cid = line[0]
#             contract_name = self.env['hr.contract'].browse(cid).name
# 
#             if self.filter_by:
#                 opc = info[cid][self.filter_by + '_id']['id']
#                 if not opc or opc != filter:
#                     continue
# 
#             if cid not in data_lines:
#                 data_lines[cid] = ddict.copy()
# 
#                 if cid not in info:
#                     continue
# 
#                 name = info[cid]['employee_name']  # remove_special_letters(info[cid]['employee_name'])
# 
#                 data_lines[cid] = {
#                     'employee_name': name,
#                     'num_document': info[cid]['num_document'],
#                     'department_id': info[cid]['department_id'],
#                     'job_id': info[cid]['job_id'],
#                     'contract': contract_name,
#                     'wage': info[cid]['wage'],
#                 }
# 
#             data_lines[cid][line[1]] = line[2]
# 
#         return data_lines
# 
#     @api.onchange('filter_by')
#     def onchange_filter_by(self):
#         self.department_id = False
#         self.job_id = False
# 
#     def generate_report(self):
#         run_ids = [i.run_id.id for i in self.payslip_run_ids]
#         company_id = self.payslip_run_ids[0].run_id.company_id.logo
# 
#         data = self._get_data(run_ids)
# 
#         opcs_dict = {
#             'department': self.department,
#             'job': self.job,
#             'wage': self.wage,
#             'num_document': self.num_document,
#         }
# 
#         hidden = [k for k, v in opcs_dict.items() if v == False]
# 
#         data_sorted = sorted(data, key=lambda i: data[i]['department_id']['id'])
#         groups = groupby(data_sorted, key=lambda i: data[i]['department_id']['name'])
# 
#         data_groupby = {}
#         for key, vals in groups:
#             data_groupby[key] = []
# 
#             for v in vals:
#                 data_groupby[key].append(data[v])
# 
#         context = {
#             'lines': data,
#             'hidden': hidden,
#             'run_ids': run_ids,
#             'logo': company_id,
#             'data_groupby': data_groupby,
#         }
# 
#         return self.env.ref('payroll_report.template_xlsx').report_action(self, data=context)
# 
# 
# class WizardPayslipReportLineXlsx(models.TransientModel):
#     _name = 'wizard.payroll_report_line.xlsx'
#     _description = 'Wizard Payroll Report Line XLSX'
# 
#     wizard_id = fields.Many2one('wizard.payroll_report.xlsx')
# 
#     run_id = fields.Many2one(comodel_name='hr.payslip.run', string='Nomina', domain="[('state','in',('close','paid'))]")

