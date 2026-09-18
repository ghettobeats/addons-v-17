# -*- coding: utf-8 -*-
# © 2026 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


class HrContract(models.Model):
    _inherit = 'hr.contract'

    # Moneda de la compañía (RD$), fija, usada como referencia para el
    # campo 'wage', que siempre debe expresarse en Peso Dominicano sin
    # importar la moneda de pago seleccionada en el contrato.
    company_currency_id = fields.Many2one(
        'res.currency', string='Moneda de la Compañía',
        related='company_id.currency_id', readonly=True, store=True)

    # El campo base 'currency_id' de hr.contract es un related readonly a
    # la moneda de la compañía. Lo convertimos en un campo editable para
    # que se pueda seleccionar la moneda en la que se le paga al empleado.
    currency_id = fields.Many2one(
        'res.currency', string='Moneda de Pago', related=False, readonly=False,
        default=lambda self: self.env.company.currency_id, tracking=True,
        help="Moneda en la que se le paga al empleado (USD, EUR, etc). "
             "El campo 'Salario' siempre se expresa en Peso Dominicano "
             "(RD$), independientemente de la moneda seleccionada aquí.")

    wage = fields.Monetary(currency_field='company_currency_id')

    # Equivalente puramente informativo del salario en la moneda de pago,
    # calculado con la tasa de cambio actual. No se usa para ningún cálculo
    # de nómina: todo el desarrollo de la nómina (reglas, TSS, ISR, etc.)
    # se hace siempre en la moneda de la compañía (wage, RD$).
    wage_currency = fields.Monetary(
        string='Salario en Moneda de Pago', currency_field='currency_id',
        compute='_compute_wage_currency',
        help="Equivalente del salario en la moneda de pago seleccionada, "
             "según la tasa de cambio vigente. Es solo informativo: la "
             "nómina siempre se calcula en Peso Dominicano (RD$).")

    same_currency = fields.Boolean(compute='_compute_same_currency')

    @api.depends('currency_id', 'company_currency_id')
    def _compute_same_currency(self):
        for contract in self:
            contract.same_currency = contract.currency_id == contract.company_currency_id

    @api.depends('wage', 'currency_id', 'company_currency_id')
    def _compute_wage_currency(self):
        for contract in self:
            if contract.currency_id and contract.company_currency_id \
                    and contract.currency_id != contract.company_currency_id:
                contract.wage_currency = contract.company_currency_id._convert(
                    contract.wage, contract.currency_id,
                    contract.company_id or self.env.company,
                    fields.Date.context_today(contract))
            else:
                contract.wage_currency = contract.wage
