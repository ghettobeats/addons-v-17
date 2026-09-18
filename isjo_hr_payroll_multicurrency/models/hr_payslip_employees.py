# -*- coding: utf-8 -*-
# © 2026 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, _
from odoo.exceptions import UserError


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    def compute_sheet(self):
        self._check_same_payment_currency()
        return super().compute_sheet()

    def _check_same_payment_currency(self):
        """Un lote de nómina debe pagarse en una sola moneda. Evita el
        error de mezclar, por accidente, empleados con distinta moneda de
        pago (currency_id del contrato) en un mismo lote."""
        self.ensure_one()
        employees = self.with_context(active_test=False).employee_ids
        if not employees:
            return

        payslip_run = False
        if self.env.context.get('active_id'):
            payslip_run = self.env['hr.payslip.run'].browse(self.env.context['active_id'])

        if payslip_run and payslip_run.date_start and payslip_run.date_end:
            contracts = employees._get_contracts(
                payslip_run.date_start, payslip_run.date_end, states=['open', 'close']
            ).filtered(lambda c: c.active)
        else:
            contracts = employees.contract_id

        currencies = contracts.mapped('currency_id')
        if payslip_run:
            currencies |= payslip_run.slip_ids.mapped('payment_currency_id')
        if len(currencies) > 1:
            detail = '\n'.join(
                '- %s: %s' % (contract.employee_id.name, contract.currency_id.name or '-')
                for contract in contracts
            )
            raise UserError(_(
                "Los empleados seleccionados no tienen todos la misma "
                "moneda de pago en su contrato. Un mismo lote de nómina "
                "debe pagarse en una sola moneda:\n%s", detail
            ))
