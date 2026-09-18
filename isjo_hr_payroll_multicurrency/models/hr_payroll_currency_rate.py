# -*- coding: utf-8 -*-
# © 2026 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HrPayrollCurrencyRate(models.Model):
    _name = 'hr.payroll.currency.rate'
    _description = 'Tasa de Cambio Fija para Nómina'
    _rec_name = 'currency_id'

    company_id = fields.Many2one(
        'res.company', string='Compañía', required=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', string='Moneda', required=True)
    rate = fields.Float(
        string='RD$ por Unidad', required=True, digits=(12, 6),
        help="Cantidad de Pesos Dominicanos (RD$) que equivale a 1 unidad "
             "de esta moneda, para efectos exclusivos de Nómina. Es "
             "independiente de la tasa de cambio que usa Contabilidad y "
             "solo se usa como sugerencia por defecto al calcular recibos "
             "de nómina; cada recibo puede ajustarla mientras esté en "
             "borrador.")

    _sql_constraints = [
        ('unique_currency_per_company', 'unique(company_id, currency_id)',
         'Ya existe una tasa de nómina configurada para esta moneda en esta compañía.'),
    ]

    @api.model
    def _get_rate(self, currency, company=None):
        """Tasa fija de nómina (RD$ por unidad) configurada para `currency`,
        o 0.0 si no hay ninguna configurada."""
        company = company or self.env.company
        record = self.search([
            ('company_id', '=', company.id),
            ('currency_id', '=', currency.id),
        ], limit=1)
        return record.rate
