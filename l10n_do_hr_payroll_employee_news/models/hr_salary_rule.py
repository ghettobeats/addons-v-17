# -*- coding: utf-8 -*-
# © 2024 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models, fields, api


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'
    _description = 'HR Salary Rule'

    # appears_on_report = fields.Boolean("Aparece en el reporte de Excel")

    def unlink(self):
        hr_payslip_input = self.env['hr.payslip.input.type']

        for rule in self:
            # Buscar todas las entradas que tienen esta regla
            entries = hr_payslip_input.search([('code', '=', str(rule.code))])
            for entry in entries:
                # Eliminar la estructura de struct_ids
                struct_ids = entry.struct_ids.filtered(lambda s: s != rule.struct_id)
                entry.write({'struct_ids': [(6, 0, struct_ids.ids)]})

        return super(HrSalaryRule, self).unlink()
