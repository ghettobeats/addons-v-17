# -*- coding: utf-8 -*-

from odoo import fields, models


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    employee_identification_id = fields.Char("Número de identificación",
                                             related="employee_id.identification_id")
    employee_identification = fields.Char("Identificación",
                                          related="employee_id.identification")
    employee_department_id = fields.Many2one(string="Departamento",
                                             related="employee_id.department_id")
    employee_region = fields.Selection(string="Región",
                                       related="employee_id.region")
    
    