# -*- coding: utf-8 -*-
# © 2024 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class CloneSalaryRuleWizardInherit(models.TransientModel):
    _inherit = 'clone.salary.rule.wizard'

    def clone_salary_rule(self):
        hr_salary_rule = self.env['hr.salary.rule']
        salary_rule_ids = hr_salary_rule.browse(self._context.get('active_ids', False))
        hr_payslip_input = self.env['hr.payslip.input.type']

        for salary_rule_id in salary_rule_ids:
            if salary_rule_id.is_clone:
                continue

            # Clonar la regla salarial
            values = {
                'name': salary_rule_id.name,
                'category_id': salary_rule_id.category_id.id,
                'code': salary_rule_id.code,
                'sequence': salary_rule_id.sequence,
                'struct_id': self.struct_id.id,
                'is_clone': True,
                'cloned_salary_rule_id': salary_rule_id.id,
                'appears_on_payslip': salary_rule_id.appears_on_payslip,
                'condition_select': salary_rule_id.condition_select,
                'condition_range': salary_rule_id.condition_range,
                'condition_range_min': salary_rule_id.condition_range_min,
                'condition_range_max': salary_rule_id.condition_range_max,
                'condition_python': salary_rule_id.condition_python,
                'amount_select': salary_rule_id.amount_select,
                'amount_percentage_base': salary_rule_id.amount_percentage_base,
                'quantity': salary_rule_id.quantity,
                'amount_fix': salary_rule_id.amount_fix,
                'amount_percentage': salary_rule_id.amount_percentage,
                'amount_python_compute': salary_rule_id.amount_python_compute,
                'partner_id': salary_rule_id.partner_id.id,
                'note': salary_rule_id.note,
                'account_debit': salary_rule_id.account_debit,
                'account_credit': salary_rule_id.account_credit,
                'analytic_account_id': salary_rule_id.analytic_account_id.id,
                'not_computed_in_net': salary_rule_id.not_computed_in_net,
            }
            new_rule = hr_salary_rule.create(values)

            # Verificar si existe una entrada para la regla clonada
            existing_entries = hr_payslip_input.search([('code', '=', str(salary_rule_id.code))])
            for entry in existing_entries:
                struct_ids = entry.struct_ids.ids if entry.struct_ids else []
                struct_ids.append(new_rule.struct_id.id)
                entry.write({'struct_ids': [(6, 0, struct_ids)]})

        notification_message = f'Se crearon {len(salary_rule_ids.ids)} regla(s) salarial(es) a la estructura salarial "{self.struct_id.name}"'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'title': 'Clonar Reglas Salariales',
                'message': notification_message,
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window_close',
                }
            }
        }
