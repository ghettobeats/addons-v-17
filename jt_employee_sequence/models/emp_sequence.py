# -*- coding: utf-8 -*-
########################################################################################################################
#  Copyright (c) 2024 - Isjo Technology, SRL. (<https://isjo-technology.com/>)
#  Write by Daniel Diaz (daniel.diaz@isjo-technology.com)
#  See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class HREmployee(models.Model):
    _inherit = 'hr.employee'
    _description = "Generate employee sequence id"

    emp_id = fields.Char(string='Empleado Id', store=True)
    registration_number = fields.Char(string='Registration Number of the Employee', store=True, groups="hr.group_hr_user", copy=False)
    display_name = fields.Char(
        string='Nombre para mostrar',
        compute='_compute_display_name',
        store=True
    )

    @api.depends('emp_id', 'name')
    def name_get(self):
        result = []
        for record in self:
            emp_id = record.emp_id or ''
            name = record.name or ''
            display_name = f"{emp_id} - {name}" if emp_id and name else name or emp_id
            result.append((record.id, display_name))
        return result

    @api.depends('emp_id', 'name')
    def _compute_display_name(self):
        for record in self:
            emp_id = record.emp_id or ''
            name = record.name or ''
            record.display_name = f"{emp_id} - {name}" if emp_id and name else name or emp_id

    @api.model
    def create(self, values):
        values['emp_id'] = values['registration_number'] = self.env[
            'ir.sequence'].next_by_code('seqemp.seqemp')
        print(f"values: {values['registration_number']}")
        return super(HREmployee, self).create(values)
        

    _order = 'emp_id'
    _sql_constraints = [('emp_id_uniq', 'unique (emp_id)', 'The code employee must be unique')]
