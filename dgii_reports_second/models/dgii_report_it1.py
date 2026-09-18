# Part of Domincana Premium.
# See LICENSE file for full copyright and licensing details.
# © 2018 José López <jlopez@indexa.do>

import calendar
import base64
from datetime import datetime as dt
import pytz

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta

try:
    import pycountry
except ImportError:
    raise ImportError(
        _("This module needs pycountry to get 609 ISO 3166 "
          "country codes. Please install pycountry on your system. "
          "(See requirements file)"))


class DgiiReport(models.Model):
    _inherit = 'dgii.reports'

    compras_bsexentos = fields.Monetary()
    servicios_bsexentos = fields.Monetary()
    import_bsexentos = fields.Monetary()
    total_bsexentos = fields.Monetary(compute="compute_vertical_totals")
    compras_activos1 = fields.Monetary()
    servicios_activos1 = fields.Monetary()
    import_activos1 = fields.Monetary()
    total_activos1 = fields.Monetary(compute="compute_vertical_totals")
    compras_otrosnd = fields.Monetary()
    servicios_otrosnd = fields.Monetary()
    import_otrosnd = fields.Monetary()
    total_otrosnd = fields.Monetary(compute="compute_vertical_totals")
    compras_totalnd = fields.Monetary(compute="compute_vertical_totals")
    servicios_totalnd = fields.Monetary(compute="compute_vertical_totals")
    import_totalnd = fields.Monetary(compute="compute_vertical_totals")
    total_totalnd = fields.Monetary(compute="compute_vertical_totals")

    @api.depends('compras_bsexentos', 'servicios_bsexentos', 'import_bsexentos',
                 'compras_activos1', 'servicios_activos1', 'import_activos1',
                 'compras_otrosnd', 'servicios_otrosnd', 'import_otrosnd',)
    def compute_vertical_totals(self):
        for rec in self:
            rec.total_bsexentos = rec.compras_bsexentos + rec.servicios_bsexentos \
                                  + rec.import_bsexentos
            rec.total_activos1 = rec.compras_activos1 + rec.servicios_activos1 \
                                  + rec.import_activos1
            rec.total_otrosnd = rec.compras_otrosnd + rec.servicios_otrosnd \
                                 + rec.import_otrosnd
            rec.total_totalnd = rec.total_bsexentos + rec.total_activos1 \
                                + rec.total_otrosnd
            rec.compras_totalnd = rec.compras_bsexentos + rec.compras_activos1 \
                                + rec.compras_otrosnd
            rec.servicios_totalnd = rec.servicios_bsexentos + rec.servicios_activos1 \
                                  + rec.servicios_otrosnd
            rec.import_totalnd = rec.import_activos1 + rec.import_otrosnd \
                                    + rec.import_bsexentos

    def _compute_nd_anexoa(self):
        for rec in self:
            compras_bsexentos = 0.0
            servicios_bsexentos = 0.0
            import_bsexentos = 0.0
            compras_activos1 = 0.0
            servicios_activos1 = 0.0
            import_activos1 = 0.0
            compras_otrosnd = 0.0
            servicios_otrosnd = 0.0
            import_otrosnd = 0.0

            month, year = self.name.split('/')
            start_date = '{}-{}-01'.format(year, month)
            s_date = dt.strptime(start_date,
                                 '%Y-%m-%d').date()

            last_day = calendar.monthrange(int(year), int(month))[1]
            end_date = '{}-{}-{}'.format(year, month, last_day)

            invoice_ids_import = self.env['account.move'].search(
                [('invoice_date', '>=', start_date),
                 ('invoice_date', '<=', end_date),
                 ('company_id', '=', self.company_id.id),
                 ('state', 'in', ['posted', 'in_payment', 'paid']),
                 ('move_type', 'in', ['in_refund', 'in_invoice']),
                 ('import_itbis_amount', '>', 0)],
                order='invoice_date asc')

            invoice_ids = self._get_invoices(['posted', 'in_payment', 'paid'],
                                                    ['in_refund', 'in_invoice'])

            for inv in invoice_ids:
                if inv.invoice_date >= s_date and inv.amount_untaxed != 0:
                    if inv.clasificacion_itbis_compra == '01':
                        if inv.move_type == 'in_refund':
                            compras_bsexentos -= self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                               (inv.good_total_amount/inv.amount_untaxed) * inv.invoiced_itbis)
                            servicios_bsexentos -= self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                               (inv.service_total_amount / inv.amount_untaxed) * inv.invoiced_itbis)
                        else:
                            compras_bsexentos += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                               (inv.good_total_amount / inv.amount_untaxed) * inv.invoiced_itbis)
                            servicios_bsexentos += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                                 (inv.service_total_amount / inv.amount_untaxed) * inv.invoiced_itbis)
                    if inv.clasificacion_itbis_compra == '02':
                        if inv.move_type == 'in_refund':
                            compras_activos1 -= self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                               (inv.good_total_amount/inv.amount_untaxed) * inv.invoiced_itbis)
                            servicios_activos1 -= self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                               (inv.service_total_amount / inv.amount_untaxed) * inv.invoiced_itbis)
                        else:
                            compras_activos1 += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                               (inv.good_total_amount/inv.amount_untaxed) * inv.invoiced_itbis)
                            servicios_activos1 += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                               (inv.service_total_amount / inv.amount_untaxed) * inv.invoiced_itbis)
                    if inv.clasificacion_itbis_compra == '03':
                        if inv.move_type == 'in_refund':
                            compras_otrosnd -= self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                               (inv.good_total_amount/inv.amount_untaxed) * inv.invoiced_itbis)
                            servicios_otrosnd -= self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                               (inv.service_total_amount / inv.amount_untaxed) * inv.invoiced_itbis)
                        else:
                            compras_otrosnd += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                             (
                                                                                         inv.good_total_amount / inv.amount_untaxed) * inv.invoiced_itbis)
                            servicios_otrosnd += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                               (
                                                                                           inv.service_total_amount / inv.amount_untaxed) * inv.invoiced_itbis)

            for inv in invoice_ids_import:
                if inv.invoice_date >= s_date:
                    if inv.clasificacion_itbis_compra == '01':
                        import_bsexentos += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date, inv.import_itbis_amount)
                    if inv.clasificacion_itbis_compra == '02':
                        import_activos1 += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date, inv.import_itbis_amount)
                    if inv.clasificacion_itbis_compra == '03':
                        import_otrosnd += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date, inv.import_itbis_amount)

            rec.compras_bsexentos = compras_bsexentos
            rec.servicios_bsexentos = servicios_bsexentos
            rec.import_bsexentos = import_bsexentos
            rec.compras_activos1 = compras_activos1
            rec.servicios_activos1 = servicios_activos1
            rec.import_activos1 = import_activos1
            rec.compras_otrosnd = compras_otrosnd
            rec.servicios_otrosnd = servicios_otrosnd
            rec.import_otrosnd = import_otrosnd

    compras_pbexport = fields.Monetary()
    servicios_pbexport = fields.Monetary()
    import_pbexport = fields.Monetary()
    total_pbexport = fields.Monetary(compute="compute_vertical_totals_2")
    compras_pbgravados = fields.Monetary()
    servicios_pbgravados = fields.Monetary()
    import_pbgravados = fields.Monetary()
    total_pbgravados = fields.Monetary(compute="compute_vertical_totals_2")
    compras_sgravados = fields.Monetary()
    servicios_sgravados = fields.Monetary()
    import_sgravados = fields.Monetary()
    total_sgravados = fields.Monetary(compute="compute_vertical_totals_2")
    compras_totald = fields.Monetary(compute="compute_vertical_totals_2")
    servicios_totald = fields.Monetary(compute="compute_vertical_totals_2")
    import_totald = fields.Monetary(compute="compute_vertical_totals_2")
    total_totald = fields.Monetary(compute="compute_vertical_totals_2")

    @api.depends('compras_pbexport', 'servicios_pbexport', 'import_pbexport',
                 'compras_pbgravados', 'servicios_pbgravados', 'import_pbgravados',
                 'compras_sgravados', 'servicios_sgravados', 'import_sgravados', )
    def compute_vertical_totals_2(self):
        for rec in self:
            rec.total_pbexport = rec.compras_pbexport + rec.servicios_pbexport \
                                  + rec.import_pbexport
            rec.total_pbgravados = rec.compras_pbgravados + rec.servicios_pbgravados \
                                 + rec.import_pbgravados
            rec.total_sgravados = rec.compras_sgravados + rec.servicios_sgravados \
                                + rec.import_sgravados
            rec.compras_totald = rec.compras_pbexport + rec.compras_pbgravados \
                                + rec.compras_sgravados
            rec.servicios_totald = rec.servicios_pbexport + rec.servicios_pbgravados \
                                  + rec.servicios_sgravados
            rec.import_totald = rec.import_pbexport + rec.import_pbgravados \
                                    + rec.import_sgravados
            rec.total_totald = rec.total_pbexport + rec.total_pbgravados \
                                 + rec.total_sgravados

    def _compute_d_anexoa(self):
        for rec in self:
            compras_pbexport = 0.0
            servicios_pbexport = 0.0
            import_pbexport = 0.0
            compras_pbgravados = 0.0
            servicios_pbgravados = 0.0
            import_pbgravados = 0.0
            compras_sgravados = 0.0
            servicios_sgravados = 0.0
            import_sgravados = 0.0

            month, year = self.name.split('/')
            start_date = '{}-{}-01'.format(year, month)
            s_date = dt.strptime(start_date,
                                 '%Y-%m-%d').date()

            last_day = calendar.monthrange(int(year), int(month))[1]
            end_date = '{}-{}-{}'.format(year, month, last_day)

            invoice_ids_import = self.env['account.move'].search(
                [('invoice_date', '>=', start_date),
                 ('invoice_date', '<=', end_date),
                 ('company_id', '=', self.company_id.id),
                 ('state', 'in', ['posted', 'in_payment', 'paid']),
                 ('move_type', 'in', ['in_refund', 'in_invoice']),
                 ('import_itbis_amount', '>', 0)],
                order='invoice_date asc')

            invoice_ids = self._get_invoices(['posted', 'in_payment', 'paid'],
                                             ['in_refund', 'in_invoice'])

            for inv in invoice_ids:
                if inv.invoice_date >= s_date:
                    if inv.clasificacion_itbis_compra == '04' and inv.amount_untaxed != 0:
                        if inv.move_type == 'in_refund':
                            compras_pbexport -= self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                               (inv.good_total_amount / inv.amount_untaxed) * inv.invoiced_itbis)
                            servicios_pbexport -= self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                                 (inv.service_total_amount / inv.amount_untaxed) * inv.invoiced_itbis)
                        else:
                            compras_pbexport += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                          (inv.good_total_amount / inv.amount_untaxed) * inv.invoiced_itbis)
                            servicios_pbexport += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                    (inv.service_total_amount / inv.amount_untaxed) * inv.invoiced_itbis)

                    if inv.clasificacion_itbis_compra == '05' and inv.amount_untaxed != 0:
                        if inv.move_type == 'in_refund':
                            compras_pbgravados -= self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                              (inv.good_total_amount / inv.amount_untaxed) * inv.invoiced_itbis)
                            servicios_pbgravados -= self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                                (inv.service_total_amount / inv.amount_untaxed) * inv.invoiced_itbis)
                        else:
                            compras_pbgravados += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                                (inv.good_total_amount / inv.amount_untaxed) * inv.invoiced_itbis)
                            servicios_pbgravados += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                                  (inv.service_total_amount / inv.amount_untaxed) * inv.invoiced_itbis)

                    if inv.clasificacion_itbis_compra == '06' and inv.amount_untaxed != 0:
                        if inv.move_type == 'in_refund':
                            compras_sgravados -= self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                             (inv.good_total_amount / inv.amount_untaxed) * inv.invoiced_itbis)
                            servicios_sgravados -= self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                               (inv.service_total_amount / inv.amount_untaxed) * inv.invoiced_itbis)
                        else:
                            compras_sgravados += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                               (inv.good_total_amount / inv.amount_untaxed) * inv.invoiced_itbis)
                            servicios_sgravados += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                                 (inv.service_total_amount / inv.amount_untaxed) * inv.invoiced_itbis)

            for inv in invoice_ids_import:
                if inv.invoice_date >= s_date:
                    if inv.clasificacion_itbis_compra == '04':
                        if inv.move_type == 'in_refund':
                            import_pbexport -= self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                              inv.import_itbis_amount)
                        else:
                            import_pbexport += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                             inv.import_itbis_amount)
                    if inv.clasificacion_itbis_compra == '05':
                        if inv.move_type == 'in_refund':
                            import_pbgravados -= self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                             inv.import_itbis_amount)
                        else:
                            import_pbgravados += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                               inv.import_itbis_amount)
                    if inv.clasificacion_itbis_compra == '06':
                        if inv.move_type == 'in_refund':
                            import_sgravados -= self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                            inv.import_itbis_amount)
                        else:
                            import_sgravados += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                              inv.import_itbis_amount)

            rec.compras_pbexport = compras_pbexport
            rec.servicios_pbexport = servicios_pbexport
            rec.import_pbexport = import_pbexport
            rec.compras_pbgravados = compras_pbgravados
            rec.servicios_pbgravados = servicios_pbgravados
            rec.import_pbgravados = import_pbgravados
            rec.compras_sgravados = compras_sgravados
            rec.servicios_sgravados = servicios_sgravados
            rec.import_sgravados = import_sgravados

    compras_propor = fields.Monetary()
    servicios_propor = fields.Monetary()
    import_propor = fields.Monetary()
    total_propor = fields.Monetary(compute="compute_vertical_totals_3")
    coeficiente_propor = fields.Float(digits=(16, 2), compute="compute_proporcionalidad")
    calcular_proporcionalidad = fields.Boolean(string="Calcular proporcionalidad del ITBIS?", default=True)
    compras_propor_ad = fields.Monetary(compute="compute_vertical_totals_3")
    servicios_propor_ad = fields.Monetary(compute="compute_vertical_totals_3")
    import_propor_ad = fields.Monetary(compute="compute_vertical_totals_3")
    total_propor_ad = fields.Monetary(compute="compute_vertical_totals_3")
    total_propor_compras = fields.Monetary(compute="compute_vertical_totals_3")
    total_propor_servicios = fields.Monetary(compute="compute_vertical_totals_3")
    total_propor_import = fields.Monetary(compute="compute_vertical_totals_3")
    total_propor_total = fields.Monetary(compute="compute_vertical_totals_3")

    @api.depends('nograv_expo_bs342', 'nograv_destino', 'total_gravados',
                 'total_operaciones')
    def compute_proporcionalidad(self):
        for rec in self:
            if rec.calcular_proporcionalidad == True and rec.total_operaciones > rec.total_gravados and rec.total_gravados != 0.0:
                if rec.total_operaciones > 0:
                    rec.coeficiente_propor = ((rec.nograv_expo_bs342 + rec.nograv_destino + rec.total_gravados) / rec.total_operaciones) * 100
                else:
                    rec.coeficiente_propor = 0.0
            else:
                rec.coeficiente_propor = 0.0

    @api.depends('compras_propor', 'servicios_propor', 'import_propor',
                 'compras_propor_ad', 'servicios_propor_ad', 'import_propor_ad',)
    def compute_vertical_totals_3(self):
        for rec in self:
            rec.total_propor = rec.compras_propor + rec.servicios_propor \
                                 + rec.import_propor
            rec.compras_propor_ad = (rec.compras_propor * (rec.coeficiente_propor / 100)) if rec.coeficiente_propor > 0 else 0.0
            rec.servicios_propor_ad = (rec.servicios_propor * (rec.coeficiente_propor / 100)) if rec.coeficiente_propor > 0 else 0.0
            rec.import_propor_ad = (rec.import_propor * (rec.coeficiente_propor / 100)) if rec.coeficiente_propor > 0 else 0.0
            rec.total_propor_ad = rec.compras_propor_ad + rec.servicios_propor_ad \
                                   + rec.import_propor_ad
            rec.total_propor_compras = rec.compras_propor_ad + rec.compras_totald
            rec.total_propor_servicios = rec.servicios_propor_ad + rec.servicios_totald
            rec.total_propor_import = rec.import_propor_ad + rec.import_totald
            rec.total_propor_total = rec.total_propor_ad + rec.total_totald

    def _compute_propor_anexoa(self):
        for rec in self:
            compras_propor = 0.0
            servicios_propor = 0.0
            import_propor = 0.0

            month, year = self.name.split('/')
            start_date = '{}-{}-01'.format(year, month)
            s_date = dt.strptime(start_date,
                                 '%Y-%m-%d').date()

            last_day = calendar.monthrange(int(year), int(month))[1]
            end_date = '{}-{}-{}'.format(year, month, last_day)

            invoice_ids_import = self.env['account.move'].search(
                [('invoice_date', '>=', start_date),
                 ('invoice_date', '<=', end_date),
                 ('company_id', '=', self.company_id.id),
                 ('state', 'in', ['posted', 'in_payment', 'paid']),
                 ('move_type', 'in', ['in_refund', 'in_invoice']),
                 ('import_itbis_amount', '>', 0)],
                order='invoice_date asc')

            invoice_ids = self._get_invoices(['posted', 'in_payment', 'paid'],
                                             ['in_refund', 'in_invoice'])

            for inv in invoice_ids:
                if inv.invoice_date >= s_date:
                    if inv.clasificacion_itbis_compra == '07':
                        if inv.move_type == 'in_refund':
                            compras_propor -= self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                              (
                                                                                          inv.good_total_amount / inv.amount_untaxed) * inv.invoiced_itbis)
                            servicios_propor -= self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                                (
                                                                                            inv.service_total_amount / inv.amount_untaxed) * inv.invoiced_itbis)
                        else:
                            compras_propor += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                              (
                                                                                          inv.good_total_amount / inv.amount_untaxed) * inv.invoiced_itbis)
                            servicios_propor += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                                (
                                    inv.service_total_amount / inv.amount_untaxed) * inv.invoiced_itbis)

            for inv in invoice_ids_import:
                if inv.invoice_date >= s_date:
                    if inv.clasificacion_itbis_compra == '07':
                        if inv.move_type == 'in_refund':
                            import_propor -= self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                             inv.import_itbis_amount)
                        else:
                            import_propor += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                             inv.import_itbis_amount)

            rec.compras_propor = compras_propor
            rec.servicios_propor = servicios_propor
            rec.import_propor = import_propor

    nograv_expo_bs342 = fields.Monetary()
    nograv_expo_serv344 = fields.Monetary()
    nograv_expo_bs343y344 = fields.Monetary()
    nograv_destino = fields.Monetary()
    nograv_bienes_p3y4_343 = fields.Monetary()
    total_no_gravados = fields.Monetary(compute="_compute_no_gravados")
    total_gravados = fields.Monetary(compute="_compute_gravados")

    @api.depends('nograv_expo_bs342', 'nograv_expo_serv344', 'nograv_expo_bs343y344',
                 'nograv_destino', 'nograv_bienes_p3y4_343', 'import_propor_ad',
                 'construc_total_operaciones_exentas', 'comision_total_operaciones_exentas', 'total_operaciones')
    def _compute_gravados(self):
        for rec in self:
            rec.total_gravados = rec.total_operaciones - rec.total_no_gravados


    @api.depends('nograv_expo_bs342', 'nograv_expo_serv344', 'nograv_expo_bs343y344',
                 'nograv_destino', 'nograv_bienes_p3y4_343', 'import_propor_ad',
    'construc_total_operaciones_exentas','comision_total_operaciones_exentas', )
    def _compute_no_gravados(self):
        for rec in self:
            rec.total_no_gravados = rec.nograv_expo_bs342 + rec.nograv_expo_serv344 + rec.nograv_expo_bs343y344 + \
                                    rec.nograv_destino + rec.nograv_bienes_p3y4_343 + rec.import_propor_ad + rec.construc_total_operaciones_exentas \
                                    + rec.comision_total_operaciones_exentas


    def _compute_exentos_it1(self):
        for rec in self:
            nograv_expo_bs342 = 0.0
            nograv_expo_serv344 = 0.0
            nograv_expo_bs343y344 = 0.0
            nograv_destino = 0.0
            nograv_bienes_p3y4_343 = 0.0

            month, year = self.name.split('/')
            start_date = '{}-{}-01'.format(year, month)
            s_date = dt.strptime(start_date,
                                 '%Y-%m-%d').date()



            invoice_ids = self._get_invoices(['posted', 'in_payment', 'paid'],
                                             ['out_invoice'])

            for inv in invoice_ids:
                if inv.invoice_date >= s_date:
                    if inv.tipo_itbis_venta == '01':
                        base_imponible = 0.0
                        for line in inv.invoice_line_ids:
                            if line.tax_ids:
                                for tax in line.tax_ids:
                                    if tax.amount == 0.0 and tax.tax_group_id.name == 'ITBIS' and tax.amount_type != 'group':
                                        base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                    if tax.tax_group_id.name == 'ITBIS' and tax.amount_type == 'group':
                                        for taxes in tax.children_tax_ids:
                                            if taxes.amount == 0.0 and taxes.tax_group_id.name == 'ITBIS' and taxes.amount_type != 'group':
                                                base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                            if not line.tax_ids:
                                base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                        nograv_expo_bs342 += base_imponible
                    if inv.tipo_itbis_venta == '02':
                        base_imponible = 0.0
                        for line in inv.invoice_line_ids:
                            if line.tax_ids:
                                for tax in line.tax_ids:
                                    if tax.amount == 0.0 and tax.tax_group_id.name == 'ITBIS' and tax.amount_type != 'group':
                                        base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                    if tax.tax_group_id.name == 'ITBIS' and tax.amount_type == 'group':
                                        for taxes in tax.children_tax_ids:
                                            if taxes.amount == 0.0 and taxes.tax_group_id.name == 'ITBIS' and taxes.amount_type != 'group':
                                                base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                            if not line.tax_ids:
                                base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                        nograv_expo_serv344 += base_imponible
                    if inv.tipo_itbis_venta == '03':
                        base_imponible = 0.0
                        for line in inv.invoice_line_ids:
                            if line.tax_ids:

                                for tax in line.tax_ids:
                                    if tax.amount == 0.0 and tax.tax_group_id.name == 'ITBIS' and tax.amount_type != 'group':
                                        base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                    if tax.tax_group_id.name == 'ITBIS' and tax.amount_type == 'group':
                                        for taxes in tax.children_tax_ids:
                                            if taxes.amount == 0.0 and taxes.tax_group_id.name == 'ITBIS' and taxes.amount_type != 'group':
                                                base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                            if not line.tax_ids:
                                base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                        nograv_expo_bs343y344 += base_imponible
                    if inv.tipo_itbis_venta == '04':
                        base_imponible = 0.0
                        for line in inv.invoice_line_ids:
                            if line.tax_ids:
                                for tax in line.tax_ids:
                                    if tax.amount == 0.0 and tax.tax_group_id.name == 'ITBIS' and tax.amount_type != 'group':
                                        base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                    if tax.tax_group_id.name == 'ITBIS' and tax.amount_type == 'group':
                                        for taxes in tax.children_tax_ids:
                                            if taxes.amount == 0.0 and taxes.tax_group_id.name == 'ITBIS' and taxes.amount_type != 'group':
                                                base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                            if not line.tax_ids:
                                base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                        nograv_destino += base_imponible
                    if inv.tipo_itbis_venta == '13':
                        base_imponible = 0.0
                        for line in inv.invoice_line_ids:
                            if line.tax_ids:
                                for tax in line.tax_ids:
                                    if tax.amount == 0.0 and tax.tax_group_id.name == 'ITBIS' and tax.amount_type != 'group':
                                        base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                    if tax.tax_group_id.name == 'ITBIS' and tax.amount_type == 'group':
                                        for taxes in tax.children_tax_ids:
                                            if taxes.amount == 0.0 and taxes.tax_group_id.name == 'ITBIS' and taxes.amount_type != 'group':
                                                base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                            if not line.tax_ids:
                                base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                        nograv_bienes_p3y4_343 += base_imponible

            invoice_ids_credit = self._get_invoices(['posted', 'in_payment', 'paid'],
                                                    ['out_refund'])

            for inv in invoice_ids_credit:

                if inv.journal_id.l10n_latam_use_documents:
                    if inv.l10n_do_origin_ncf:
                        modified = False
                        modified = self.env['account.move'].search(
                            ['&', '&', ('l10n_latam_document_number', '=', inv.l10n_do_origin_ncf)
                                , ('partner_id', '=', inv.partner_id.id), ('state', '=', 'posted')
                                , ('move_type', '=', 'out_invoice'), ('company_id', '=', rec.company_id.id)])

                        for modifieds in modified:
                            if inv.l10n_do_origin_ncf == modifieds.l10n_latam_document_number and \
                                inv.tipo_itbis_venta != modifieds.tipo_itbis_venta:
                                raise UserError(_("La nota de credito %s no posee la misma asignacion de tipo "
                                                  "de itbis de venta que la factura %s. Esto podria traer inconsistencias "
                                                  "en la elaboracion del IT1. Favor corregir.", inv.name, modifieds.name))

                            if inv.l10n_do_origin_ncf == modifieds.l10n_latam_document_number:
                                origin_exento = 0.0
                                nc_exento = 0.0
                                for line in modifieds.invoice_line_ids:
                                    if line.tax_ids:
                                        for tax in line.tax_ids:
                                            if tax.amount == 0.0 and tax.tax_group_id.name == 'ITBIS' and tax.amount_type != 'group':
                                                origin_exento += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                            if tax.tax_group_id.name == 'ITBIS' and tax.amount_type == 'group':
                                                for taxes in tax.children_tax_ids:
                                                    if taxes.amount == 0.0 and taxes.tax_group_id.name == 'ITBIS' and taxes.amount_type != 'group':
                                                        origin_exento += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                    if not line.tax_ids:
                                        origin_exento += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                for line in inv.invoice_line_ids:
                                    if line.tax_ids:
                                        for tax in line.tax_ids:
                                            if tax.amount == 0.0 and tax.tax_group_id.name == 'ITBIS' and tax.amount_type != 'group':
                                                nc_exento += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                            if tax.tax_group_id.name == 'ITBIS' and tax.amount_type == 'group':
                                                for taxes in tax.children_tax_ids:
                                                    if taxes.amount == 0.0 and taxes.tax_group_id.name == 'ITBIS' and taxes.amount_type != 'group':
                                                        nc_exento += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                    if not line.tax_ids:
                                        nc_exento += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                if nc_exento > origin_exento and (inv.invoice_date - modifieds.invoice_date).days <= 30:
                                    raise UserError(_("La nota de credito %s tiene un valor exento mayor que la factura "
                                                      " %s afectada. Esto podria traer inconsistencias "
                                                      "en la elaboracion del IT1, pues la nota de credito si esta dentro "
                                                      "de los 30 dias deberia afectar el valor exento en la misma proporcion "
                                                      "o menor que lo facturado. Favor corregir.", inv.name,
                                                      modifieds.name))
                                origin_gravado = 0.0
                                nc_gravado = 0.0
                                for line in modifieds.invoice_line_ids:
                                    if line.tax_ids:
                                        for tax in line.tax_ids:
                                            if tax.amount > 0.0 and tax.tax_group_id.name == 'ITBIS' and tax.amount_type != 'group':
                                                origin_gravado += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal) * (tax.amount / 100)
                                            if tax.tax_group_id.name == 'ITBIS' and tax.amount_type == 'group':
                                                for taxes in tax.children_tax_ids:
                                                    origin_gravado += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal) * (taxes.amount / 100)
                                for line in inv.invoice_line_ids:
                                    if line.tax_ids:
                                        for tax in line.tax_ids:
                                            if tax.amount > 0.0 and tax.tax_group_id.name == 'ITBIS' and tax.amount_type != 'group':
                                                nc_gravado += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal) * (tax.amount / 100)
                                            if tax.tax_group_id.name == 'ITBIS' and tax.amount_type == 'group':
                                                for taxes in tax.children_tax_ids:
                                                    nc_gravado += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal) * (taxes.amount / 100)
                                if nc_gravado > origin_gravado and (inv.invoice_date - modifieds.invoice_date).days <= 30:
                                    raise UserError(_("La nota de credito %s tiene un valor gravado mayor que la factura "
                                                      " %s afectada. Esto podria traer inconsistencias "
                                                      "en la elaboracion del IT1, pues la nota de credito si esta dentro "
                                                      "de los 30 dias deberia afectar el valor gravado en la misma proporcion "
                                                      "o menor que lo facturado. Favor corregir.", inv.name,
                                                      modifieds.name))





                            if (inv.invoice_date - modifieds.invoice_date).days <= 30 and \
                                    inv.l10n_do_origin_ncf == modifieds.l10n_latam_document_number:
                                if inv.invoice_date >= s_date:
                                    if inv.tipo_itbis_venta == '01':
                                        base_imponible = 0.0
                                        for line in inv.invoice_line_ids:
                                            if line.tax_ids:
                                                for tax in line.tax_ids:
                                                    if tax.amount == 0.0 and tax.tax_group_id.name == 'ITBIS' and tax.amount_type != 'group':
                                                        base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                                    if tax.tax_group_id.name == 'ITBIS' and tax.amount_type == 'group':
                                                        for taxes in tax.children_tax_ids:
                                                            if taxes.amount == 0.0 and taxes.tax_group_id.name == 'ITBIS' and taxes.amount_type != 'group':
                                                                base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                            if not line.tax_ids:
                                                base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                        nograv_expo_bs342 -= base_imponible
                                    if inv.tipo_itbis_venta == '02':
                                        base_imponible = 0.0
                                        for line in inv.invoice_line_ids:
                                            if line.tax_ids:
                                                for tax in line.tax_ids:
                                                    if tax.amount == 0.0 and tax.tax_group_id.name == 'ITBIS' and tax.amount_type != 'group':
                                                        base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                                    if tax.tax_group_id.name == 'ITBIS' and tax.amount_type == 'group':
                                                        for taxes in tax.children_tax_ids:
                                                            if taxes.amount == 0.0 and taxes.tax_group_id.name == 'ITBIS' and taxes.amount_type != 'group':
                                                                base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                            if not line.tax_ids:
                                                base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                        nograv_expo_serv344 -= base_imponible
                                    if inv.tipo_itbis_venta == '03':
                                        base_imponible = 0.0
                                        for line in inv.invoice_line_ids:
                                            if line.tax_ids:
                                                for tax in line.tax_ids:
                                                    if tax.amount == 0.0 and tax.tax_group_id.name == 'ITBIS' and tax.amount_type != 'group':
                                                        base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                                    if tax.tax_group_id.name == 'ITBIS' and tax.amount_type == 'group':
                                                        for taxes in tax.children_tax_ids:
                                                            if taxes.amount == 0.0 and taxes.tax_group_id.name == 'ITBIS' and taxes.amount_type != 'group':
                                                                base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                            if not line.tax_ids:
                                                base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                        nograv_expo_bs343y344 -= base_imponible
                                    if inv.tipo_itbis_venta == '04':
                                        base_imponible = 0.0
                                        for line in inv.invoice_line_ids:
                                            if line.tax_ids:
                                                for tax in line.tax_ids:
                                                    if tax.amount == 0.0 and tax.tax_group_id.name == 'ITBIS' and tax.amount_type != 'group':
                                                        base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                                    if tax.tax_group_id.name == 'ITBIS' and tax.amount_type == 'group':
                                                        for taxes in tax.children_tax_ids:
                                                            if taxes.amount == 0.0 and taxes.tax_group_id.name == 'ITBIS' and taxes.amount_type != 'group':
                                                                base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                            if not line.tax_ids:
                                                base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                        nograv_destino -= base_imponible
                                    if inv.tipo_itbis_venta == '13':
                                        base_imponible = 0.0
                                        for line in inv.invoice_line_ids:
                                            if line.tax_ids:
                                                for tax in line.tax_ids:
                                                    if tax.amount == 0.0 and tax.tax_group_id.name == 'ITBIS' and tax.amount_type != 'group':
                                                        base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                                    if tax.tax_group_id.name == 'ITBIS' and tax.amount_type == 'group':
                                                        for taxes in tax.children_tax_ids:
                                                            if taxes.amount == 0.0 and taxes.tax_group_id.name == 'ITBIS' and taxes.amount_type != 'group':
                                                                base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                            if not line.tax_ids:
                                                base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                        nograv_bienes_p3y4_343 -= base_imponible



                    else:
                        if inv.journal_id.l10n_latam_use_documents:
                            raise UserError(_("La nota de credito %s no posee un NCF afectado. "
                                              "Favor corregir.", inv.name))

            rec.nograv_expo_bs342 = nograv_expo_bs342
            rec.nograv_expo_serv344 = nograv_expo_serv344
            rec.nograv_expo_bs343y344 = nograv_expo_bs343y344
            rec.nograv_destino = nograv_destino
            rec.nograv_bienes_p3y4_343 = nograv_bienes_p3y4_343


    grav_18 = fields.Monetary()
    grav_16 = fields.Monetary()
    grav_9 = fields.Monetary()
    grav_8 = fields.Monetary()
    grav_vactivos2y3 = fields.Monetary()
    cobrado_18 = fields.Monetary(compute="compute_itbis_cobrado")
    cobrado_16 = fields.Monetary(compute="compute_itbis_cobrado")
    cobrado_9 = fields.Monetary(compute="compute_itbis_cobrado")
    cobrado_8 = fields.Monetary(compute="compute_itbis_cobrado")
    cobrado_vactivos2y3 = fields.Monetary(compute="compute_itbis_cobrado")
    total_cobrado = fields.Monetary(compute="compute_itbis_cobrado")
    l_impuesto_pagar = fields.Monetary(compute="compute_itbis_cobrado")
    l_saldo_favor = fields.Monetary(compute="compute_itbis_cobrado")
    l_saldos_autorizados = fields.Monetary()
    l_saldo_favor_anterior = fields.Monetary()
    l_otros_pagos_computables = fields.Monetary()
    l_compen_y_reembol_autorizados = fields.Monetary()
    l_diferencia_pagar = fields.Monetary(compute="l_compute_suma_final")
    l_saldo_favor_final = fields.Monetary(compute="l_compute_suma_final")
    iv_recargos_porcentaje = fields.Float()
    iv_recargos = fields.Monetary()
    iv_interes_porcentaje = fields.Float()
    iv_interes = fields.Monetary()
    iv_sanciones = fields.Monetary()
    v_total_a_pagar = fields.Monetary(compute="compute_v_total_pagar")

    @api.depends('l_diferencia_pagar', 'iv_recargos', 'iv_interes',
                 'iv_sanciones')
    def compute_v_total_pagar(self):
        for rec in self:
            rec.v_total_a_pagar = rec.l_diferencia_pagar + rec.iv_recargos + rec.iv_interes \
                                  + rec.iv_sanciones


    @api.depends('l_impuesto_pagar', 'l_saldos_autorizados', 'l_saldo_favor_anterior',
                 'retcli_total_pagos_computables', 'l_otros_pagos_computables', 'l_otros_pagos_computables',
                 'l_otros_pagos_computables', 'l_otros_pagos_computables')
    def l_compute_suma_final(self):
        for rec in self:
            diferencia_a_pagar = 0.0
            saldo_a_favor = 0.0
            rec.l_diferencia_pagar = 0.0
            rec.l_saldo_favor_final = 0.0

            if rec.l_impuesto_pagar > 0:
                # raise UserError(_("%s", rec.l_impuesto_pagar - rec.l_saldos_autorizados - rec.l_saldo_favor_anterior \
                # - rec.retcli_total_pagos_computables - rec.l_otros_pagos_computables - rec.l_compen_y_reembol_autorizados))
                diferencia_a_pagar = rec.l_impuesto_pagar - rec.l_saldos_autorizados - rec.l_saldo_favor_anterior \
                - rec.retcli_total_pagos_computables - rec.l_otros_pagos_computables - rec.l_compen_y_reembol_autorizados

            elif rec.l_saldo_favor > 0:
                saldo_a_favor = rec.l_saldo_favor + rec.l_saldos_autorizados + rec.l_saldo_favor_anterior \
                + rec.retcli_total_pagos_computables + rec.l_otros_pagos_computables + rec.l_compen_y_reembol_autorizados

            if diferencia_a_pagar > 0:
                rec.l_diferencia_pagar = diferencia_a_pagar
            elif diferencia_a_pagar < 0:
                rec.l_saldo_favor_final = abs(diferencia_a_pagar)
            elif saldo_a_favor > 0:
                rec.l_saldo_favor_final = saldo_a_favor


    def compute_saldo_a_favor_ant(self):
        for rec in self:
            last_month = dt.strptime('01/' + rec.name,'%d/%m/%Y').date() - relativedelta(months=1)

            last_mont_str = (str(last_month.month) if len(str(last_month.month)) == 2 else '0' + str(last_month.month)) + '/' +  str(last_month.year)

            report_ant = self.env['dgii.reports'].search([('name', '=', last_mont_str),('company_id', '=', rec.company_id.id)])

            if report_ant:
                rec.l_saldo_favor_anterior = report_ant.l_saldo_favor_final
            else:
                rec.l_saldo_favor_anterior = 0.0




    @api.depends('grav_18', 'grav_16', 'grav_9',
                 'grav_8', 'grav_vactivos2y3')
    def compute_itbis_cobrado(self):
        for rec in self:
            rec.l_impuesto_pagar = 0.0
            rec.l_saldo_favor = 0.0
            rec.cobrado_18 = rec.grav_18 * 0.18
            rec.cobrado_16 = rec.grav_16 * 0.16
            rec.cobrado_9 = rec.grav_9 * 0.09
            rec.cobrado_8 = rec.grav_8 * 0.08
            rec.cobrado_vactivos2y3 = rec.grav_vactivos2y3 * 0.18
            rec.total_cobrado = rec.cobrado_18 + rec.cobrado_16 + rec.cobrado_9 + \
                                rec.cobrado_8 + rec.cobrado_vactivos2y3

            if (rec.total_cobrado - rec.total_propor_total) > 0:
                rec.l_impuesto_pagar = rec.total_cobrado - rec.total_propor_total
            elif (rec.total_cobrado - rec.total_propor_total) < 0:
                rec.l_saldo_favor = abs(rec.total_cobrado - rec.total_propor_total)
            else:
                rec.l_impuesto_pagar = 0.0
                rec.l_saldo_favor = 0.0




    def _compute_gravados_it1(self):
        for rec in self:
            grav_18 = 0.0
            grav_16 = 0.0
            grav_9 = 0.0
            grav_8 = 0.0
            grav_vactivos2y3 = 0.0

            month, year = self.name.split('/')
            start_date = '{}-{}-01'.format(year, month)
            s_date = dt.strptime(start_date,
                                 '%Y-%m-%d').date()



            invoice_ids = self._get_invoices(['posted', 'in_payment', 'paid'],
                                             ['out_invoice'])

            for inv in invoice_ids:
                if inv.invoice_date >= s_date:
                    for line in inv.invoice_line_ids:
                        for tax in line.tax_ids:
                            if tax.amount_type != 'group':
                                if tax.amount == 18.0 and inv.tipo_itbis_venta != '05':
                                    grav_18 += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                if tax.amount == 16.0:
                                    grav_16 += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                if tax.amount == 9.0:
                                    grav_9 += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                if tax.amount == 8.0:
                                    grav_8 += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                if tax.amount == 18.0 and inv.tipo_itbis_venta == '05':
                                    grav_vactivos2y3 += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                if tax.amount == 1.8 and inv.tipo_itbis_venta in ('08','09'):
                                    grav_18 += (self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal) * 0.10)
                            else:
                                for taxes in tax.children_tax_ids:
                                    if taxes.amount == 18.0 and inv.tipo_itbis_venta != '05':
                                        grav_18 += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                    if taxes.amount == 16.0:
                                        grav_16 += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                    if taxes.amount == 9.0:
                                        grav_9 += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                    if taxes.amount == 8.0:
                                        grav_8 += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                    if taxes.amount == 18.0 and inv.tipo_itbis_venta == '05':
                                        grav_vactivos2y3 += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                    if taxes.amount == 1.8 and inv.tipo_itbis_venta in ('08', '09'):
                                        grav_18 += (self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal) * 0.10)

            invoice_ids_credit = self._get_invoices(['posted', 'in_payment', 'paid'],
                                                    ['out_refund'])

            if rec.calcular_nc_30dias:
                for inv in invoice_ids_credit:

                    if inv.journal_id.l10n_latam_use_documents:
                        if inv.l10n_do_origin_ncf:
                            modified = False
                            modified = self.env['account.move'].search(
                                ['&', '&', ('l10n_latam_document_number', '=', inv.l10n_do_origin_ncf)
                                    , ('partner_id', '=', inv.partner_id.id), ('state', '=', 'posted')
                                    , ('move_type', '=', 'out_invoice'), ('company_id', '=', rec.company_id.id)])
                            for modifieds in modified:
                                if (inv.invoice_date - modifieds.invoice_date).days <= 30 and \
                                        inv.l10n_do_origin_ncf == modifieds.l10n_latam_document_number:
                                    if inv.invoice_date >= s_date:
                                        for line in inv.invoice_line_ids:
                                            for tax in line.tax_ids:
                                                if tax.amount_type != 'group':
                                                    if tax.amount == 18.0 and inv.tipo_itbis_venta != '05':
                                                        grav_18 -= self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                                    if tax.amount == 16.0:
                                                        grav_16 -= self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                                    if tax.amount == 9.0:
                                                        grav_9 -= self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                                    if tax.amount == 8.0:
                                                        grav_8 -= self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                                    if tax.amount == 18.0 and inv.tipo_itbis_venta == '05':
                                                        grav_vactivos2y3 -= self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                                    if tax.amount == 1.8 and inv.tipo_itbis_venta in ('08', '09'):
                                                        grav_18 -= (self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal) * 0.10)
                                                else:
                                                    for taxes in tax.children_tax_ids:
                                                        if taxes.amount == 18.0 and inv.tipo_itbis_venta != '05':
                                                            grav_18 -= self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                                        if taxes.amount == 16.0:
                                                            grav_16 -= self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                                        if taxes.amount == 9.0:
                                                            grav_9 -= self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                                        if taxes.amount == 8.0:
                                                            grav_8 -= self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                                        if taxes.amount == 18.0 and inv.tipo_itbis_venta == '05':
                                                            grav_vactivos2y3 -= self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                                        if taxes.amount == 1.8 and inv.tipo_itbis_venta in ('08', '09'):
                                                            grav_18 -= (self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal) * 0.10)

            rec.grav_18 = grav_18
            rec.grav_16 = grav_16
            rec.grav_9 = grav_9
            rec.grav_8 = grav_8
            rec.grav_vactivos2y3 = grav_vactivos2y3

    a_ret_servpf = fields.Monetary()
    a_ret_sernolucr = fields.Monetary()
    a_total_pfnl = fields.Monetary(compute="sum_a_retentions")
    a_ret_0709 = fields.Monetary()
    a_ret_0205_0707 = fields.Monetary()
    a_ret_rst_18 = fields.Monetary()
    a_ret_rst_16 = fields.Monetary()
    a_total_rst = fields.Monetary(compute="sum_a_retentions")
    a_ret_0519_18 = fields.Monetary()
    a_ret_0519_16 = fields.Monetary()
    a_total_0519 = fields.Monetary(compute="sum_a_retentions")

    a_total_nl_18 = fields.Monetary(compute="sum_a_retentions")
    a_total_0709_18 = fields.Monetary(compute="sum_a_retentions")
    a_total_0205y0707_18 = fields.Monetary(compute="sum_a_retentions")
    a_total_rst_18 = fields.Monetary(compute="sum_a_retentions")
    a_total_rst_16 = fields.Monetary(compute="sum_a_retentions")
    a_suma_rst = fields.Monetary(compute="sum_a_retentions")
    a_total_0519_18 = fields.Monetary(compute="sum_a_retentions")
    a_total_0519_16 = fields.Monetary(compute="sum_a_retentions")
    a_suma_0519 = fields.Monetary(compute="sum_a_retentions")
    a_itbis_perventa = fields.Monetary()
    a_impuesto_pagar = fields.Monetary(compute="sum_a_retentions")
    a_pago_cuenta = fields.Monetary()
    a_diferencia_pagar = fields.Monetary(compute="sum_a_retentions")
    a_nuevo_saldo_favor = fields.Monetary(compute="sum_a_retentions")
    b_recargos_porcentaje = fields.Float()
    b_recargos = fields.Monetary()
    b_interes_porcentaje = fields.Float()
    b_interes = fields.Monetary()
    b_sanciones = fields.Monetary()
    c_total_a_pagar = fields.Monetary(compute="sum_a_retentions")
    c_total_a_pagar_general = fields.Monetary(compute="sum_a_retentions")


    @api.depends('a_ret_servpf','a_ret_sernolucr','a_ret_0709','a_ret_0205_0707','a_ret_rst_18'
                 ,'a_ret_rst_16','a_ret_0519_18','a_ret_0519_16','a_itbis_perventa','a_pago_cuenta','b_recargos',
                 'b_interes','b_sanciones')
    def sum_a_retentions(self):
        for rec in self:
            rec.a_total_pfnl = rec.a_ret_servpf + rec.a_total_pfnl
            rec.a_total_rst = rec.a_ret_rst_18 + rec.a_ret_rst_16
            rec.a_total_0519 = rec.a_ret_0519_18 + rec.a_ret_0519_16
            rec.a_total_nl_18 = rec.a_total_pfnl * 0.18
            rec.a_total_0709_18 = rec.a_ret_0709 * 0.18
            rec.a_total_0205y0707_18 = (rec.a_ret_0205_0707 * 0.18) * 0.30
            rec.a_total_rst_18 = (rec.a_ret_rst_18 * 0.18)
            rec.a_total_rst_16 = (rec.a_ret_rst_16 * 0.16)
            rec.a_suma_rst = (rec.a_total_rst_18 + rec.a_total_rst_16)
            rec.a_total_0519_18 = (rec.a_ret_0519_18 * 0.18)
            rec.a_total_0519_16 = (rec.a_ret_0519_16 * 0.16)
            rec.a_suma_0519 = rec.a_total_0519_18 + rec.a_total_0519_16
            rec.a_impuesto_pagar = rec.a_total_nl_18 + rec.a_total_0709_18 + rec.a_total_0205y0707_18 + \
                rec.a_suma_rst + rec.a_suma_0519 + rec.a_itbis_perventa


            rec.a_diferencia_pagar = 0.0
            rec.a_nuevo_saldo_favor = 0.0

            if (rec.a_impuesto_pagar - rec.a_pago_cuenta) > 0:
                rec.a_diferencia_pagar = rec.a_impuesto_pagar - rec.a_pago_cuenta

            elif (rec.a_impuesto_pagar - rec.a_pago_cuenta) < 0:
                rec.a_nuevo_saldo_favor = abs(rec.a_impuesto_pagar - rec.a_pago_cuenta)

            rec.c_total_a_pagar = rec.a_diferencia_pagar + rec.b_recargos + rec.b_interes + rec.b_sanciones
            rec.c_total_a_pagar_general = rec.c_total_a_pagar + rec.v_total_a_pagar



    def _compute_retpurchase_it1(self):
        for rec in self:
            a_ret_servpf = 0.0
            a_ret_sernolucr = 0.0
            a_ret_0709 = 0.0
            a_ret_0205_0707 = 0.0
            a_ret_rst_18 = 0.0
            a_ret_rst_16 = 0.0
            a_ret_0519_18 = 0.0
            a_ret_0519_16 = 0.0

            month, year = self.name.split('/')
            last_day = calendar.monthrange(int(year), int(month))[1]
            start_date = '{}-{}-01'.format(year, month)
            end_date = '{}-{}-{}'.format(year, month, last_day)


            ret_payments = self.env['account.payment'].search(
                                [('state', '=', 'posted'),('payment_type', '=', 'outbound'), ('company_id', '=', rec.company_id.id),
                                 ('company_id', '=', rec.company_id.id),('withold_method', 'in', ('itbis','itbis_isr')),
                                 ('withold_method', 'in', ('itbis','itbis_isr')),('date', '>=', start_date),
                                 ('date', '<=', end_date)])



            for pay in ret_payments:
                if pay.withold_itbis_select.purchase_itbis_retention_type == '01':
                    a_ret_servpf += self._convert_to_DOP_currency(pay,False, pay.currency_id,pay.date,pay.withold_itbis_amount) / (abs(pay.withold_itbis_select.amount) / 100)
                if pay.withold_itbis_select.purchase_itbis_retention_type == '02':
                    a_ret_sernolucr += self._convert_to_DOP_currency(pay,False, pay.currency_id,pay.date,pay.withold_itbis_amount) / (abs(pay.withold_itbis_select.amount) / 100)
                if pay.withold_itbis_select.purchase_itbis_retention_type == '03':
                    a_ret_0709 += self._convert_to_DOP_currency(pay,False, pay.currency_id,pay.date,pay.withold_itbis_amount) / (abs(pay.withold_itbis_select.amount) / 100)
                if pay.withold_itbis_select.purchase_itbis_retention_type == '04':
                    a_ret_0205_0707 += self._convert_to_DOP_currency(pay,False, pay.currency_id,pay.date,pay.withold_itbis_amount) / (abs(pay.withold_itbis_select.amount) / 100)
                if pay.withold_itbis_select.purchase_itbis_retention_type == '05':
                    a_ret_rst_18 += self._convert_to_DOP_currency(pay,False, pay.currency_id,pay.date,pay.withold_itbis_amount) / (abs(pay.withold_itbis_select.amount) / 100)
                if pay.withold_itbis_select.purchase_itbis_retention_type == '06':
                    a_ret_rst_16 += self._convert_to_DOP_currency(pay,False, pay.currency_id,pay.date,pay.withold_itbis_amount) / (abs(pay.withold_itbis_select.amount) / 100)
                if pay.withold_itbis_select.purchase_itbis_retention_type == '07':
                    a_ret_0519_18 += self._convert_to_DOP_currency(pay,False, pay.currency_id,pay.date,pay.withold_itbis_amount) / (abs(pay.withold_itbis_select.amount) / 100)
                if pay.withold_itbis_select.purchase_itbis_retention_type == '08':
                    a_ret_0519_16 += self._convert_to_DOP_currency(pay,False, pay.currency_id,pay.date,pay.withold_itbis_amount) / (abs(pay.withold_itbis_select.amount) / 100)

            invoice_ids = self._get_invoices(['posted', 'in_payment', 'paid'],
                                             ['in_invoice', 'in_refund'])
            
            for inv in invoice_ids:
                if inv.move_type == 'in_invoice' and inv.payment_state in ('in_payment', 'paid'):
                    for line in inv.invoice_line_ids:
                        for tax in line.tax_ids:
                            if tax.amount_type != 'group' and 'ITBIS' in tax.tax_group_id.name and tax.amount < 0:

                                if tax.purchase_itbis_retention_type == '01':
                                    a_ret_servpf += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                if tax.purchase_itbis_retention_type == '02':
                                    a_ret_sernolucr += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                                  line.price_subtotal)
                                if tax.purchase_itbis_retention_type == '03':
                                    a_ret_0709 += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                                  line.price_subtotal)
                                if tax.purchase_itbis_retention_type == '04':
                                    a_ret_0205_0707 += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                                  line.price_subtotal)
                                if tax.purchase_itbis_retention_type == '05':
                                    a_ret_rst_18 += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                                  line.price_subtotal)
                                if tax.purchase_itbis_retention_type == '06':
                                    a_ret_rst_16 += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                                  line.price_subtotal)
                                if tax.purchase_itbis_retention_type == '07':
                                    a_ret_0519_18 += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                                  line.price_subtotal)
                                if tax.purchase_itbis_retention_type == '08':
                                    a_ret_0519_16 += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                                  line.price_subtotal)
                            elif tax.amount_type == 'group':
                                for taxes in tax.children_tax_ids:
                                    if taxes.amount_type != 'group' and 'ITBIS' in taxes.tax_group_id.name and taxes.amount < 0:
                                        if taxes.purchase_itbis_retention_type == '01':
                                            a_ret_servpf += self._convert_to_DOP_currency(False,inv, inv.currency_id,
                                                                                          inv.invoice_date,
                                                                                          line.price_subtotal)
                                        if taxes.purchase_itbis_retention_type == '02':
                                            a_ret_sernolucr += self._convert_to_DOP_currency(False,inv, inv.currency_id,
                                                                                             inv.invoice_date,
                                                                                             line.price_subtotal)
                                        if taxes.purchase_itbis_retention_type == '03':
                                            a_ret_0709 += self._convert_to_DOP_currency(False,inv, inv.currency_id,
                                                                                        inv.invoice_date,
                                                                                        line.price_subtotal)
                                        if taxes.purchase_itbis_retention_type == '04':
                                            a_ret_0205_0707 += self._convert_to_DOP_currency(False,inv, inv.currency_id,
                                                                                             inv.invoice_date,
                                                                                             line.price_subtotal)
                                        if taxes.purchase_itbis_retention_type == '05':
                                            a_ret_rst_18 += self._convert_to_DOP_currency(False,inv, inv.currency_id,
                                                                                          inv.invoice_date,
                                                                                          line.price_subtotal)
                                        if taxes.purchase_itbis_retention_type == '06':
                                            a_ret_rst_16 += self._convert_to_DOP_currency(False,inv, inv.currency_id,
                                                                                          inv.invoice_date,
                                                                                          line.price_subtotal)
                                        if taxes.purchase_itbis_retention_type == '07':
                                            a_ret_0519_18 += self._convert_to_DOP_currency(False,inv, inv.currency_id,
                                                                                           inv.invoice_date,
                                                                                           line.price_subtotal)
                                        if taxes.purchase_itbis_retention_type == '08':
                                            a_ret_0519_16 += self._convert_to_DOP_currency(False,inv, inv.currency_id,
                                                                                           inv.invoice_date,
                                                                                           line.price_subtotal)
                elif inv.move_type == 'in_refund' and inv.payment_state in ('in_payment', 'paid'):
                    for line in inv.invoice_line_ids:
                        for tax in line.tax_ids:
                            if tax.amount_type != 'group' and 'ITBIS' in tax.tax_group_id.name and tax.amount < 0:
                                if tax.purchase_itbis_retention_type == '01':
                                    a_ret_servpf -= self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                if tax.purchase_itbis_retention_type == '02':
                                    a_ret_sernolucr -= self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                                  line.price_subtotal)
                                if tax.purchase_itbis_retention_type == '03':
                                    a_ret_0709 -= self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                                  line.price_subtotal)
                                if tax.purchase_itbis_retention_type == '04':
                                    a_ret_0205_0707 -= self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                                  line.price_subtotal)
                                if tax.purchase_itbis_retention_type == '05':
                                    a_ret_rst_18 -= self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                                  line.price_subtotal)
                                if tax.purchase_itbis_retention_type == '06':
                                    a_ret_rst_16 -= self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                                  line.price_subtotal)
                                if tax.purchase_itbis_retention_type == '07':
                                    a_ret_0519_18 -= self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                                  line.price_subtotal)
                                if tax.purchase_itbis_retention_type == '08':
                                    a_ret_0519_16 -= self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                                  line.price_subtotal)
                            elif tax.amount_type == 'group':
                                for taxes in tax.children_tax_ids:
                                    if taxes.amount_type != 'group' and 'ITBIS' in taxes.tax_group_id.name and taxes.amount < 0:
                                        if taxes.purchase_itbis_retention_type == '01':
                                            a_ret_servpf -= self._convert_to_DOP_currency(False,inv, inv.currency_id,
                                                                                          inv.invoice_date,
                                                                                          line.price_subtotal)
                                        if taxes.purchase_itbis_retention_type == '02':
                                            a_ret_sernolucr -= self._convert_to_DOP_currency(False,inv, inv.currency_id,
                                                                                             inv.invoice_date,
                                                                                             line.price_subtotal)
                                        if taxes.purchase_itbis_retention_type == '03':
                                            a_ret_0709 -= self._convert_to_DOP_currency(False,inv, inv.currency_id,
                                                                                        inv.invoice_date,
                                                                                        line.price_subtotal)
                                        if taxes.purchase_itbis_retention_type == '04':
                                            a_ret_0205_0707 -= self._convert_to_DOP_currency(False,inv, inv.currency_id,
                                                                                             inv.invoice_date,
                                                                                             line.price_subtotal)
                                        if taxes.purchase_itbis_retention_type == '05':
                                            a_ret_rst_18 -= self._convert_to_DOP_currency(False,inv, inv.currency_id,
                                                                                          inv.invoice_date,
                                                                                          line.price_subtotal)
                                        if taxes.purchase_itbis_retention_type == '06':
                                            a_ret_rst_16 -= self._convert_to_DOP_currency(False,inv, inv.currency_id,
                                                                                          inv.invoice_date,
                                                                                          line.price_subtotal)
                                        if taxes.purchase_itbis_retention_type == '07':
                                            a_ret_0519_18 -= self._convert_to_DOP_currency(False,inv, inv.currency_id,
                                                                                           inv.invoice_date,
                                                                                           line.price_subtotal)
                                        if taxes.purchase_itbis_retention_type == '08':
                                            a_ret_0519_16 -= self._convert_to_DOP_currency(False,inv, inv.currency_id,
                                                                                           inv.invoice_date,
                                                                                           line.price_subtotal)

            rec.a_ret_servpf = a_ret_servpf
            rec.a_ret_sernolucr = a_ret_sernolucr
            rec.a_ret_0709 = a_ret_0709
            rec.a_ret_0205_0707 = a_ret_0205_0707
            rec.a_ret_rst_18 = a_ret_rst_18
            rec.a_ret_rst_16 = a_ret_rst_16
            rec.a_ret_0519_18 = a_ret_0519_18
            rec.a_ret_0519_16 = a_ret_0519_16

    def _compute_anexoa(self):
        res = super(DgiiReport, self)._compute_anexoa()
        for rec in self:
            rec._compute_nd_anexoa()
            rec._compute_d_anexoa()
            rec._compute_propor_anexoa()
            rec._compute_exentos_it1()
            rec._compute_gravados_it1()
            rec.compute_saldo_a_favor_ant()
            rec._compute_retpurchase_it1()

        return res







