# -*- coding: utf-8 -*-
# © 2026 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

# Estados de hr.payslip a partir de los cuales la tasa y el equivalente en
# moneda de pago quedan bloqueados (ya no se recalculan).
LOCKED_STATES = ('done', 'paid', 'cancel')


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    # El campo base de hr.payslip es related='contract_id.currency_id'. En
    # este módulo, currency_id del contrato pasó a ser la moneda de pago
    # (editable), así que hay que anclar aquí a la moneda de la compañía
    # para que basic_wage/gross_wage/net_wage y las líneas de reglas
    # salariales (que heredan este currency_id vía hr.payslip.line) sigan
    # siempre en RD$, igual que en Odoo estándar.
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)

    payment_currency_id = fields.Many2one(
        related='contract_id.currency_id', string='Moneda de Pago', readonly=True)

    same_currency = fields.Boolean(compute='_compute_same_currency')

    @api.depends('currency_id', 'payment_currency_id')
    def _compute_same_currency(self):
        for slip in self:
            slip.same_currency = slip.currency_id == slip.payment_currency_id

    payroll_currency_rate = fields.Float(
        string='Tasa de Cambio (RD$ por unidad)', digits=(12, 6),
        compute='_compute_payroll_currency_rate', store=True, readonly=False,
        help="Tasa usada para calcular el equivalente del neto en la "
             "moneda de pago. Se sugiere automáticamente (tasa fija de "
             "Nómina configurada en Ajustes, o si no existe, la tasa de "
             "Contabilidad del día), pero puede ajustarse manualmente "
             "mientras el recibo esté en borrador o en espera. Al "
             "confirmar el recibo queda bloqueada.")

    net_wage_currency = fields.Monetary(
        string='Neto en Moneda de Pago', currency_field='payment_currency_id',
        compute='_compute_net_wage_currency', store=True, readonly=False,
        help="Equivalente informativo del neto (net_wage) en la moneda de "
             "pago del contrato, usando payroll_currency_rate. No "
             "participa en ningún cálculo de nómina, que siempre se hace "
             "en RD$. Queda bloqueado al confirmar el recibo.")

    @api.depends('payment_currency_id', 'currency_id', 'company_id', 'date_to')
    def _compute_payroll_currency_rate(self):
        for slip in self:
            if slip.state in LOCKED_STATES:
                continue
            if not slip.payment_currency_id or slip.same_currency:
                slip.payroll_currency_rate = 0.0
                continue
            fixed_rate = self.env['hr.payroll.currency.rate']._get_rate(
                slip.payment_currency_id, slip.company_id)
            slip.payroll_currency_rate = fixed_rate or slip.payment_currency_id._convert(
                1.0, slip.currency_id, slip.company_id,
                slip.date_to or fields.Date.context_today(slip), round=False)

    @api.depends('net_wage', 'payroll_currency_rate', 'same_currency')
    def _compute_net_wage_currency(self):
        for slip in self:
            if slip.state in LOCKED_STATES:
                continue
            if slip.same_currency or not slip.payroll_currency_rate:
                slip.net_wage_currency = slip.net_wage
            else:
                slip.net_wage_currency = slip.net_wage / slip.payroll_currency_rate

    def compute_sheet(self):
        # net_wage_currency depende de net_wage (que compute_sheet acaba de
        # recalcular) y de payroll_currency_rate (que depende del contrato,
        # related a través de otro modelo). El disparo automático de
        # @api.depends entre estas escrituras encadenadas no es confiable en
        # todos los casos, así que se fuerza el recálculo explícitamente
        # cada vez que se pulsa "Calcular hoja", igual que hace Odoo con
        # otros campos editables-y-calculados (ver sale.order.line.price_unit).
        res = super().compute_sheet()
        self._compute_payroll_currency_rate()
        self._compute_net_wage_currency()
        return res
