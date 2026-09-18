# -*- coding: utf-8 -*-
# © 2024 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
from odoo.osv import expression


class HrPayslipEmployeesExtend(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    structure_class_ids = fields.Many2many(
        comodel_name='hr.structure.class',
        string='Classes',
        help="Filter employees by their assigned structure classes."
    )

    employee_ids = fields.Many2many(
        comodel_name='hr.employee',
        string='Employees',
        domain="[('structure_class_id', 'in', structure_class_ids)]",
        help="Employees filtered by department, classes, or other criteria."
    )

    from odoo.osv import expression

    def _get_available_contracts_domain(self):
        active_id = self.env.context.get('active_id')
        payslip_run = self.env['hr.payslip.run'].browse(active_id)
        employees_ids = payslip_run.slip_ids.mapped('employee_id').mapped('id')

        # Llamar al dominio base del super
        res = super(HrPayslipEmployeesExtend, self)._get_available_contracts_domain()

        # Excluir empleados con nóminas en el lote actual y al admin (user_id = 2)
        domain = [
            ('id', 'not in', employees_ids),
            ('user_id', '!=', 2),
        ]

        # Excluir contratos fuera del rango del lote de nómina
        contract_domain = [
            ('contract_ids.date_start', '<=', payslip_run.date_start),
            '|',
            ('contract_ids.date_end', '=', False),
            ('contract_ids.date_end', '>=', payslip_run.date_end),
        ]

        # Filtrar por las clases de estructura seleccionadas
        if self.structure_class_ids:
            class_domain = [
                ('contract_ids.employee_id.structure_class_id', 'in', self.structure_class_ids.ids)
            ]
            res = expression.AND([domain, res, contract_domain, class_domain])
        else:
            res = expression.AND([domain, res, contract_domain])

        return res

    @api.depends('department_id', 'structure_class_ids')
    def _compute_employee_ids(self):
        for wizard in self:
            # Obtén el dominio base para los contratos disponibles
            domain = wizard._get_available_contracts_domain()

            # Filtrar por departamento, si está seleccionado
            if wizard.department_id:
                domain = expression.AND([
                    domain,
                    [('department_id', 'child_of', wizard.department_id.id)]
                ])

            # Filtrar por clases de estructura seleccionadas
            if wizard.structure_class_ids:
                domain = expression.AND([
                    domain,
                    [('contract_ids.employee_id.structure_class_id', 'in', wizard.structure_class_ids.ids)]
                ])

            # Buscar empleados basados en el dominio combinado
            wizard.employee_ids = self.env['hr.employee'].search(domain)

    # @api.onchange('structure_class_ids', 'department_id')
    # def _onchange_structure_classes(self):
    #     """
    #     Update the available employees when structure_class_ids or department_id changes.
    #     """
    #     domain = []
    #     if self.structure_class_ids:
    #         domain.append(('contract_id.employee_id.structure_class_id', 'in', self.structure_class_ids.ids))
    #     if self.department_id:
    #         domain.append(('department_id', '=', self.department_id.id))
    # 
    #     return {'domain': {'employee_ids': domain}}

