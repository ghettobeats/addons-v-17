# -*- coding: utf-8 -*-

from odoo import api, fields, models


class HrContractHistory(models.Model):
    _inherit = "hr.contract.history"

    employee_class = fields.Selection(related="employee_id.structure_class")
    department_id = fields.Many2one(related="employee_id.department_id")
    # job_id = fields.Many2one(related="employee_id.job_id", store=True)
    # structure_type_id = fields.Many2one(store=True,
    #                                     compute="_compute_structure_type_id")

    @api.depends("employee_id", "employee_class")
    def _compute_structure_type_id(self):
        for rec in self:
            structure_types = self.env["hr.payroll.structure.type"].search([])
            selection_field = self.env["hr.employee"]._fields["structure_class"]._description_selection(self.env)
            structure_class = dict(selection_field).get(rec.employee_class)

            structure_type = [structure for structure in structure_types if structure_class in structure.name]
            if structure_type:
                rec.structure_type_id = structure_type[0].id
            else:
                rec.structure_type_id = False
