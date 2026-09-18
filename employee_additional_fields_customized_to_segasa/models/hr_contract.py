# -*- coding: utf-8 -*-

from odoo import api, fields, models


class HrContract(models.Model):
    _inherit = "hr.contract"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'employee_id' in vals:
                employee = self.env['hr.employee'].browse(vals['employee_id'])
                if employee:
                    vals['name'] = f"{employee.emp_id} CT {employee.name}"
                    # Agregar department_id y job_id
                    vals['department_id'] = employee.department_id.id
                    vals['job_id'] = employee.job_id.id
        return super(HrContract, self).create(vals_list)

    def write(self, vals):
        if 'employee_id' in vals or 'name' not in vals:
            for record in self:
                employee = record.employee_id if not vals.get('employee_id') else self.env['hr.employee'].browse(
                    vals['employee_id'])
                if employee:
                    vals['name'] = f"{employee.emp_id} CT {employee.name}"
                    # Agregar department_id y job_id
                    vals['department_id'] = employee.department_id.id
                    vals['job_id'] = employee.job_id.id
        return super(HrContract, self).write(vals)

    @api.onchange("employee_id")
    def _onchange_employee_id(self):
        if self.employee_id:
            self.name = f"{self.employee_id.emp_id} CT {self.employee_id.name}"
            self.department_id = self.employee_id.department_id or False
            self.job_id = self.employee_id.job_id or False
        else:
            self.name = ""
            self.department_id = False
            self.job_id = False

