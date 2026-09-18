# -*- coding: utf-8 -*-
# © 2026 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    payment_currency_id = fields.Many2one(
        'res.currency', string='Moneda de Pago',
        compute='_compute_payment_currency_id', store=True,
        help="Moneda de pago común a todos los recibos del lote. Vacío si "
             "el lote todavía no tiene recibos generados.")

    same_currency = fields.Boolean(compute='_compute_same_currency')

    payroll_currency_rate = fields.Float(
        string='Tasa de Cambio (RD$ por unidad)', digits=(12, 6),
        help="Tasa a aplicar a todos los recibos del lote que aún no estén "
             "confirmados/pagados. No se aplica sola al escribirla: hay "
             "que presionar 'Aplicar Tasa a los Recibos'.")

    @api.depends('slip_ids.payment_currency_id')
    def _compute_payment_currency_id(self):
        for run in self:
            currencies = run.slip_ids.payment_currency_id
            run.payment_currency_id = currencies if len(currencies) == 1 else False

    @api.depends('payment_currency_id', 'company_id.currency_id')
    def _compute_same_currency(self):
        for run in self:
            run.same_currency = not run.payment_currency_id \
                or run.payment_currency_id == run.company_id.currency_id

    def action_apply_payroll_currency_rate(self):
        for run in self:
            if not run.payroll_currency_rate:
                raise UserError(_("Ingresa primero una tasa de cambio para el lote."))
            slips = run.slip_ids.filtered(lambda s: s.state not in ('done', 'paid', 'cancel'))
            if not slips:
                raise UserError(_(
                    "No hay recibos en este lote que se puedan actualizar "
                    "(todos están confirmados/pagados)."))
            slips.write({'payroll_currency_rate': run.payroll_currency_rate})
            slips._compute_net_wage_currency()
