# -*- coding: utf-8 -*-
# © 2024 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import pytz
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.osv import expression


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    def _get_available_contracts_domain(self):
        active_id = self.env.context.get('active_id')
        payslip_run = self.env['hr.payslip.run'].browse(active_id)
        employees_ids = payslip_run.slip_ids.mapped('employee_id').mapped('id')
        res = super(HrPayslipEmployees, self)._get_available_contracts_domain()
        # excludes employees with a payslip in the current payroll batch
        # and excludes the employee assigned to the admin user (user_id = 2)
        domain = [('id', 'not in', employees_ids), ('user_id', '!=', 2)]
        # excludes employees with unavailable contracts for the payroll batch period
        res = expression.AND([domain, res,
                             [('contract_ids.date_start', '<=', payslip_run.date_start),
                              '|',
                              ('contract_ids.date_end', '=', False),
                              ('contract_ids.date_end', '>=', payslip_run.date_end)]])
        # ****** TEST ******
        # res = [('id', '=', '0')]
        # ****** TEST ******
        return res

    def compute_sheet(self):
        self.ensure_one()
        active_id = self.env.context.get('active_id')
        payslip_run = self.env['hr.payslip.run'].browse(active_id)
        # set the salary structure of the current payroll batch
        self.structure_id = payslip_run.struct_id

        result = super(HrPayslipEmployees, self).compute_sheet()

        # Odoo's base wizard (hr_payroll/wizard/hr_payroll_payslips_by_employees.py)
        # builds this notification inside a loop that overwrites its own message on
        # every iteration, so with several employees in conflict it only ever shows
        # the last one and never says which employee it belongs to. We rebuild the
        # message here instead of touching the base module.
        if isinstance(result, dict) and result.get('tag') == 'display_notification':
            message = self._build_work_entry_conflict_message(payslip_run)
            if message:
                result['params']['message'] = message
                result['params']['sticky'] = True
        return result

    def _build_work_entry_conflict_message(self, payslip_run):
        conflicts = self.env['hr.work.entry'].search([
            ('employee_id', 'in', self.employee_ids.ids),
            ('state', '=', 'conflict'),
            ('date_start', '<=', payslip_run.date_end + relativedelta(days=1)),
            ('date_stop', '>=', payslip_run.date_start + relativedelta(days=-1)),
        ])
        if not conflicts:
            return False

        lines = []
        for employee in conflicts.employee_id.sorted('name'):
            entries = conflicts.filtered(lambda w: w.employee_id == employee)
            tz = pytz.timezone(employee.resource_calendar_id.tz or 'UTC')
            lines.append(_('Empleado: %s', employee.name))
            for entry in entries.sorted('date_start'):
                date_start = pytz.utc.localize(entry.date_start).astimezone(tz)
                date_stop = pytz.utc.localize(entry.date_stop).astimezone(tz)
                lines.append(' - %s -> %s' % (
                    date_start.strftime('%Y-%m-%d %H:%M'),
                    date_stop.strftime('%Y-%m-%d %H:%M'),
                ))
        return _('Entradas de trabajo en conflicto (hora local):\n%s', '\n'.join(lines))
