# Part of Domincana Premium.
# See LICENSE file for full copyright and licensing details.
# © 2018 José López <jlopez@indexa.do>
# © 2018 Gustavo Valverde <gustavo@iterativo.do>

import calendar
import base64
from datetime import datetime as dt
import pytz

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

try:
    import pycountry
except ImportError:
    raise ImportError(
        _("This module needs pycountry to get 609 ISO 3166 "
          "country codes. Please install pycountry on your system. "
          "(See requirements file)"))


class DgiiReportSaleSummary(models.Model):
    _name = 'dgii.reports.sale.summary'
    _description = "DGII Report Sale Summary"
    _order = 'sequence'

    name = fields.Char()
    sequence = fields.Integer()
    qty = fields.Integer()
    amount = fields.Monetary()

    def _get_l10n_do_ncf_types(self):
        """ Return a list of fiscal types and their respective sequence type to be used
        on sequences, journals and document types. """
        return [
            ("fiscal", "01"),
            ("consumer", "02"),
            ("debit_note", "03"),
            ("credit_note", "04"),
            ("informal", "11"),
            ("unique", "12"),
            ("minor", "13"),
            ("special", "14"),
            ("governmental", "15"),
            ("export", "16"),
            ("exterior", "17"),
            ("e-fiscal", "31"),
            ("e-consumer", "32"),
            ("e-debit_note", "33"),
            ("e-credit_note", "34"),
            ("e-informal", "41"),
            ("e-minor", "43"),
            ("e-special", "44"),
            ("e-governmental", "45"),
            ("in_fiscal", "01"),
            ("positive", "+"),
            ("negative", "-"),
        ]

    l10n_do_ncf_type = fields.Selection(
        selection="_get_l10n_do_ncf_types",
        string="NCF types",
        help="NCF types defined by the DGII that can be used to identify the"
             " documents presented to the government and that depends on the"
             " operation type, the responsibility of both the issuer and the"
             " receptor of the document",
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.user.company_id.currency_id)
    dgii_report_id = fields.Many2one('dgii.reports', ondelete='cascade')

class DgiiReportRetributionSummary(models.Model):
    _name = 'dgii.reports.ir17.retribution'
    _description = "DGII Report IR17 Retribution Summary"

    date = fields.Date(related='move_id.date', store=True, readonly=True, index=True, copy=False)
    move_id = fields.Many2one('account.move.line', string="Linea de movimiento relacionado", store=True)
    amount_original = fields.Monetary(string="Monto original", store=True, compute="_sum_debit_credit")
    amount_base = fields.Monetary(string="Monto base", store=True)
    account_retribution_type = fields.Selection([
        ('R10', 'Asignacion de vehiculo: 27% del 10%'),
        ('R20', 'Asignacion de vehiculo: 27% del 20%'),
        ('R30', 'Asignacion de vehiculo: 27% del 30%'),
        ('R40', 'Asignacion de vehiculo: 27% del 40%'),
        ('RA', 'Otras retribuciones complementarias: 27% sobre el total'),
    ], string='Account Retribution Type', copy=False, related='move_id.account_id.account_retribution_type', store=True)
    account_id = fields.Many2one('account.account', string='Account', related='move_id.account_id', store=True)
    amount_calculated = fields.Monetary(string="Impuesto (27%)", store=True)
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.user.company_id.currency_id)
    dgii_report_id = fields.Many2one('dgii.reports', ondelete='cascade', store=True)

    @api.depends('move_id')
    def _sum_debit_credit(self):
        for rec in self:
            if rec.move_id:
                rec.amount_original = rec.move_id.debit - rec.move_id.credit
            else:
                rec.amount_original = 0.0



class DgiiReport(models.Model):
    _name = 'dgii.reports'
    _description = "DGII Report"
    _inherit = ['mail.thread']

    def _compute_previous_report_pending(self):
        for report in self:
            previous = False
            if self.id:
                previous = self.search([('company_id', '=', report.company_id.id),
                                    ('state', 'in', ('draft', 'generated')),
                                    ('id', '!=', self.id)],
                                   order='create_date asc',
                                   limit=1)
            if previous:
                previous_date = dt.strptime('01/' + previous.name,
                                            '%d/%m/%Y').date()
                current_date = dt.strptime('01/' + self.name,
                                           '%d/%m/%Y').date()
                report.previous_report_pending = True if previous_date < \
                                                         current_date else False
            else:
                report.previous_report_pending = False

    name = fields.Char(string='Period', required=True, size=7)
    state = fields.Selection([('draft', 'New'), ('error', 'With error'),
                              ('generated', 'Generated'), ('sent', 'Sent')],
                             default='draft',
                             tracking=True,
                             copy=False)
    regenerate = fields.Selection([('orig', 'original'), ('rege', 'regenerated')], default='orig',
                                  tracking=True, copy='false')
    last_date_sent = fields.Date(string='Ultima fecha marcado como enviado', copy=False)
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.user.company_id.currency_id)
    company_id = fields.Many2one('res.company',
                                 'Company',
                                 default=lambda self: self.env.company.id,
                                 required=True)
    company_ids = fields.Many2many('res.company', 'dgii_res_company_users_rel', 'user_id', 'cid',
                                   string='Companies', default=lambda self: self.env.company.ids)

    company_vat = fields.Char(related='company_id.vat')
    previous_report_pending = fields.Boolean(
        compute='_compute_previous_report_pending')

    _sql_constraints = [
        ('name_unique', 'UNIQUE(name, company_id)',
         _("You cannot have more than one report by period."))
    ]

    def get_name_date(self):
        month, year = self.name.split('/')
        last_day = calendar.monthrange(int(year), int(month))[1]
        end_datestr = '{}-{}-{}'.format(year, month, last_day)
        end_date = dt.strptime(end_datestr, '%Y-%m-%d')
        return end_date

    def _compute_606_fields(self):
        for rec in self:
            data = {
                'purchase_records': 0,
                'service_total_amount': 0,
                'good_total_amount': 0,
                'purchase_invoiced_amount': 0,
                'purchase_invoiced_itbis': 0,
                'purchase_withholded_itbis': 0,
                'cost_itbis': 0,
                'advance_itbis': 0,
                'income_withholding': 0,
                'purchase_selective_tax': 0,
                'purchase_other_taxes': 0,
                'purchase_legal_tip': 0
            }
            purchase_line_ids = self.env['dgii.reports.purchase.line'].search([
                ('dgii_report_id', '=', rec.id)
            ])
            for inv in purchase_line_ids:
                data['purchase_records'] += 1
                if inv.fiscal_invoice_number:
                    if inv.fiscal_invoice_number[:3] in ('B04', 'E34'):
                        data['service_total_amount'] -= inv.service_total_amount if \
                            self.get_name_date().month == inv.invoice_date.month and \
                            self.get_name_date().year == inv.invoice_date.year else 0
                        data['good_total_amount'] -= inv.good_total_amount if \
                            self.get_name_date().month == inv.invoice_date.month and \
                            self.get_name_date().year == inv.invoice_date.year else 0
                        data['purchase_invoiced_amount'] -= inv.invoiced_amount if \
                            self.get_name_date().month == inv.invoice_date.month and \
                            self.get_name_date().year == inv.invoice_date.year else 0
                        data['purchase_invoiced_itbis'] -= inv.invoiced_itbis if \
                            self.get_name_date().month == inv.invoice_date.month and \
                            self.get_name_date().year == inv.invoice_date.year else 0
                        data['purchase_withholded_itbis'] -= inv.withholded_itbis
                        data['cost_itbis'] -= inv.cost_itbis if \
                            self.get_name_date().month == inv.invoice_date.month and \
                            self.get_name_date().year == inv.invoice_date.year else 0
                        data['advance_itbis'] -= inv.advance_itbis if \
                            self.get_name_date().month == inv.invoice_date.month and \
                            self.get_name_date().year == inv.invoice_date.year else 0
                        data['income_withholding'] -= inv.income_withholding
                        data['purchase_selective_tax'] -= inv.selective_tax if \
                            self.get_name_date().month == inv.invoice_date.month and \
                            self.get_name_date().year == inv.invoice_date.year else 0
                        data['purchase_other_taxes'] -= inv.other_taxes if \
                            self.get_name_date().month == inv.invoice_date.month and \
                            self.get_name_date().year == inv.invoice_date.year else 0
                        data['purchase_legal_tip'] -= inv.legal_tip if \
                            self.get_name_date().month == inv.invoice_date.month and \
                            self.get_name_date().year == inv.invoice_date.year else 0
                    else:
                        data['service_total_amount'] += inv.service_total_amount if \
                        self.get_name_date().month == inv.invoice_date.month and \
                        self.get_name_date().year == inv.invoice_date.year else 0
                        data['good_total_amount'] += inv.good_total_amount if \
                            self.get_name_date().month == inv.invoice_date.month and \
                            self.get_name_date().year == inv.invoice_date.year else 0
                        data['purchase_invoiced_amount'] += inv.invoiced_amount if \
                            self.get_name_date().month == inv.invoice_date.month and \
                            self.get_name_date().year == inv.invoice_date.year else 0
                        data['purchase_invoiced_itbis'] += inv.invoiced_itbis if \
                            self.get_name_date().month == inv.invoice_date.month and \
                            self.get_name_date().year == inv.invoice_date.year else 0
                        data['purchase_withholded_itbis'] += inv.withholded_itbis
                        data['cost_itbis'] += inv.cost_itbis if \
                            self.get_name_date().month == inv.invoice_date.month and \
                            self.get_name_date().year == inv.invoice_date.year else 0
                        data['advance_itbis'] += inv.advance_itbis if \
                            self.get_name_date().month == inv.invoice_date.month and \
                            self.get_name_date().year == inv.invoice_date.year else 0
                        data['income_withholding'] += inv.income_withholding
                        data['purchase_selective_tax'] += inv.selective_tax if \
                            self.get_name_date().month == inv.invoice_date.month and \
                            self.get_name_date().year == inv.invoice_date.year else 0
                        data['purchase_other_taxes'] += inv.other_taxes if \
                            self.get_name_date().month == inv.invoice_date.month and \
                            self.get_name_date().year == inv.invoice_date.year else 0
                        data['purchase_legal_tip'] += inv.legal_tip if \
                            self.get_name_date().month == inv.invoice_date.month and \
                            self.get_name_date().year == inv.invoice_date.year else 0        
                else:
                    data['service_total_amount'] += inv.service_total_amount if \
                        self.get_name_date().month == inv.invoice_date.month and \
                        self.get_name_date().year == inv.invoice_date.year else 0
                    data['good_total_amount'] += inv.good_total_amount if \
                        self.get_name_date().month == inv.invoice_date.month and \
                        self.get_name_date().year == inv.invoice_date.year else 0
                    data['purchase_invoiced_amount'] += inv.invoiced_amount if \
                        self.get_name_date().month == inv.invoice_date.month and \
                        self.get_name_date().year == inv.invoice_date.year else 0
                    data['purchase_invoiced_itbis'] += inv.invoiced_itbis if \
                        self.get_name_date().month == inv.invoice_date.month and \
                        self.get_name_date().year == inv.invoice_date.year else 0
                    data['purchase_withholded_itbis'] += inv.withholded_itbis
                    data['cost_itbis'] += inv.cost_itbis if \
                        self.get_name_date().month == inv.invoice_date.month and \
                        self.get_name_date().year == inv.invoice_date.year else 0
                    data['advance_itbis'] += inv.advance_itbis if \
                        self.get_name_date().month == inv.invoice_date.month and \
                        self.get_name_date().year == inv.invoice_date.year else 0
                    data['income_withholding'] += inv.income_withholding
                    data['purchase_selective_tax'] += inv.selective_tax if \
                        self.get_name_date().month == inv.invoice_date.month and \
                        self.get_name_date().year == inv.invoice_date.year else 0
                    data['purchase_other_taxes'] += inv.other_taxes if \
                        self.get_name_date().month == inv.invoice_date.month and \
                        self.get_name_date().year == inv.invoice_date.year else 0
                    data['purchase_legal_tip'] += inv.legal_tip if \
                        self.get_name_date().month == inv.invoice_date.month and \
                        self.get_name_date().year == inv.invoice_date.year else 0

            rec.purchase_records = data['purchase_records']
            rec.service_total_amount = data['service_total_amount']
            rec.good_total_amount = data['good_total_amount']
            rec.purchase_invoiced_amount = data['purchase_invoiced_amount']
            rec.purchase_invoiced_itbis = data['purchase_invoiced_itbis']
            rec.purchase_withholded_itbis = data['purchase_withholded_itbis']
            rec.cost_itbis = data['cost_itbis']
            rec.advance_itbis = data['advance_itbis']
            rec.income_withholding = data['income_withholding']
            rec.purchase_selective_tax = data['purchase_selective_tax']
            rec.purchase_other_taxes = data['purchase_other_taxes']
            rec.purchase_legal_tip = data['purchase_legal_tip']


    def _607_correct_summary(self, inv):
        if self.get_name_date().month == inv.invoice_date.month and \
            self.get_name_date().year == inv.invoice_date.year and \
            inv.fiscal_invoice_number[:3] in ('B02', 'E32') and \
            inv.invoiced_amount >= 250000:
                return True

        elif self.get_name_date().month == inv.invoice_date.month and \
            self.get_name_date().year == inv.invoice_date.year and \
            inv.fiscal_invoice_number[:3] in ('B02', 'E32') and \
            inv.invoiced_amount < 250000:
                return False

        elif self.get_name_date().month == inv.invoice_date.month and \
            self.get_name_date().year == inv.invoice_date.year:
            return True

        else:
            return False



    def _compute_607_fields(self):
        for rec in self:
            data = {
                'sale_records': 0,
                'sale_invoiced_amount': 0,
                'sale_invoiced_itbis': 0,
                'sale_withholded_itbis': 0,
                'sale_withholded_isr': 0,
                'sale_selective_tax': 0,
                'sale_other_taxes': 0,
                'sale_legal_tip': 0
            }
            sale_line_ids = self.env['dgii.reports.sale.line'].search([
                ('dgii_report_id', '=', rec.id)
            ])
            for inv in sale_line_ids:

                if inv.fiscal_invoice_number[:3] in ('B02', 'E32') and \
                            inv.invoiced_amount >= 250000:
                    data['sale_records'] += 1

                elif inv.fiscal_invoice_number[:3] in ('B02', 'E32') and \
                            inv.invoiced_amount < 250000:
                    data['sale_records'] += 0

                else:
                    data['sale_records'] += 1
                if inv.fiscal_invoice_number:
                    if inv.fiscal_invoice_number[:3] in ('B04', 'E34'):
                        data['sale_invoiced_amount'] -= inv.invoiced_amount if self._607_correct_summary(inv) else 0
                        data['sale_invoiced_itbis'] -= inv.invoiced_itbis if self._607_correct_summary(inv) else 0
                        data['sale_withholded_itbis'] -= inv.third_withheld_itbis
                        data['sale_withholded_isr'] -= inv.third_income_withholding
                        data['sale_selective_tax'] -= inv.selective_tax if self._607_correct_summary(inv) else 0
                        data['sale_other_taxes'] -= inv.other_taxes if self._607_correct_summary(inv) else 0
                        data['sale_legal_tip'] -= inv.legal_tip if self._607_correct_summary(inv) else 0
                else:
                    data['sale_invoiced_amount'] += inv.invoiced_amount if self._607_correct_summary(inv) else 0
                    data['sale_invoiced_itbis'] += inv.invoiced_itbis if self._607_correct_summary(inv) else 0
                    data['sale_withholded_itbis'] += inv.third_withheld_itbis
                    data['sale_withholded_isr'] += inv.third_income_withholding
                    data['sale_selective_tax'] += inv.selective_tax if self._607_correct_summary(inv) else 0
                    data['sale_other_taxes'] += inv.other_taxes if self._607_correct_summary(inv) else 0
                    data['sale_legal_tip'] += inv.legal_tip if self._607_correct_summary(inv) else 0



            rec.sale_records = data['sale_records']
            rec.sale_invoiced_amount = data['sale_invoiced_amount']
            rec.sale_invoiced_itbis = data['sale_invoiced_itbis']
            rec.sale_withholded_itbis = data['sale_withholded_itbis']
            rec.sale_withholded_isr = data['sale_withholded_isr']
            rec.sale_selective_tax = data['sale_selective_tax']
            rec.sale_other_taxes = data['sale_other_taxes']
            rec.sale_legal_tip = data['sale_legal_tip']

    def _compute_608_fields(self):
        for rec in self:
            cancel_line_ids = self.env['dgii.reports.cancel.line'].search([
                ('dgii_report_id', '=', rec.id)
            ])
            rec.cancel_records = len(cancel_line_ids)

    def _compute_609_fields(self):
        for rec in self:
            data = {
                'exterior_records': 0,
                'presumed_income': 0,
                'exterior_withholded_isr': 0,
                'exterior_invoiced_amount': 0
            }
            external_line_ids = self.env['dgii.reports.exterior.line'].search([
                ('dgii_report_id', '=', rec.id)
            ])
            for inv in external_line_ids:
                data['exterior_records'] += 1
                data['presumed_income'] += inv.presumed_income
                data['exterior_withholded_isr'] += inv.withholded_isr
                data['exterior_invoiced_amount'] += inv.invoiced_amount

            rec.exterior_records = abs(data['exterior_records'])
            rec.presumed_income = abs(data['presumed_income'])
            rec.exterior_withholded_isr = abs(data['exterior_withholded_isr'])
            rec.exterior_invoiced_amount = abs(
                data['exterior_invoiced_amount'])

    # 606
    purchase_records = fields.Integer(compute='_compute_606_fields')
    service_total_amount = fields.Monetary(compute='_compute_606_fields')
    good_total_amount = fields.Monetary(compute='_compute_606_fields')
    purchase_invoiced_amount = fields.Monetary(compute='_compute_606_fields')
    purchase_invoiced_itbis = fields.Monetary(compute='_compute_606_fields')
    purchase_withholded_itbis = fields.Monetary(compute='_compute_606_fields')
    cost_itbis = fields.Monetary(compute='_compute_606_fields')
    advance_itbis = fields.Monetary(compute='_compute_606_fields')
    income_withholding = fields.Monetary(compute='_compute_606_fields')
    purchase_selective_tax = fields.Monetary(compute='_compute_606_fields')
    purchase_other_taxes = fields.Monetary(compute='_compute_606_fields')
    purchase_legal_tip = fields.Monetary(compute='_compute_606_fields')
    purchase_filename = fields.Char()
    purchase_binary = fields.Binary(string='606 file')

    # 607
    sale_records = fields.Integer(compute='_compute_607_fields')
    sale_invoiced_amount = fields.Float(compute='_compute_607_fields')
    sale_invoiced_itbis = fields.Float(compute='_compute_607_fields')
    sale_withholded_itbis = fields.Float(compute='_compute_607_fields')
    sale_withholded_isr = fields.Float(compute='_compute_607_fields')
    sale_selective_tax = fields.Float(compute='_compute_607_fields')
    sale_other_taxes = fields.Float(compute='_compute_607_fields')
    sale_legal_tip = fields.Float(compute='_compute_607_fields')
    sale_filename = fields.Char()
    sale_binary = fields.Binary(string='607 file')

    # 608
    cancel_records = fields.Integer(compute='_compute_608_fields')
    cancel_filename = fields.Char()
    cancel_binary = fields.Binary(string='608 file')

    # 609
    exterior_records = fields.Integer(compute='_compute_609_fields')
    presumed_income = fields.Float(compute='_compute_609_fields')
    exterior_withholded_isr = fields.Float(compute='_compute_609_fields')
    exterior_invoiced_amount = fields.Float(compute='_compute_609_fields')
    exterior_filename = fields.Char()
    exterior_binary = fields.Binary(string='609 file')

    # IT-1
    ncf_sale_summary_ids = fields.One2many('dgii.reports.sale.summary',
                                           'dgii_report_id',
                                           string='Operations by NCF type',
                                           copy=False)
    cash = fields.Monetary('Cash', copy=False)
    bank = fields.Monetary('Check / Transfer / Deposit', copy=False)
    card = fields.Monetary('Credit Card / Debit Card', copy=False)
    credit = fields.Monetary('Credit', copy=False)
    bond = fields.Monetary('Gift certificates or vouchers', copy=False)
    swap = fields.Monetary('Swap', copy=False)
    others = fields.Monetary('Other Sale Forms', copy=False)
    sale_type_total = fields.Monetary('Total', copy=False)

    opr_income = fields.Monetary('Operations Income (No-Financial)',
                                 copy=False)
    fin_income = fields.Monetary('Financial Income', copy=False)
    ext_income = fields.Monetary('Extraordinary Income', copy=False)
    lea_income = fields.Monetary('Lease Income', copy=False)
    ast_income = fields.Monetary('Depreciable Assets Income', copy=False)
    otr_income = fields.Monetary('Others Income', copy=False)
    income_type_total = fields.Monetary('Total', copy=False, compute="sum_opr_income")

    # General Summary of Consumer Invoices
    csmr_ncf_qty = fields.Integer('Issued Consumer NCF Qty', copy=False)
    csmr_ncf_total_amount = fields.Monetary('Invoiced Amount Total',
                                            copy=False)
    csmr_ncf_total_itbis = fields.Monetary('Invoiced ITBIS Total', copy=False)
    csmr_ncf_total_isc = fields.Monetary('Selective Tax', copy=False)
    csmr_ncf_total_othr = fields.Monetary('Other Taxes Total', copy=False)
    csmr_ncf_total_lgl_tip = fields.Monetary('Legal Tip Total', copy=False)

    # General Summary of Consumer Invoices - Sale Form
    csmr_cash = fields.Monetary('Cash', copy=False)
    csmr_bank = fields.Monetary('Check / Transfer / Deposit', copy=False)
    csmr_card = fields.Monetary('Credit Card / Debit Card', copy=False)
    csmr_credit = fields.Monetary('Credit', copy=False)
    csmr_bond = fields.Monetary('Gift certificates or vouchers', copy=False)
    csmr_swap = fields.Monetary('Swap', copy=False)
    csmr_others = fields.Monetary('Other Sale Forms', copy=False)

    def _get_country_number(self, partner_id):
        """
        Returns ISO 3166 country number from partner
        country code
        """
        res = False
        if not partner_id.country_id:
            return False
        try:
            country = pycountry.countries.get(
                alpha_2=partner_id.country_id.code)
            res = country.numeric
        except AttributeError:
            return res
        return res

    def _validate_date_format(self, date):
        """Validate date format <MM/YYYY>"""
        if date is not None:
            error = _('Error. Date format must be MM/YYYY')
            if len(date) == 7:
                try:
                    dt.strptime(date, '%m/%Y')
                except ValueError:
                    raise ValidationError(error)
            else:
                raise ValidationError(error)

    @api.model
    def create(self, vals):
        self._validate_date_format(vals.get('name'))


        return super(DgiiReport, self).create(vals)

    def write(self, vals):
        self._validate_date_format(vals.get('name'))

        return super(DgiiReport, self).write(vals)

    @staticmethod
    def get_date_tuple(date):
        return date.year, date.month

    def _get_pending_invoices(self, states, types):

        period = dt.strptime(self.name, '%m/%Y')

        month, year = self.name.split('/')
        last_day = calendar.monthrange(int(year), int(month))[1]
        start_date = '{}-{}-01'.format(year, month)
        end_date = '{}-{}-{}'.format(year, month, last_day)

        invoice_ids = self.env['account.move'].search([
            ('fiscal_status', '=', 'normal'),
            ('payment_state', 'in', ('paid','in_payment')),
            ('state', 'in', states),
            ('payment_date', '>=', start_date),
            ('payment_date', '<=', end_date),
            ('invoice_date', '<', start_date),
            ('company_id', '=', self.company_id.id),
            ('move_type', 'in', types),
        ]).filtered(lambda inv: self.get_date_tuple(inv.payment_date) ==
                                (period.year, period.month))

        return invoice_ids

    def _get_invoices(self, states, types):
        """
        Given rec and state, return a recordset of invoices
        :param state: a list of invoice state
        :param type: a list of invoice type
        :return: filtered invoices
        """
        month, year = self.name.split('/')
        last_day = calendar.monthrange(int(year), int(month))[1]
        start_date = '{}-{}-01'.format(year, month)
        end_date = '{}-{}-{}'.format(year, month, last_day)

        invoice_ids = self.env['account.move'].search(
            [('invoice_date', '>=', start_date),
             ('invoice_date', '<=', end_date),
             ('company_id', '=', self.company_id.id),
             ('state', 'in', states),
             ('move_type', 'in', types),
             ('l10n_latam_document_type_id', '!=', False)],
            order='invoice_date asc').filtered(
            lambda inv: (inv.journal_id.type != 'others') or
                        (inv.journal_id.l10n_latam_use_documents is True))

        # Append pending invoces (fiscal_status = Partial, state = Paid)
        invoice_ids |= self._get_pending_invoices(states, types)

        return invoice_ids

    def formated_rnc_cedula(self, vat):
        if vat:
            if len(vat) in [9, 11]:
                id_type = 1 if len(vat) == 9 else 2
                return (vat.strip().replace('-', ''),
                        id_type) if not vat.isspace() else False
            else:
                return False
        else:
            return False

    def _get_formated_date(self, date):

        return dt.strptime(date, '%Y-%m-%d').strftime('%Y%m%d') \
            if isinstance(date, str) else date.strftime('%Y%m%d') \
            if date else ""

    def _get_formated_amount(self, amount):

        return str('{:.2f}'.format(abs(amount)))

    def process_606_report_data(self, values):

        RNC = str(values['rnc_cedula'] if values['rnc_cedula'] else "")
        ID_TYPE = str(values['identification_type']
                      if values['identification_type'] else "")
        EXP_TYPE = str(
            values['expense_type'] if values['expense_type'] else "")
        NCF = str(values['fiscal_invoice_number'])
        NCM = str(values['modified_invoice_number']
                  if values['modified_invoice_number'] else "")
        INV_DATE = str(self._get_formated_date(
            values['invoice_date']))
        PAY_DATE = str(self._get_formated_date(
            values['payment_date']))
        SERV_AMOUNT = self._get_formated_amount(values['service_total_amount'])
        GOOD_AMOUNT = self._get_formated_amount(values['good_total_amount'])
        INV_AMOUNT = self._get_formated_amount(values['invoiced_amount'])
        INV_ITBIS = self._get_formated_amount(values['invoiced_itbis'])
        WH_ITBIS = self._get_formated_amount(values['withholded_itbis'])
        PROP_ITBIS = self._get_formated_amount(values['proportionality_tax'])
        COST_ITBIS = self._get_formated_amount(values['cost_itbis'])
        ADV_ITBIS = self._get_formated_amount(values['advance_itbis'])
        PP_ITBIS = ''
        WH_TYPE = str(values['isr_withholding_type']
                      if values['isr_withholding_type'] else "")
        INC_WH = self._get_formated_amount(values['income_withholding'])
        PP_ISR = ''
        ISC = self._get_formated_amount(values['selective_tax'])
        OTHR = self._get_formated_amount(values['other_taxes'])
        LEG_TIP = self._get_formated_amount(values['legal_tip'])
        PAY_FORM = str(
            values['payment_type'] if values['payment_type'] else "")

        return "|".join([
            RNC, ID_TYPE, EXP_TYPE, NCF, NCM, INV_DATE, PAY_DATE, SERV_AMOUNT,
            GOOD_AMOUNT, INV_AMOUNT, INV_ITBIS, WH_ITBIS, PROP_ITBIS,
            COST_ITBIS, ADV_ITBIS, PP_ITBIS, WH_TYPE, INC_WH, PP_ISR, ISC,
            OTHR, LEG_TIP, PAY_FORM
        ])

    def _generate_606_txt(self, records, qty):

        company_vat = self.company_id.vat
        period = dt.strptime(self.name.replace('/', ''),
                             '%m%Y').strftime('%Y%m')

        header = "606|{}|{}|{}".format(
            str(company_vat), period, qty) + '\n'
        data = header + records

        file_path = '/tmp/DGII_606_{}_{}.txt'.format(company_vat, period)
        with open(file_path, 'w', encoding="utf-8", newline='\r\n') as txt_606:
            txt_606.write(str(data))

        self.write({
            'purchase_filename': file_path.replace('/tmp/', ''),
            'purchase_binary': base64.b64encode(open(file_path, 'rb').read())
        })

    def _include_in_current_report(self, invoice):
        """
        Evaluate if invoice was paid in current month or
        was included in a previous period.
        New reported invoices should not include any
        withholding amount nor payment date
        if payment was made after current period.
        :param invoice: account.move object
        :return: boolean
        """
        if not invoice.payment_date:
            return False

        payment_date = invoice.payment_date
        period = dt.strptime(self.name, '%m/%Y')
        same_minor_period = (payment_date.month,
                             payment_date.year) <= (period.month, period.year)

        return True if (payment_date and same_minor_period) else False

    def _convert_to_DOP_currency(self,pay,inv, base_currency, date, amount=0.0):
        user_company_id = self.env.user.company_id
        user_currency_id = self.env['res.currency'].browse(74)
        base_currency_id = base_currency

        if inv != False:
            if inv.recalculate_manual == True and inv.currency_rate > 0.0:
                amount_converted = inv.currency_rate * amount
                return amount_converted
            else:
                pass
        
        elif pay != False:
            if pay.tasa_manual == True and pay.payment_rate > 0.0:
                amount_converted = pay.payment_rate * amount
                return amount_converted
            else:
                pass

        return base_currency_id._convert(
            amount, user_currency_id, user_company_id, date)

    def _get_payment_form_regenerated(self, invi):

        inv = self.env['account.move'].search([('id', '=', invi)])
        payment_form = inv.payment_form

        if inv.payment_date:

            if (inv.payment_date.month != inv.invoice_date.month or inv.payment_date.year != inv.invoice_date.year) \
                    and self.regenerate == 'rege' and self.get_name_date().month == inv.payment_date.month \
                    and self.get_name_date().year == inv.payment_date.year:
                return payment_form

            elif inv.payment_date.month == inv.invoice_date.month and inv.payment_date.year == inv.invoice_date.year \
                    and self.regenerate == 'rege':
                return payment_form

            elif (inv.payment_date.month != inv.invoice_date.month or inv.payment_date.year != inv.invoice_date.year)\
                    and self.regenerate == 'rege':
                return '04' if inv.move_type != 'in_refund' else '06'

            elif self.regenerate == 'orig':
                return payment_form


        elif inv.payment_date is False:
            return payment_form

    def _compute_606_data(self):
        for rec in self:
            PurchaseLine = self.env['dgii.reports.purchase.line']
            PurchaseLine.search([('dgii_report_id', '=', rec.id)]).unlink()

            invoice_ids = self._get_invoices(['posted', 'in_payment', 'paid'],
                                             ['in_invoice', 'in_refund'])

            line = 0
            report_data = ''
            for inv in invoice_ids:
                inv.fiscal_status = 'blocked' if not inv.fiscal_status else \
                    inv.fiscal_status
                line += 1
                rnc_ced = self.formated_rnc_cedula(
                    inv.partner_id.vat
                ) if inv.move_type != 'exterior' else \
                    self.formated_rnc_cedula(
                        inv.company_id.vat)
                show_payment_date = self._include_in_current_report(inv)
                values = {
                    'dgii_report_id': rec.id,
                    'line': line,
                    'rnc_cedula': rnc_ced[0] if rnc_ced else False,
                    'identification_type': rnc_ced[1] if rnc_ced else False,
                    'expense_type': inv.l10n_do_expense_type
                    if inv.l10n_do_expense_type else False,
                    'fiscal_invoice_number': inv.l10n_latam_document_number,
                    'modified_invoice_number': inv.l10n_do_origin_ncf if
                    inv.move_type == 'in_refund' else False,
                    'invoice_date': inv.invoice_date,
                    'payment_date': inv.payment_date if
                    show_payment_date else False,
                    'service_total_amount': self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                          inv.service_total_amount),
                    'good_total_amount': self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                       inv.good_total_amount),
                    'invoiced_amount': self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                     inv.amount_untaxed),
                    'invoiced_itbis': self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                    inv.invoiced_itbis),
                    'proportionality_tax': self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                         inv.proportionality_tax),
                    'cost_itbis': self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date, inv.cost_itbis),
                    'advance_itbis': self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                   inv.advance_itbis),
                    'purchase_perceived_itbis': 0,  # Falta computar en la fact
                    'purchase_perceived_isr': 0,  # Falta computarlo en la fact
                    'isr_withholding_type': inv.isr_withholding_type if
                    show_payment_date else None,
                    'withholded_itbis': self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                      inv.withholded_itbis) if
                    show_payment_date else 0,
                    'income_withholding': self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                        inv.income_withholding) if
                    show_payment_date else 0,
                    'selective_tax': self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                   inv.selective_tax),
                    'other_taxes': self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date, inv.other_taxes),
                    'legal_tip': self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date, inv.legal_tip),
                    'payment_type': self._get_payment_form_regenerated(inv.id),
                    'invoice_partner_id': inv.partner_id.id,
                    'invoice_id': inv.id,
                    'credit_note': True if inv.move_type == 'in_refund' else False
                }
                PurchaseLine.create(values)
                report_data += self.process_606_report_data(values) + '\n'
            self._generate_606_txt(report_data, line)

    def _get_payments_dict(self):
        return {
            'cash': 0,
            'bank': 0,
            'card': 0,
            'credit': 0,
            'swap': 0,
            'bond': 0,
            'others': 0
        }

    def _convert_to_user_currency(self, base_currency, date, amount):
        user_company_id = self.env.user.company_id
        user_currency_id = self.env['res.currency'].browse(74)
        base_currency_id = base_currency

        return base_currency_id._convert(
            amount, user_currency_id, user_company_id, date)

    @staticmethod
    def include_payment(invoice_id, payment_id):
        """ Returns True if payment date is on or before current period """

        p_date = payment_id.payment_date
        i_date = invoice_id.invoice_date

        return True if (p_date.year <= i_date.year) and (
                p_date.month <= i_date.month) else False

    def _get_sale_payments_forms(self, invoice_id):
        payments_dict = self._get_payments_dict()
        Payment = self.env['account.payment']

        if invoice_id.move_type == 'out_invoice':
            for payment in invoice_id._get_invoice_payment_widget():
                payment_id = Payment.browse(payment['account_payment_id'])
                if payment_id:

                    key = payment_id.journal_id.l10n_do_payment_form if not payment_id.payment_method_id.l10n_do_payment_form else \
                        payment_id.payment_method_id.l10n_do_payment_form
                    # raise UserError(_("%s", payment_id.payment_method_id.l10n_do_payment_form))
                    if key and (self._include_in_current_report(invoice_id) or invoice_id.payment_state in ('paid', 'in_payment','partial')):
                        payments_dict[
                            key] += self._convert_to_user_currency(
                            invoice_id.currency_id, invoice_id.date, payment['amount'])

                    elif invoice_id.move_type == 'out_refund':
                        payments_dict[
                            'credit'] += self._convert_to_user_currency(
                            invoice_id.currency_id, invoice_id.date, payment['amount'])
                    else:
                        payments_dict[
                            'credit'] += self._convert_to_user_currency(
                            invoice_id.currency_id, invoice_id.date, payment['amount'])
                elif invoice_id.move_type == 'out_refund':
                    payments_dict[
                        'credit'] += self._convert_to_user_currency(
                        invoice_id.currency_id, invoice_id.date, payment['amount'])

                pay_journal = self.env['account.move'].search([('id', '=', payment['move_id'])])
                if pay_journal and not payment_id:
                    key2 = pay_journal.journal_id.l10n_do_payment_form
                    if key2 and self._include_in_current_report(invoice_id) or invoice_id.payment_state in ('paid', 'in_payment','partial') and \
                        pay_journal.move_type == 'entry':
                        payments_dict[
                            key2] += self._convert_to_user_currency(
                            invoice_id.currency_id, invoice_id.date, payment['amount'])
                    elif not key2 and self._include_in_current_report(invoice_id) or invoice_id.payment_state in ('paid', 'in_payment','partial') and \
                        pay_journal.move_type in ('entry', 'out_refund'):
                        payments_dict[
                            'credit'] += self._convert_to_user_currency(
                            invoice_id.currency_id, invoice_id.date, payment['amount'])


                elif not pay_journal and not payment_id:
                    payments_dict['credit'] += self._convert_to_user_currency(
                        invoice_id.currency_id, invoice_id.date, payment['amount'])

            if invoice_id.move_type == 'out_refund':
                payments_dict[
                    'credit'] += self._convert_to_user_currency(
                    invoice_id.currency_id, invoice_id.date, payment['amount'])
            else:
                payments_dict['credit'] += self._convert_to_user_currency(
                    invoice_id.currency_id, invoice_id.date, invoice_id.amount_residual)
        else:
            for payment in invoice_id._get_invoice_payment_widget():
                if invoice_id.move_type == 'out_refund':
                    payments_dict[
                    'credit'] += self._convert_to_user_currency(
                    invoice_id.currency_id, invoice_id.date, payment['amount'])
                else:
                    payments_dict['credit'] += self._convert_to_user_currency(
                        invoice_id.currency_id, invoice_id.date, payment['amount'])
            if invoice_id.move_type == 'out_refund':
                payments_dict[
                    'credit'] += self._convert_to_user_currency(
                    invoice_id.currency_id, invoice_id.date, invoice_id.amount_residual)
            else:
                payments_dict['credit'] += self._convert_to_user_currency(
                    invoice_id.currency_id, invoice_id.date, invoice_id.amount_residual)

        return payments_dict

    def _get_607_operations_dict(self):
        return {
            'fiscal': {
                'sequence': 1,
                'qty': 0,
                'amount': 0,
                'name': 'COMPROBANTE VÁLIDO PARA CRÉDITO FISCAL',
                'dgii_report_id': self.id,
                'l10n_do_ncf_type': 'fiscal',
            },
            'consumer': {
                'sequence': 2,
                'qty': 0,
                'amount': 0,
                'name': 'COMPROBANTE CONSUMIDOR FINAL',
                'dgii_report_id': self.id,
                'l10n_do_ncf_type': 'consumer',
            },
            'export': {
                'sequence': 3,
                'qty': 0,
                'amount': 0,
                'name': 'COMPROBANTE DE EXPORTACIONES',
                'dgii_report_id': self.id,
                'l10n_do_ncf_type': 'export',
            },
            'debit_note': {
                'sequence': 4,
                'qty': 0,
                'amount': 0,
                'name': 'COMPROBANTES NOTA DE DÉBITO',
                'dgii_report_id': self.id,
                'l10n_do_ncf_type': 'debit_note',
            },
            'credit_note': {
                'sequence': 5,
                'qty': 0,
                'amount': 0,
                'name': 'COMPROBANTES NOTA DE CRÉDITO',
                'dgii_report_id': self.id,
                'l10n_do_ncf_type': 'credit_note',
            },
            'unique': {
                'sequence': 6,
                'qty': 0,
                'amount': 0,
                'name': 'COMPROBANTE REGISTRO ÚNICO DE INGRESOS',
                'dgii_report_id': self.id,
                'l10n_do_ncf_type': 'unique',
            },
            'special': {
                'sequence': 8,
                'qty': 0,
                'amount': 0,
                'name': 'COMPROBANTE REGISTRO REGIMENES ESPECIALES',
                'dgii_report_id': self.id,
                'l10n_do_ncf_type': 'special',
            },
            'governmental': {
                'sequence': 9,
                'qty': 0,
                'amount': 0,
                'name': 'COMPROBANTES GUBERNAMENTALES',
                'dgii_report_id': self.id,
                'l10n_do_ncf_type': 'governmental',
            },
            'positive': {
                'sequence': 11,
                'qty': 0,
                'amount': 0,
                'name': 'OTRAS OPERACIONES (POSITIVAS) - *PENDIENTE*',
                'dgii_report_id': self.id,
                'l10n_do_ncf_type': 'positive',
            },
            'negative': {
                'sequence': 12,
                'qty': 0,
                'amount': 0,
                'name': 'OTRAS OPERACIONES (NEGATIVAS) - *PENDIENTE*',
                'dgii_report_id': self.id,
                'l10n_do_ncf_type': 'negative',
            },
        }

    def _process_op_dict(self, args, invoice):
        op_dict = args
        if invoice.l10n_do_income_type and invoice.move_type != 'out_refund' and invoice.l10n_latam_document_type_id.l10n_do_ncf_type not in ('debit_note','credit_note'):
            op_dict[invoice.l10n_latam_document_type_id.l10n_do_ncf_type]['qty'] += 1 if \
                    self.get_name_date().month == invoice.invoice_date.month and \
                    self.get_name_date().year == invoice.invoice_date.year else 0
            op_dict[invoice.l10n_latam_document_type_id.l10n_do_ncf_type][
                'amount'] += self._convert_to_DOP_currency(False,invoice, invoice.currency_id, invoice.invoice_date,
                                                           invoice.amount_untaxed) if \
                    self.get_name_date().month == invoice.invoice_date.month and \
                    self.get_name_date().year == invoice.invoice_date.year else 0
        if invoice.move_type == 'out_refund' and not invoice.move_type == 'in_refund' and invoice.l10n_latam_document_type_id.l10n_do_ncf_type not in ('debit_note'):
            op_dict['credit_note']['qty'] += 1 if \
                    self.get_name_date().month == invoice.invoice_date.month and \
                    self.get_name_date().year == invoice.invoice_date.year else 0
            op_dict['credit_note']['amount'] += self._convert_to_DOP_currency(False,invoice, invoice.currency_id, invoice.invoice_date,
                                                                     invoice.amount_untaxed) if \
                    self.get_name_date().month == invoice.invoice_date.month and \
                    self.get_name_date().year == invoice.invoice_date.year else 0
        if invoice.move_type == 'out_invoice' and invoice.l10n_latam_document_type_id.l10n_do_ncf_type in ('debit_note'):
            op_dict['debit_note']['qty'] += 1 if \
                    self.get_name_date().month == invoice.invoice_date.month and \
                    self.get_name_date().year == invoice.invoice_date.year else 0
            op_dict['debit_note']['amount'] += self._convert_to_DOP_currency(False,invoice, invoice.currency_id, invoice.invoice_date,
                                                                     invoice.amount_untaxed) if \
                    self.get_name_date().month == invoice.invoice_date.month and \
                    self.get_name_date().year == invoice.invoice_date.year else 0

        return op_dict

    def _set_payment_form_fields(self, payments_dict):
        for rec in self:
            rec.cash = payments_dict.get('cash')
            rec.bank = payments_dict.get('bank')
            rec.card = payments_dict.get('card')
            rec.credit = payments_dict.get('credit')
            rec.bond = payments_dict.get('bond')
            rec.swap = payments_dict.get('swap')
            rec.others = payments_dict.get('others')
            rec.sale_type_total = rec.cash + rec.bank + \
                                  rec.card + rec.credit + rec.bond + rec.swap + rec.others

    def _get_income_type_dict(self):
        return {'01': 0, '02': 0, '03': 0, '04': 0, '05': 0, '06': 0}

    def _process_income_dict(self, args, invoice):
        income_dict = args
        if invoice.l10n_do_income_type and invoice.move_type != 'out_refund':
            income_dict[invoice.l10n_do_income_type] += self._convert_to_DOP_currency(False,invoice, invoice.currency_id,
                                                                                      invoice.invoice_date,
                                                                                      invoice.amount_untaxed) if \
                    self.get_name_date().month == invoice.invoice_date.month and \
                    self.get_name_date().year == invoice.invoice_date.year else 0
        elif invoice.l10n_do_income_type and invoice.move_type == 'out_refund':
            income_dict[invoice.l10n_do_income_type] += -1 * self._convert_to_DOP_currency(False,invoice, invoice.currency_id,
                                                                                      invoice.invoice_date,
                                                                                      invoice.amount_untaxed) if \
                    self.get_name_date().month == invoice.invoice_date.month and \
                    self.get_name_date().year == invoice.invoice_date.year else 0
        return income_dict

    @api.onchange('opr_income', 'fin_income', 'ext_income', 'lea_income', 'ast_income',
                 'otr_income')
    def sum_opr_income(self):
        for rec in self:
            rec.income_type_total = \
                rec.opr_income + rec.fin_income + rec.ext_income + \
                rec.lea_income + rec.ast_income + rec.otr_income



    def _set_income_type_fields(self, income_dict):
        for rec in self:
            fin_income = 0.0
            rec.opr_income = income_dict.get('01')
            rec.fin_income = income_dict.get('02')
            rec.ext_income = income_dict.get('03')
            rec.lea_income = income_dict.get('04')
            rec.ast_income = income_dict.get('05')
            rec.otr_income = income_dict.get('06')

            if rec.calcular_ingresos_financieros_anexoa:
                month, year = self.name.split('/')
                last_day = calendar.monthrange(int(year), int(month))[1]
                start_date = '{}-{}-01'.format(year, month)
                end_date = '{}-{}-{}'.format(year, month, last_day)

                move_id = self.env['account.move.line'].search(
                    [('account_id.calcular_ingresos_financieros_anexoa', '=', True),
                     ('parent_state', '=', 'posted'),
                     ('date', '>=', start_date),
                     ('date', '<=', end_date),
                     ('company_id', '=', rec.company_id.id)
                     ])


                for line in move_id:
                    fin_income += line.debit - line.credit
            rec.fin_income += abs(fin_income)
            rec.income_type_total = \
                rec.opr_income + rec.fin_income + rec.ext_income + \
                rec.lea_income + rec.ast_income + rec.otr_income

    def process_607_report_data(self, values):

        RNC = str(values['rnc_cedula'] if values['rnc_cedula'] else "")
        ID_TYPE = str(values['identification_type']
                      if values['identification_type'] else "")
        NCF = str(values['fiscal_invoice_number'])
        NCM = str(values['modified_invoice_number']
                  if values['modified_invoice_number'] else "")
        INCOME_TYPE = str(values['income_type'])
        INV_DATE = str(self._get_formated_date(
            values['invoice_date']))
        WH_DATE = str(self._get_formated_date(
            values['withholding_date']))
        INV_AMOUNT = self._get_formated_amount(values['invoiced_amount'])
        INV_ITBIS = self._get_formated_amount(values['invoiced_itbis'])
        WH_ITBIS = self._get_formated_amount(values['third_withheld_itbis'])
        PRC_ITBIS = ''
        WH_ISR = self._get_formated_amount(values['third_income_withholding'])
        PCR_ISR = ''
        ISC = self._get_formated_amount(values['selective_tax'])
        OTH_TAX = self._get_formated_amount(values['other_taxes'])
        LEG_TIP = self._get_formated_amount(values['legal_tip'])
        CASH = self._get_formated_amount(values['cash'])
        BANK = self._get_formated_amount(values['bank'])
        CARD = self._get_formated_amount(values['card'])
        CRED = self._get_formated_amount(values['credit'])
        SWAP = self._get_formated_amount(values['swap'])
        BOND = self._get_formated_amount(values['bond'])
        OTHR = self._get_formated_amount(values['others'])

        return "|".join([
            RNC, ID_TYPE, NCF, NCM, INCOME_TYPE, INV_DATE, WH_DATE, INV_AMOUNT,
            INV_ITBIS, WH_ITBIS, PRC_ITBIS, WH_ISR, PCR_ISR, ISC, OTH_TAX,
            LEG_TIP, CASH, BANK, CARD, CRED, SWAP, BOND, OTHR
        ])

    def _generate_607_txt(self, records, qty):

        company_vat = self.company_id.vat
        period = \
            dt.strptime(self.name.replace('/', ''), '%m%Y').strftime('%Y%m')

        header = "607|{}|{}|{}".format(
            str(company_vat), period, qty) + '\n'
        data = header + records

        file_path = '/tmp/DGII_607_{}_{}.txt'.format(company_vat, period)
        with open(file_path, 'w', encoding="utf-8", newline='\r\n') as txt_607:
            txt_607.write(str(data))

        self.write({
            'sale_filename': file_path.replace('/tmp/', ''),
            'sale_binary': base64.b64encode(open(file_path, 'rb').read())
        })

    def _get_csmr_vals_dict(self):
        return {
            'csmr_ncf_qty': 0,
            'csmr_ncf_total_amount': 0,
            'csmr_ncf_total_itbis': 0,
            'csmr_ncf_total_isc': 0,
            'csmr_ncf_total_othr': 0,
            'csmr_ncf_total_lgl_tip': 0,
            'csmr_cash': 0,
            'csmr_bank': 0,
            'csmr_card': 0,
            'csmr_credit': 0,
            'csmr_bond': 0,
            'csmr_swap': 0,
            'csmr_others': 0
        }

    def _set_csmr_fields_vals(self, csmr_dict):
        self.write(csmr_dict)


    def _607_compute_correct_summary(self, inv):
        if self.get_name_date().month == inv.invoice_date.month and \
            self.get_name_date().year == inv.invoice_date.year and \
            inv.l10n_latam_document_number[:3]  in ('B02', 'E32') and \
                self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                              inv.amount_untaxed) >= 250000:
                return True

        elif self.get_name_date().month == inv.invoice_date.month and \
            self.get_name_date().year == inv.invoice_date.year and \
            inv.l10n_latam_document_number[:3]  in ('B02', 'E32') and \
                self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                              inv.amount_untaxed) < 250000:
                return False

        else:
            return True


    def _compute_607_data(self):
        for rec in self:
            SaleLine = self.env['dgii.reports.sale.line']
            SaleLine.search([('dgii_report_id', '=', rec.id)]).unlink()

            invoice_ids = self._get_invoices(['posted', 'in_payment', 'paid'],
                                             ['out_invoice', 'out_refund'])

            line = 0
            excluded_line = line
            op_dict = self._get_607_operations_dict()
            payment_dict = self._get_payments_dict()
            income_dict = self._get_income_type_dict()
            csmr_dict = self._get_csmr_vals_dict()
            monto_busqueda = []
            report_data = ''
            for inv in invoice_ids:
                op_dict = self._process_op_dict(op_dict, inv)
                income_dict = self._process_income_dict(income_dict, inv)
                inv.fiscal_status = \
                    'blocked' if not inv.fiscal_status else inv.fiscal_status


                if inv.partner_id.country_id.code == "DO":

                    if inv.fiscal_position_id.name == 'In process' and not inv.partner_id.vat and \
                            inv.l10n_latam_document_type_id.l10n_do_ncf_type == 'consumer' and \
                            self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                          inv.amount_untaxed) >= 250000:
                        rnc_ced = ('XINPROCESS',3)

                    elif inv.fiscal_position_id.name == 'In process' and inv.partner_id.vat and \
                            inv.l10n_latam_document_type_id.l10n_do_ncf_type == 'consumer' and \
                            self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                          inv.amount_untaxed) >= 250000:

                        rnc_ced = self.formated_rnc_cedula(inv.partner_id.vat)

                    elif inv.l10n_latam_document_type_id.l10n_do_ncf_type != 'unico':
                        rnc_ced = self.formated_rnc_cedula(inv.partner_id.vat)
                    else:
                        rnc_ced = self.formated_rnc_cedula(inv.company_id.vat)

                elif inv.partner_id.country_id.code != "DO":

                    if inv.fiscal_position_id.name == 'In process' and not inv.partner_id.vat and \
                            inv.l10n_latam_document_type_id.l10n_do_ncf_type == 'consumer' and \
                            self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                          inv.amount_untaxed) >= 250000:
                        rnc_ced = ('XINPROCESS',3)

                    elif inv.fiscal_position_id.name == 'In process' and inv.partner_id.vat and \
                            inv.l10n_latam_document_type_id.l10n_do_ncf_type == 'consumer' and \
                            self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                          inv.amount_untaxed) >= 250000:
                        rnc_ced = (inv.partner_id.vat,3)


                show_payment_date = self._include_in_current_report(inv)
                payments = self._get_sale_payments_forms(inv)
                values = {
                    'dgii_report_id': rec.id,
                    'line': line,
                    'rnc_cedula': rnc_ced[0] if rnc_ced else False,
                    'identification_type': rnc_ced[1] if rnc_ced else False,
                    'fiscal_invoice_number': inv.l10n_latam_document_number,
                    'modified_invoice_number':
                        inv.l10n_do_origin_ncf if inv.l10n_do_origin_ncf and
                                                  inv.l10n_do_origin_ncf[-10:-8] in ['01', '02', '14', '15'] else
                        False,
                    'income_type': inv.l10n_do_income_type,
                    'invoice_date': inv.invoice_date,
                    'withholding_date': inv.payment_date if (
                            inv.move_type != 'out_refund' and
                            show_payment_date) else False,
                    'invoiced_amount': self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                     inv.amount_untaxed),
                    'invoiced_itbis': self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                    inv.invoiced_itbis),
                    'third_withheld_itbis': self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                          inv.third_withheld_itbis)
                    if show_payment_date else 0,
                    'perceived_itbis': 0,  # Pendiente
                    'third_income_withholding': self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                              inv.third_income_withholding)
                    if show_payment_date else 0,
                    'perceived_isr': 0,  # Pendiente
                    'selective_tax': self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                   inv.selective_tax),
                    'other_taxes': self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date, inv.other_taxes),
                    'legal_tip': self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date, inv.legal_tip),
                    'invoice_partner_id': inv.partner_id.id,
                    'invoice_id': inv.id,
                    'credit_note': True if inv.move_type == 'out_refund' else False,
                    'cash': payments.get('cash'),
                    'bank': payments.get('bank'),
                    'card': payments.get('card'),
                    'credit': payments.get('credit'),
                    'swap': payments.get('swap'),
                    'bond': payments.get('bond'),
                    'others': payments.get('others'),
                    'is_csmr': False if self._607_compute_correct_summary(inv) else True,
                    'is_cs': True if str(inv.l10n_latam_document_number)[:3] in ('B02', 'E32') else False,
                }

                if str(values['fiscal_invoice_number'])[:3] in ('B02', 'E32'):
                    csmr_dict['csmr_ncf_qty'] += 1 if values['invoiced_amount'] < 250000 or values['invoiced_amount'] >= 250000 else 0
                    csmr_dict['csmr_ncf_total_amount'] += \
                        values['invoiced_amount'] if values['invoiced_amount'] < 250000 or values['invoiced_amount'] >= 250000 else 0
                    csmr_dict['csmr_ncf_total_itbis'] += \
                        values['invoiced_itbis'] if values['invoiced_amount'] < 250000 or values['invoiced_amount'] >= 250000 else 0
                    csmr_dict['csmr_ncf_total_isc'] += values['selective_tax'] if values['invoiced_amount'] < 250000 or values['invoiced_amount'] >= 250000 else 0
                    csmr_dict['csmr_ncf_total_othr'] += values['other_taxes'] if values['invoiced_amount'] < 250000 or values['invoiced_amount'] >= 250000 else 0
                    csmr_dict['csmr_ncf_total_lgl_tip'] += values['legal_tip'] if values['invoiced_amount'] < 250000 or values['invoiced_amount'] >= 250000 else 0
                    csmr_dict['csmr_cash'] += values['cash'] if values['invoiced_amount'] < 250000 or values['invoiced_amount'] >= 250000 else 0
                    csmr_dict['csmr_bank'] += values['bank'] if values['invoiced_amount'] < 250000 or values['invoiced_amount'] >= 250000 else 0
                    csmr_dict['csmr_card'] += values['card'] if values['invoiced_amount'] < 250000 or values['invoiced_amount'] >= 250000 else 0
                    csmr_dict['csmr_credit'] += values['credit'] if values['invoiced_amount'] < 250000 or values['invoiced_amount'] >= 250000 else 0
                    csmr_dict['csmr_bond'] += values['bond'] if values['invoiced_amount'] < 250000 or values['invoiced_amount'] >= 250000 else 0
                    csmr_dict['csmr_swap'] += values['swap'] if values['invoiced_amount'] < 250000 or values['invoiced_amount'] >= 250000 else 0
                    csmr_dict['csmr_others'] += values['others'] if values['invoiced_amount'] < 250000 or values['invoiced_amount'] >= 250000 else 0

                line += 1
                values.update({'line': line})
                SaleLine.create(values)
                if str(values['fiscal_invoice_number'])[:3] in ('B02', 'E32') and self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,inv.amount_untaxed) < 250000:
                    excluded_line += 1
                    # Excluye las facturas de Consumo
                    # con monto menor a 250000 solo del txt
                    pass
                else:
                    report_data += self.process_607_report_data(values) + '\n'


                for k in payment_dict:
                    if self.get_name_date().month == inv.invoice_date.month and \
                    self.get_name_date().year == inv.invoice_date.year:

                        if inv.move_type == 'out_refund':
                            payment_dict[k] += payments[k] * -1
                        else:
                            payment_dict[k] += payments[k]
                        # if payments[k] > 0.0 and k == 'bank':
                        #     monto_busqueda.append(inv.l10n_latam_document_number)


                    else:
                        continue

            for k in op_dict:
                self.env['dgii.reports.sale.summary'].create(op_dict[k])

            self._set_csmr_fields_vals(csmr_dict)
            self._set_payment_form_fields(payment_dict)
            self._set_income_type_fields(income_dict)
            self._generate_607_txt(report_data, line - excluded_line)

    def process_608_report_data(self, values):

        NCF = str(values['fiscal_invoice_number'])
        INV_DATE = str(self._get_formated_date(
            values['invoice_date']))
        ANU_TYPE = str(values['anulation_type'])

        return "|".join([NCF, INV_DATE, ANU_TYPE])

    def _generate_608_txt(self, records, qty):

        company_vat = self.company_id.vat
        period = dt.strptime(self.name.replace('/', ''),
                             '%m%Y').strftime('%Y%m')

        header = "608|{}|{}|{}".format(
            str(company_vat), period, qty) + '\n'
        data = header + records

        file_path = '/tmp/DGII_608_{}_{}.txt'.format(company_vat, period)
        with open(file_path, 'w', encoding="utf-8", newline='\r\n') as txt_608:
            txt_608.write(str(data))

        self.write({
            'cancel_filename': file_path.replace('/tmp/', ''),
            'cancel_binary': base64.b64encode(open(file_path, 'rb').read())
        })

    def _compute_608_data(self):
        for rec in self:
            CancelLine = self.env['dgii.reports.cancel.line']
            CancelLine.search([('dgii_report_id', '=', rec.id)]).unlink()

            invoice_ids = self._get_invoices(['cancel'], [
                'out_invoice', 'out_refund'
            ]).filtered(lambda inv: (inv.journal_id.type != 'normal'))
            line = 0
            report_data = ''
            for inv in invoice_ids:
                inv.fiscal_status = 'blocked' if not inv.fiscal_status else \
                    inv.fiscal_status
                line += 1
                values = {
                    'dgii_report_id': rec.id,
                    'line': line,
                    'invoice_partner_id': inv.partner_id.id,
                    'fiscal_invoice_number': inv.l10n_latam_document_number,
                    'invoice_date': inv.invoice_date,
                    'anulation_type': inv.cancellation_type,
                    'invoice_id': inv.id
                }
                CancelLine.create(values)
                report_data += self.process_608_report_data(values) + '\n'

            self._generate_608_txt(report_data, line)

    def process_609_report_data(self, values):

        LEGAL_NAME = str(values['legal_name'])
        ID_TYPE = str(values['tax_id_type'] if values['tax_id_type'] else "")
        TAX_ID = str(values['tax_id'] if values['tax_id'] else "")
        CNT_CODE = str(
            values['country_code'] if values['country_code'] else "")
        PST = str(values['purchased_service_type']
                  if values['purchased_service_type'] else "")
        STD = str(values['service_type_detail']
                  if values['service_type_detail'] else "")
        REL_PART = str(
            values['related_part'] if values['related_part'] else "0")
        DOC_NUM = str(
            values['doc_number'] if values['doc_number'] else "")
        DOC_DATE = str(self._get_formated_date(values['doc_date']))
        INV_AMOUNT = self._get_formated_amount(values['invoiced_amount'])
        ISR_DATE = str(self._get_formated_date(
            values['isr_withholding_date']))
        PRM_INCM = self._get_formated_amount(values['presumed_income'])
        WH_ISR = self._get_formated_amount(values['withholded_isr'])

        return "|".join([
            LEGAL_NAME, ID_TYPE, TAX_ID, CNT_CODE, PST, STD, REL_PART, DOC_NUM,
            DOC_DATE, INV_AMOUNT, ISR_DATE, PRM_INCM, WH_ISR
        ])

    def _generate_609_txt(self, records, qty):

        company_vat = self.company_id.vat
        period = dt.strptime(self.name.replace('/', ''),
                             '%m%Y').strftime('%Y%m')

        header = "609|{}|{}|{}".format(
            str(company_vat), period, qty) + '\n'
        data = header + records

        file_path = '/tmp/DGII_609_{}_{}.txt'.format(company_vat, period)
        with open(file_path, 'w', encoding="utf-8", newline='\r\n') as txt_609:
            txt_609.write(str(data))

        self.write({
            'exterior_filename': file_path.replace('/tmp/', ''),
            'exterior_binary': base64.b64encode(open(file_path, 'rb').read())
        })

    def _compute_609_data(self):
        for rec in self:
            ExteriorLine = self.env['dgii.reports.exterior.line']
            ExteriorLine.search([('dgii_report_id', '=', rec.id)]).unlink()

            invoice_ids = self._get_invoices(['posted', 'in_payment', 'paid'], [
                'in_invoice', 'in_refund'
            ]).filtered(lambda inv: (inv.partner_id.country_id.code != 'DO')
                                    and (inv.journal_id.type == 'exterior'))
            line = 0
            report_data = ''
            for inv in invoice_ids:
                inv.fiscal_status = 'blocked' if not inv.fiscal_status else \
                    inv.fiscal_status
                line += 1
                values = {
                    'dgii_report_id': rec.id,
                    'line': line,
                    'legal_name': inv.partner_id.name,
                    'tax_id_type':
                        1
                        if inv.partner_id.company_type == 'individual' else 2,
                    'tax_id': inv.partner_id.vat,
                    'country_code': self._get_country_number(inv.partner_id),
                    'purchased_service_type': int(inv.service_type),
                    'service_type_detail': inv.service_type_detail.code,
                    'related_part': int(inv.partner_id.related),
                    'doc_number': inv.number,
                    'doc_date': inv.invoice_date,
                    'invoiced_amount': self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                     (inv.amount_untaxed * -1)),
                    'isr_withholding_date': inv.payment_date if
                    inv.payment_date else False,
                    'presumed_income': 0,  # Pendiente
                    'withholded_isr': self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                    inv.income_withholding) if
                    inv.payment_date else 0,
                    'invoice_id': inv.id
                }
                ExteriorLine.create(values)
                report_data += self.process_609_report_data(values) + '\n'

            self._generate_609_txt(report_data, line)



    alquiler_sub = fields.Monetary()
    alquiler_isr = fields.Monetary()
    honorarios_sub = fields.Monetary()
    honorarios_isr = fields.Monetary()
    premios_sub = fields.Monetary()
    premios_isr = fields.Monetary()
    titulos_sub = fields.Monetary()
    titulos_isr = fields.Monetary()
    dividendos_sub = fields.Monetary()
    dividendos_isr = fields.Monetary()
    personas_fnoresidentes25312_sub = fields.Monetary()
    personas_fnoresidentes25312_isr = fields.Monetary()
    personas_fnoresidentes572007_sub = fields.Monetary()
    personas_fnoresidentes572007_isr = fields.Monetary()
    personas_jnoresidentes25312_sub = fields.Monetary()
    personas_jnoresidentes25312_isr = fields.Monetary()
    personas_jnoresidentes572007_sub = fields.Monetary()
    personas_jnoresidentes572007_isr = fields.Monetary()
    remesas_sub = fields.Monetary()
    remesas_isr = fields.Monetary()
    remesas_acuerdos_sub = fields.Monetary()
    remesas_acuerdos_p = fields.Float()
    remesas_acuerdos_isr = fields.Monetary()
    retencion_estados_sub = fields.Monetary()
    retencion_estados_isr = fields.Monetary()
    juegos_telefono_sub = fields.Monetary()
    juegos_telefono_isr = fields.Monetary()
    capital_sub = fields.Monetary()
    capital_isr = fields.Monetary()
    juego_internet_sub = fields.Monetary()
    juego_internet_isr = fields.Monetary()
    otras_rentas_sub = fields.Monetary()
    otras_rentas_isr = fields.Monetary()
    rentas_presuntas_sub = fields.Monetary()
    rentas_presuntas_isr = fields.Monetary()
    rentas_0707_sub = fields.Monetary()
    rentas_0707_isr = fields.Monetary()
    interes_juridicas_sub = fields.Monetary()
    interes_juridicas_isr = fields.Monetary()
    interes_fisicas_sub = fields.Monetary()
    interes_fisicas_isr = fields.Monetary()

    
    otros_impuestos_sub = fields.Monetary(compute="_calculate_sum")
    otros_impuestos_isr = fields.Monetary(compute="_calculate_sum")
    total_sum_21_22 = fields.Monetary(compute="_calculate_sum_21_22")
    total_saldos_compensables = fields.Monetary()
    total_pagos_computables = fields.Monetary()
    total_saldo_favor_anterior_isr = fields.Monetary()
    total_diferencia_pagar_isr = fields.Monetary(compute="_calculate_diferencia_saldo")
    total_saldo_favor_isr = fields.Monetary(compute="_calculate_diferencia_saldo")
    total_a_pagar_isr = fields.Monetary(compute="_calculate_total_a_pagar")

    retribuciones_sub = fields.Monetary()
    retribuciones_isr = fields.Monetary()
    recargos_isr = fields.Monetary()
    intereses_isr = fields.Monetary()

    api.depends('total_saldo_favor_isr', 'recargos_isr', 'intereses_isr',
                'total_diferencia_pagar_isr')
    def _calculate_total_a_pagar(self):
        for rec in self:
            rec.total_a_pagar_isr = rec.total_diferencia_pagar_isr + rec.recargos_isr + rec.intereses_isr


    api.depends('total_saldos_compensables', 'total_pagos_computables', 'total_saldo_favor_anterior_isr', 'total_sum_21_22')
    def _calculate_diferencia_saldo(self):
        for rec in self:
            total = rec.total_sum_21_22 - rec.total_saldos_compensables - rec.total_pagos_computables - rec.total_saldo_favor_anterior_isr
            if total >= 0:
                rec.total_diferencia_pagar_isr = total
                rec.total_saldo_favor_isr = 0.0
            elif total < 0:
                rec.total_diferencia_pagar_isr = 0.0
                rec.total_saldo_favor_isr = - total

    api.depends('alquiler_sub', 'honorarios_sub')
    def _calculate_sum_21_22(self):
        for rec in self:
            rec.total_sum_21_22 = rec.otros_impuestos_isr + rec.retribuciones_isr

    api.onchange('alquiler_sub', 'honorarios_sub', 'premios_sub', 'titulos_sub', 'dividendos_sub', 'personas_fnoresidentes25312_sub', 'personas_fnoresidentes572007_sub', 'personas_jnoresidentes25312_sub', 'personas_jnoresidentes572007_sub', 'remesas_sub', 'remesas_acuerdos_sub', 'retencion_estados_sub', 'juegos_telefono_sub', 'capital_sub', 'juego_internet_sub', 'otras_rentas_sub', 'rentas_presuntas_sub', 'rentas_0707_sub', 'interes_juridicas_sub', 'interes_fisicas_sub')
    def _calculate_sum_onchange(self):
        for rec in self:
            rec.otros_impuestos_sub = rec.alquiler_sub + rec.honorarios_sub + rec.otras_rentas_sub + rec.rentas_presuntas_sub + rec.interes_juridicas_sub + \
                                      rec.interes_fisicas_sub + rec.interes_fisicas_sub + rec.juegos_telefono_sub + rec.premios_sub + rec.titulos_sub + rec.dividendos_sub + rec.personas_fnoresidentes25312_sub + rec.personas_fnoresidentes572007_sub + rec.personas_jnoresidentes25312_sub + rec.personas_jnoresidentes572007_sub + rec.remesas_sub + rec.remesas_acuerdos_sub + rec.retencion_estados_sub + rec.juegos_telefono_sub + rec.capital_sub + rec.juego_internet_sub + rec.rentas_0707_sub  + rec.rentas_0707_sub 
            
            rec.otros_impuestos_isr = rec.alquiler_isr + rec.honorarios_isr + rec.otras_rentas_isr + rec.rentas_presuntas_isr + rec.interes_juridicas_isr + \
                                      rec.interes_fisicas_isr + rec.interes_fisicas_isr + rec.juegos_telefono_isr + rec.premios_isr + rec.titulos_isr + rec.dividendos_isr + rec.personas_fnoresidentes25312_isr + rec.personas_fnoresidentes572007_isr + rec.personas_jnoresidentes25312_isr + rec.personas_jnoresidentes572007_isr + rec.remesas_isr + rec.remesas_acuerdos_isr + rec.retencion_estados_isr + rec.juegos_telefono_isr + rec.capital_isr + rec.juego_internet_isr + rec.rentas_0707_isr  + rec.rentas_0707_isr 



    api.depends('alquiler_sub', 'honorarios_sub', 'premios_sub', 'titulos_sub', 'dividendos_sub', 'personas_fnoresidentes25312_sub', 'personas_fnoresidentes572007_sub', 'personas_jnoresidentes25312_sub', 'personas_jnoresidentes572007_sub', 'remesas_sub', 'remesas_acuerdos_sub', 'retencion_estados_sub', 'juegos_telefono_sub', 'capital_sub', 'juego_internet_sub', 'otras_rentas_sub', 'rentas_presuntas_sub', 'rentas_0707_sub', 'interes_juridicas_sub', 'interes_fisicas_sub')
    def _calculate_sum(self):
        for rec in self:
            rec.otros_impuestos_sub = rec.alquiler_sub + rec.honorarios_sub + rec.otras_rentas_sub + rec.rentas_presuntas_sub + rec.interes_juridicas_sub + \
                                      rec.interes_fisicas_sub + rec.interes_fisicas_sub + rec.juegos_telefono_sub + rec.premios_sub + rec.titulos_sub + rec.dividendos_sub + rec.personas_fnoresidentes25312_sub + rec.personas_fnoresidentes572007_sub + rec.personas_jnoresidentes25312_sub + rec.personas_jnoresidentes572007_sub + rec.remesas_sub + rec.remesas_acuerdos_sub + rec.retencion_estados_sub + rec.juegos_telefono_sub + rec.capital_sub + rec.juego_internet_sub + rec.rentas_0707_sub + rec.rentas_0707_sub

            rec.otros_impuestos_isr = rec.alquiler_isr + rec.honorarios_isr + rec.otras_rentas_isr + rec.rentas_presuntas_isr + rec.interes_juridicas_isr + \
                                      rec.interes_fisicas_isr + rec.interes_fisicas_isr + rec.juegos_telefono_isr + rec.premios_isr + rec.titulos_isr + rec.dividendos_isr + rec.personas_fnoresidentes25312_isr + rec.personas_fnoresidentes572007_isr + rec.personas_jnoresidentes25312_isr + rec.personas_jnoresidentes572007_isr + rec.remesas_isr + rec.remesas_acuerdos_isr + rec.retencion_estados_isr + rec.juegos_telefono_isr + rec.capital_isr + rec.juego_internet_isr + rec.rentas_0707_isr + rec.rentas_0707_isr

    def _compute_ir17(self):
        for rec in self:
            IR17Retritubion = self.env['dgii.reports.ir17.retribution']
            IR17Retritubion.search([('dgii_report_id', '=', rec.id)]).unlink()

            invoice_ids = self._get_invoices(['posted', 'in_payment', 'paid'],
                                             ['in_invoice', 'in_refund'])

            month, year = self.name.split('/')
            start_date = '{}-{}-01'.format(year, month)
            s_date = dt.strptime(start_date,
                                           '%Y-%m-%d').date()



            alquiler_sub = 0.0
            alquiler_isr = 0.0
            honorarios_sub = 0.0
            honorarios_isr = 0.0
            otras_rentas_sub = 0.0
            otras_rentas_isr = 0.0
            rentas_presuntas_sub = 0.0
            rentas_presuntas_isr = 0.0
            interes_juridicas_sub = 0.0
            interes_juridicas_isr = 0.0
            interes_fisicas_sub = 0.0
            interes_fisicas_isr = 0.0
            retencion_estados_sub = 0.0
            retencion_estados_isr = 0.0
            juegos_telefono_sub = 0.0
            juegos_telefono_isr = 0.0
            
            for inv in invoice_ids:
                if inv.isr_withholding_type == '01':
                    alquiler_sub += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                          inv.service_total_amount)
                    alquiler_isr += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                          inv.income_withholding)
                if inv.isr_withholding_type == '02':
                    honorarios_sub += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                          inv.service_total_amount)
                    honorarios_isr += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                          inv.income_withholding)
                if inv.isr_withholding_type == '03':
                    otras_rentas_sub += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                          inv.service_total_amount)
                    otras_rentas_isr += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                          inv.income_withholding)
                if inv.isr_withholding_type == '04':
                    rentas_presuntas_sub += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                          inv.service_total_amount)
                    rentas_presuntas_isr += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                          inv.income_withholding)
                if inv.isr_withholding_type == '05':
                    interes_juridicas_sub += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                          inv.service_total_amount)
                    interes_juridicas_isr += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                          inv.income_withholding)
                if inv.isr_withholding_type == '06':
                    interes_fisicas_sub += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                          inv.service_total_amount)
                    interes_fisicas_isr += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                          inv.income_withholding)
                if inv.isr_withholding_type == '07':
                    retencion_estados_sub += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                          inv.service_total_amount)
                    retencion_estados_isr += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                          inv.income_withholding)
                    
                if inv.isr_withholding_type == '08':
                    juegos_telefono_sub += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                          inv.service_total_amount)
                    juegos_telefono_isr += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,
                                                                          inv.income_withholding)
            rec.alquiler_sub = alquiler_sub
            rec.alquiler_isr = alquiler_isr
            rec.honorarios_sub = honorarios_sub
            rec.honorarios_isr = honorarios_isr
            rec.otras_rentas_sub = otras_rentas_sub
            rec.otras_rentas_isr = otras_rentas_isr
            rec.rentas_presuntas_sub = rentas_presuntas_sub
            rec.rentas_presuntas_isr = rentas_presuntas_isr
            rec.interes_juridicas_sub = interes_juridicas_sub
            rec.interes_juridicas_isr = interes_juridicas_isr
            rec.interes_fisicas_sub = interes_fisicas_sub
            rec.interes_fisicas_isr = interes_fisicas_isr
            rec.retencion_estados_sub = retencion_estados_sub
            rec.retencion_estados_isr = retencion_estados_isr
            rec.juegos_telefono_sub = juegos_telefono_sub
            rec.juegos_telefono_isr = juegos_telefono_isr

            invoice_ids_retribution = self._get_invoices(['posted'],
                                             ['in_invoice', 'in_refund', 'entry'])

            retribuciones_sub = 0.0
            for inv1 in invoice_ids_retribution:
                for line in inv1.line_ids:
                    retribuciones_sub_line = 0.0
                    if line.account_id.account_retribution_type == 'R10' and line.date >= s_date:
                        retribuciones_sub += (line.debit - line.credit) * 0.10
                        retribuciones_sub_line = (line.debit - line.credit) * 0.10
                    if line.account_id.account_retribution_type == 'R20' and line.date >= s_date:
                        retribuciones_sub += (line.debit - line.credit) * 0.20
                        retribuciones_sub_line = (line.debit - line.credit) * 0.20
                    if line.account_id.account_retribution_type == 'R30' and line.date >= s_date:
                        retribuciones_sub += (line.debit - line.credit) * 0.30
                        retribuciones_sub_line = (line.debit - line.credit) * 0.30
                    if line.account_id.account_retribution_type == 'R40' and line.date >= s_date:
                        retribuciones_sub += (line.debit - line.credit) * 0.40
                        retribuciones_sub_line = (line.debit - line.credit) * 0.40
                    if line.account_id.account_retribution_type == 'RA' and line.date >= s_date:
                        retribuciones_sub += (line.debit - line.credit)
                        retribuciones_sub_line = (line.debit - line.credit)

                    if retribuciones_sub > 0 and line.account_id.account_retribution_type and line.date >= s_date:
                        values = {
                            'move_id': line.id,
                            'amount_base': retribuciones_sub_line,
                            'amount_calculated': retribuciones_sub_line * 0.27,
                            'dgii_report_id': rec.id,
                        }
                        IR17Retritubion.create(values)
                        # raise UserError(_("%s", IR17Retritubion))

            retribuciones_isr = retribuciones_sub * 0.27

            rec.retribuciones_sub = retribuciones_sub
            rec.retribuciones_isr = retribuciones_isr

    def get_ir17_tree_view(self):
        return {
            'name': 'IR17: Detalle de retribuciones',
            'view_mode': 'tree',
            'res_model': 'dgii.reports.ir17.retribution',
            'type': 'ir.actions.act_window',
            'view_id':
                self.env.ref('dgii_reports_second.dgii_report_ir17_retribution_line_tree').id,
            'domain': [('dgii_report_id', '=', self.id)]
        }

    fiscal_qty = fields.Float()
    fiscal_amount = fields.Monetary()
    consumer_qty = fields.Float()
    consumer_amount = fields.Monetary()
    debit_note_qty = fields.Float()
    debit_note_amount = fields.Monetary()
    credit_note_qty = fields.Float()
    credit_note_amount = fields.Monetary()
    unique_qty = fields.Float()
    unique_amount = fields.Monetary()
    special_qty = fields.Float()
    special_amount = fields.Monetary()
    gub_qty = fields.Float()
    gub_amount = fields.Monetary()
    expo_qty = fields.Float()
    expo_amount = fields.Monetary()
    other_positive_qty = fields.Float()
    other_positive_amount = fields.Monetary()
    other_negative_qty = fields.Float()
    other_negative_amount = fields.Monetary()
    notas_credito_30_dias = fields.Monetary()

    retcli_norma0804 = fields.Monetary()
    retcli_norma0205_bspiata = fields.Monetary()
    retcli_norma0205 = fields.Monetary()
    retcli_alojamiento_y_ocupacion = fields.Monetary()
    retcli_ret_estado = fields.Monetary()
    retcli_itbis_percibido = fields.Monetary()
    retcli_total_pagos_computables = fields.Monetary(compute="_calculate_total_pagos_computables")

    calcular_nc_30dias = fields.Boolean(string='Calcular otras operaciones positivas (NC > 30 dias)',
                                        help="Calcular notas de credito que afectan a facturas con mas de 30 dias de "
                                             "emitidas como otras operaciones positivas?", default=True)
    calcular_ingresos_financieros_anexoa = fields.Boolean(string='Calcular ingresos financieros?',
                                        help="Calcular como ingreso financiero las cuentas del catalogo que tengan este "
                                             "concepto asignado?", default=True)

    total_operaciones = fields.Monetary(compute="_calculate_total_operaciones")

    construc_norma0707_direcciont_fact = fields.Monetary()
    construc_norma0707_direcciont_monto = fields.Monetary()
    construc_contrato_adm_fact = fields.Monetary()
    construc_contrato_adm_monto = fields.Monetary()
    construc_asesoria_hon_fact = fields.Monetary()
    construc_asesoria_hon_monto = fields.Monetary()
    construc_total_operaciones_construc_fact = fields.Monetary(compute="_compute_construc_anexoa_calculate_total_pagos_computables")
    construc_total_operaciones_construc_monto = fields.Monetary(compute="_compute_construc_anexoa_calculate_total_pagos_computables")
    construc_total_operaciones_exentas = fields.Monetary(compute="_compute_construc_anexoa_calculate_total_pagos_computables")

    comision_ventab_fact = fields.Monetary()
    comision_ventab_monto = fields.Monetary()
    comision_ventas_fact = fields.Monetary()
    comision_ventas_monto = fields.Monetary()
    comision_total_operaciones_comision_fact = fields.Monetary(compute="_compute_comision_anexoa_calculate_total")
    comision_total_operaciones_comision_monto = fields.Monetary(compute="_compute_comision_anexoa_calculate_total")
    comision_total_operaciones_exentas = fields.Monetary(compute="_compute_comision_anexoa_calculate_total")

    infor_regimen_especial_606 = fields.Monetary(compute="_compute_regimen_especial_606")

    def _compute_regimen_especial_606(self):
        for rec in self:
            if rec.state == 'generated':
                month, year = rec.name.split('/')
                start_date = '{}-{}-01'.format(year, month)
                s_date = dt.strptime(start_date,
                                     '%Y-%m-%d').date()

                invoice_ids = rec._get_invoices(['posted', 'in_payment', 'paid'],
                                                 ['in_invoice'])

                infor_regimen_especial_606 = 0.0

                for inv in invoice_ids:
                    if inv.invoice_date >= s_date:
                        if inv.l10n_latam_document_type_id.l10n_do_ncf_type in ('special', 'e-special'):
                            infor_regimen_especial_606 += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,inv.amount_untaxed)

                rec.infor_regimen_especial_606 += infor_regimen_especial_606
            else:
                rec.infor_regimen_especial_606 = 0.0


    @api.depends('comision_ventab_fact', 'comision_ventab_monto',
                 'comision_ventas_fact',
                 'comision_ventas_monto')
    def _compute_comision_anexoa_calculate_total(self):
        for rec in self:
            rec.comision_total_operaciones_comision_fact = (rec.comision_ventab_fact \
                                                            + rec.comision_ventas_fact) or 0.0

            rec.comision_total_operaciones_comision_monto = (rec.comision_ventab_monto \
                                                             + rec.comision_ventas_monto) or 0.0

            rec.comision_total_operaciones_exentas = (rec.comision_total_operaciones_comision_fact \
                                                      - rec.comision_total_operaciones_comision_monto) or 0.0


    def _compute_comision_anexoa(self):
        for rec in self:
            comision_ventab_fact = 0.0
            comision_ventab_monto = 0.0
            comision_ventas_fact = 0.0
            comision_ventas_monto = 0.0

            month, year = self.name.split('/')
            start_date = '{}-{}-01'.format(year, month)
            s_date = dt.strptime(start_date,
                                 '%Y-%m-%d').date()

            invoice_ids = self._get_invoices(['posted', 'in_payment', 'paid'],
                                                    ['out_refund', 'out_invoice'])

            for inv in invoice_ids:
                if inv.invoice_date >= s_date:
                    if inv.tipo_itbis_venta == '11':
                        comision_ventab_fact += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,inv.amount_untaxed)
                        base_imponible = 0.0
                        for line in inv.invoice_line_ids:
                            for tax in line.tax_ids:
                                if tax.amount > 0 and tax.tax_group_id.name == 'ITBIS' and tax.amount_type != 'group':
                                    base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                elif tax.amount_type == 'group':
                                    for taxes in tax.children_tax_ids:
                                        if taxes.amount > 0 and taxes.tax_group_id.name == 'ITBIS' and taxes.amount_type != 'group':
                                            base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)

                        comision_ventab_monto += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,base_imponible)
                    if inv.tipo_itbis_venta == '12':
                        comision_ventas_fact += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,inv.amount_untaxed)
                        base_imponible = 0.0
                        for line in inv.invoice_line_ids:
                            for tax in line.tax_ids:
                                if tax.amount > 0 and tax.tax_group_id.name == 'ITBIS' and tax.amount_type != 'group':
                                    base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                elif tax.amount_type == 'group':
                                    for taxes in tax.children_tax_ids:
                                        if taxes.amount > 0 and taxes.tax_group_id.name == 'ITBIS' and taxes.amount_type != 'group':
                                            base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                        comision_ventas_monto += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,base_imponible)

            rec.comision_ventab_fact = comision_ventab_fact
            rec.comision_ventab_monto = comision_ventab_monto
            rec.comision_ventas_fact = comision_ventas_fact
            rec.comision_ventas_monto = comision_ventas_monto




    @api.depends('construc_norma0707_direcciont_fact', 'construc_norma0707_direcciont_monto', 'construc_contrato_adm_fact',
                 'construc_contrato_adm_monto', 'construc_asesoria_hon_fact', 'construc_asesoria_hon_monto')
    def _compute_construc_anexoa_calculate_total_pagos_computables(self):
        for rec in self:
            rec.construc_total_operaciones_construc_fact = (rec.construc_norma0707_direcciont_fact \
             + rec.construc_contrato_adm_fact + rec.construc_asesoria_hon_fact) or 0.0

            rec.construc_total_operaciones_construc_monto = (rec.construc_norma0707_direcciont_monto \
             + rec.construc_contrato_adm_monto + rec.construc_asesoria_hon_monto) or 0.0

            rec.construc_total_operaciones_exentas = (rec.construc_total_operaciones_construc_fact \
                                                            - rec.construc_total_operaciones_construc_monto) or 0.0





    def _compute_construc_anexoa(self):
        for rec in self:
            construc_norma0707_direcciont_fact = 0.0
            construc_norma0707_direcciont_monto = 0.0
            construc_contrato_adm_fact = 0.0
            construc_contrato_adm_monto = 0.0
            construc_asesoria_hon_monto = 0.0

            month, year = self.name.split('/')
            start_date = '{}-{}-01'.format(year, month)
            s_date = dt.strptime(start_date,
                                 '%Y-%m-%d').date()

            invoice_ids = self._get_invoices(['posted', 'in_payment', 'paid'],
                                                    ['out_refund', 'out_invoice'])

            for inv in invoice_ids:
                if inv.invoice_date >= s_date:
                    if inv.tipo_itbis_venta == '08':
                        construc_norma0707_direcciont_fact += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,inv.amount_untaxed)
                        base_imponible = 0.0
                        for line in inv.invoice_line_ids:
                            for tax in line.tax_ids:
                                if tax.amount > 0 and tax.tax_group_id.name == 'ITBIS' and tax.amount_type != 'group':
                                    base_imponible += (self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal) * 0.018) / 0.18
                                elif tax.amount_type == 'group':
                                    for taxes in tax.children_tax_ids:
                                        if taxes.amount > 0 and taxes.tax_group_id.name == 'ITBIS' and taxes.amount_type != 'group':
                                            base_imponible += (self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal) * 0.018) / 0.18
                                        if tax.amount != 1.8 and tax.amount_type != 'group':
                                            raise UserError(
                                                _("No puede utilizar este tipo de ITBIS exento (Constructora 08) si existe alguna linea de la factura "
                                                  "con un ITBIS que supere el 18 porciento del 10 porciento de la factura. Factura: %s",
                                                  inv.name))

                                if tax.amount != 1.8 and tax.amount_type != 'group':
                                    raise UserError(_("No puede utilizar este tipo de ITBIS exento (Constructora 08) si existe alguna linea de la factura "
                                                      "con un ITBIS que supere el 18 porciento del 10 porciento de la factura. Factura: %s", inv.name))
                        construc_norma0707_direcciont_monto += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,base_imponible)
                    if inv.tipo_itbis_venta == '09':
                        construc_contrato_adm_fact += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,inv.amount_untaxed)
                        base_imponible = 0.0
                        for line in inv.invoice_line_ids:
                            for tax in line.tax_ids:
                                if tax.amount > 0 and tax.tax_group_id.name == 'ITBIS' and tax.amount_type != 'group':
                                    base_imponible += (self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal) * 0.018) / 0.18
                                elif tax.amount_type == 'group':
                                    for taxes in tax.children_tax_ids:
                                        if taxes.amount > 0 and taxes.tax_group_id.name == 'ITBIS' and taxes.amount_type != 'group':
                                            base_imponible += (self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal) * 0.018) / 0.18
                                        if tax.amount != 1.8 and tax.amount_type != 'group':
                                            raise UserError(
                                                _("No puede utilizar este tipo de ITBIS exento (Constructora 08) si existe alguna linea de la factura "
                                                  "con un ITBIS que supere el 18 porciento del 10 porciento de la factura. Factura: %s",
                                                  inv.name))

                                if tax.amount != 1.8 and tax.amount_type != 'group':
                                    raise UserError(
                                        _("No puede utilizar este tipo de ITBIS exento (Constructora 08) si existe alguna linea de la factura "
                                          "con un ITBIS que supere el 18 porciento del 10 porciento de la factura. Factura: %s",
                                          inv.name))
                        construc_contrato_adm_monto += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,base_imponible)
                    if inv.tipo_itbis_venta == '10':
                        base_imponible = 0.0
                        for line in inv.invoice_line_ids:
                            for tax in line.tax_ids:
                                if tax.amount > 0 and tax.tax_group_id.name == 'ITBIS' and tax.amount_type != 'group':
                                    base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)
                                elif tax.amount_type == 'group':
                                    for taxes in tax.children_tax_ids:
                                        if taxes.amount > 0 and taxes.tax_group_id.name == 'ITBIS' and taxes.amount_type != 'group':
                                            base_imponible += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,line.price_subtotal)

                        construc_asesoria_hon_monto += self._convert_to_DOP_currency(False,inv, inv.currency_id,inv.invoice_date,base_imponible)

            rec.construc_norma0707_direcciont_fact = construc_norma0707_direcciont_fact
            rec.construc_norma0707_direcciont_monto = construc_norma0707_direcciont_monto
            rec.construc_contrato_adm_fact = construc_contrato_adm_fact
            rec.construc_contrato_adm_monto = construc_contrato_adm_monto
            rec.construc_asesoria_hon_monto = construc_asesoria_hon_monto



    @api.depends('fiscal_amount','consumer_amount', 'debit_note_amount', 'credit_note_amount',
                 'unique_amount', 'special_amount', 'gub_amount', 'expo_amount', 'other_positive_amount',
                 'other_negative_amount')
    def _calculate_total_operaciones(self):
        for rec in self:
            rec.total_operaciones = rec.fiscal_amount + rec.consumer_amount + rec.debit_note_amount - rec.credit_note_amount \
                                    + rec.unique_amount + rec.special_amount + rec.gub_amount + rec.expo_amount \
                                    + rec.other_positive_amount - rec.other_negative_amount

    @api.depends('retcli_norma0804', 'retcli_norma0205_bspiata', 'retcli_norma0205', 'retcli_alojamiento_y_ocupacion',
                 'retcli_ret_estado', 'retcli_itbis_percibido')
    def _calculate_total_pagos_computables(self):
        for rec in self:
            rec.retcli_total_pagos_computables = rec.retcli_norma0804 + rec.retcli_norma0205_bspiata + rec.retcli_norma0205 + \
                                                 rec.retcli_alojamiento_y_ocupacion + rec.retcli_ret_estado + rec.retcli_itbis_percibido

    def _compute_ret_anexoa(self):
        for rec in self:
            retcli_norma0804 = 0.0
            retcli_norma0205_bspiata = 0.0
            retcli_norma0205 = 0.0
            retcli_alojamiento_y_ocupacion = 0.0
            retcli_ret_estado = 0.0
            retcli_itbis_percibido = 0.0

            month, year = self.name.split('/')
            last_day = calendar.monthrange(int(year), int(month))[1]
            start_date = '{}-{}-01'.format(year, month)
            end_date = '{}-{}-{}'.format(year, month, last_day)

            payment_id = self.env['account.payment'].search(
                [('state', '=', 'posted'),
                 ('date', '>=', start_date),
                 ('date', '<=', end_date),
                 ('company_id', '=', rec.company_id.id),
                 ('withold_method','!=', 'default')])

            invoice_ids_credit = self._get_invoices(['posted', 'in_payment', 'paid'],
                                                    ['out_refund','out_invoice'])

            for pay in payment_id:
                if pay.withold_itbis_select.sale_itbis_retention_type == '01':
                    retcli_norma0804 += self._convert_to_DOP_currency(pay,False, pay.currency_id, pay.date,pay.withold_itbis_amount)
                if pay.withold_itbis_select.sale_itbis_retention_type == '02':
                    retcli_norma0205_bspiata += self._convert_to_DOP_currency(pay,False, pay.currency_id, pay.date,pay.withold_itbis_amount)
                if pay.withold_itbis_select.sale_itbis_retention_type == '03':
                    retcli_norma0205 += self._convert_to_DOP_currency(pay,False, pay.currency_id, pay.date,pay.withold_itbis_amount)
                if pay.withold_itbis_select.sale_itbis_retention_type == '04':
                    retcli_alojamiento_y_ocupacion += self._convert_to_DOP_currency(pay,False, pay.currency_id, pay.date,pay.withold_itbis_amount)
                if pay.withold_itbis_select.sale_itbis_retention_type == '05':
                    retcli_ret_estado += self._convert_to_DOP_currency(pay,False, pay.currency_id, pay.date,pay.withold_itbis_amount)
                if pay.withold_itbis_select.sale_itbis_retention_type == '06':
                    retcli_itbis_percibido += self._convert_to_DOP_currency(pay,False, pay.currency_id, pay.date,pay.withold_itbis_amount)

            for inv in invoice_ids_credit:
                for line in inv.invoice_line_ids:
                    for tax in line.tax_ids:
                        if tax.sale_itbis_retention_type == '02':
                            retcli_norma0205_bspiata += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,inv.third_withheld_itbis)
                        if tax.sale_itbis_retention_type == '03':
                            retcli_norma0205 += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,inv.third_withheld_itbis)
                        if tax.sale_itbis_retention_type == '04':
                            retcli_alojamiento_y_ocupacion += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,inv.third_withheld_itbis)
                        if tax.sale_itbis_retention_type == '05':
                            retcli_ret_estado += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,inv.third_withheld_itbis)
                        if tax.sale_itbis_retention_type == '06':
                            retcli_itbis_percibido += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,inv.third_withheld_itbis)

            rec.retcli_norma0804 = retcli_norma0804
            rec.retcli_norma0205_bspiata = retcli_norma0205_bspiata
            rec.retcli_norma0205 = retcli_norma0205
            rec.retcli_alojamiento_y_ocupacion = retcli_alojamiento_y_ocupacion
            rec.retcli_ret_estado = retcli_ret_estado
            rec.retcli_itbis_percibido = retcli_itbis_percibido



    def _compute_anexoa(self):
        for rec in self:

            fiscal_qty = 0.0
            fiscal_amount = 0.0
            consumer_qty = 0.0
            consumer_amount = 0.0
            debit_note_qty = 0.0
            debit_note_amount = 0.0
            credit_note_qty = 0.0
            credit_note_amount = 0.0
            unique_qty = 0.0
            unique_amount = 0.0
            special_qty = 0.0
            special_amount = 0.0
            gub_qty = 0.0
            gub_amount = 0.0
            expo_qty = 0.0
            expo_amount = 0.0
            other_positive_qty = 0.0
            other_positive_amount = 0.0
            other_negative_qty = 0.0
            other_negative_amount = 0.0
            notas_credito_30_dias = 0.0

            for ncf in rec.ncf_sale_summary_ids:

                if ncf.dgii_report_id.id == self.id:

                    if ncf.l10n_do_ncf_type == 'fiscal':
                        fiscal_qty += ncf.qty
                        fiscal_amount += ncf.amount
                    if ncf.l10n_do_ncf_type == 'consumer':
                        consumer_qty += ncf.qty
                        consumer_amount += ncf.amount
                    if ncf.l10n_do_ncf_type == 'debit_note':
                        debit_note_qty += ncf.qty
                        debit_note_amount += ncf.amount
                    if ncf.l10n_do_ncf_type == 'credit_note':
                        credit_note_qty += ncf.qty
                        credit_note_amount += ncf.amount
                    if ncf.l10n_do_ncf_type == 'unique':
                        unique_qty += ncf.qty
                        unique_amount += ncf.amount
                    if ncf.l10n_do_ncf_type == 'special':
                        special_qty += ncf.qty
                        special_amount += ncf.amount
                    if ncf.l10n_do_ncf_type == 'governmental':
                        gub_qty += ncf.qty
                        gub_amount += ncf.amount
                    if ncf.l10n_do_ncf_type == 'export':
                        expo_qty += ncf.qty
                        expo_amount += ncf.amount

            rec.fiscal_qty = fiscal_qty
            rec.fiscal_amount = fiscal_amount
            rec.consumer_qty = consumer_qty
            rec.consumer_amount = consumer_amount
            rec.debit_note_qty = debit_note_qty
            rec.debit_note_amount = debit_note_amount
            rec.credit_note_qty = credit_note_qty
            rec.credit_note_amount = credit_note_amount
            rec.unique_qty = unique_qty
            rec.unique_amount = unique_amount
            rec.special_qty = special_qty
            rec.special_amount = special_amount
            rec.gub_qty = gub_qty
            rec.gub_amount = gub_amount
            rec.expo_qty = expo_qty
            rec.expo_amount = expo_amount



            invoice_ids_credit = self._get_invoices(['posted', 'in_payment', 'paid'],
                                             ['out_refund'])


            for inv in invoice_ids_credit:

                if inv.journal_id.l10n_latam_use_documents:
                    if inv.l10n_do_origin_ncf:
                        modified = False
                        modified = self.env['account.move'].search(['&', '&',('l10n_latam_document_number', '=', inv.l10n_do_origin_ncf)
                                                                       ,('partner_id', '=', inv.partner_id.id),('state', '=', 'posted')
                                                                       ,('move_type', '=', 'out_invoice'),('company_id', '=', rec.company_id.id)])


                        for modifieds in modified:


                            if (inv.invoice_date - modifieds.invoice_date).days > 30 and inv.l10n_do_origin_ncf == modifieds.l10n_latam_document_number:

                                other_positive_qty += 1
                                other_positive_amount += self._convert_to_DOP_currency(False,inv, inv.currency_id, inv.invoice_date,inv.amount_untaxed)
                                notas_credito_30_dias = other_positive_amount
                    else:
                        if inv.journal_id.l10n_latam_use_documents:
                            raise UserError(_("La nota de credito %s no posee un NCF afectado. "
                                              "Favor corregir.", inv.name))

            if rec.calcular_nc_30dias:
                rec.other_positive_qty = other_positive_qty
                rec.other_positive_amount = other_positive_amount



            rec.notas_credito_30_dias = notas_credito_30_dias

            rec._compute_ret_anexoa()
            rec._compute_construc_anexoa()
            rec._compute_comision_anexoa()
            rec._compute_regimen_especial_606()











    def _generate_report(self):
        # Drop 607 NCF Operations for recompute
        self.env['dgii.reports.sale.summary'].search([('dgii_report_id', '=',
                                                       self.id)]).unlink()

        self._compute_606_data()
        self._compute_607_data()
        self._compute_608_data()
        self._compute_609_data()
        self._compute_ir17()
        self._compute_anexoa()
        self.state = 'generated'

    def generate_report(self):
        if self.state == 'generated':
            action = self.env.ref(
                'dgii_reports_second.dgii_report_regenerate_wizard_action').read()[0]
            action['context'] = {'default_report_id': self.id}
            return action
        else:
            self._generate_report()

    def _has_withholding(self, inv):
        """Validate if given invoice has an Withholding tax"""
        return True if any([inv.income_withholding,
                            inv.withholded_itbis,
                            inv.third_withheld_itbis,
                            inv.third_income_withholding]) else False

    def _invoice_status_sent(self):
        for report in self:
            PurchaseLine = self.env['dgii.reports.purchase.line']
            SaleLine = self.env['dgii.reports.sale.line']
            CancelLine = self.env['dgii.reports.cancel.line']
            ExteriorLine = self.env['dgii.reports.exterior.line']
            invoice_ids = PurchaseLine.search([
                ('dgii_report_id', '=', report.id)
            ]).mapped('invoice_id')
            invoice_ids += SaleLine.search([
                ('dgii_report_id', '=', report.id)
            ]).mapped('invoice_id')
            invoice_ids += CancelLine.search([
                ('dgii_report_id', '=', report.id)
            ]).mapped('invoice_id')
            invoice_ids += ExteriorLine.search([
                ('dgii_report_id', '=', report.id)
            ]).mapped('invoice_id')
            for inv in invoice_ids:
                if (inv.state in ['cancel'] or inv.payment_state in ['paid','in_payment']) and \
                        self._include_in_current_report(inv):
                    inv.fiscal_status = 'done'
                    continue

                if self._has_withholding(inv):
                    inv.fiscal_status = 'normal'
                else:
                    inv.fiscal_status = 'done'

    def _invoice_status_regenerate(self):
        for report in self:
            PurchaseLine = self.env['dgii.reports.purchase.line']
            SaleLine = self.env['dgii.reports.sale.line']
            CancelLine = self.env['dgii.reports.cancel.line']
            ExteriorLine = self.env['dgii.reports.exterior.line']
            invoice_ids = PurchaseLine.search([
                ('dgii_report_id', '=', report.id)
            ]).mapped('invoice_id')
            invoice_ids += SaleLine.search([
                ('dgii_report_id', '=', report.id)
            ]).mapped('invoice_id')
            invoice_ids += CancelLine.search([
                ('dgii_report_id', '=', report.id)
            ]).mapped('invoice_id')
            invoice_ids += ExteriorLine.search([
                ('dgii_report_id', '=', report.id)
            ]).mapped('invoice_id')
            for inv in invoice_ids:
                if (inv.payment_state in ['paid']) and \
                        self._include_in_current_report(inv):
                    inv.fiscal_status = 'normal'
                    continue

                else:
                    inv.fiscal_status = 'blocked'

    def state_sent(self):
        user = self.env['res.users'].browse(self.env.uid)
        # converting time to users timezone
        if user.tz:
            tz = pytz.timezone(user.tz) or pytz.utc
            time = pytz.utc.localize(dt.now()).astimezone(tz)
        else:
            time = dt.now()

        for report in self:
            report._invoice_status_sent()
            report.state = 'sent'
            report.last_date_sent = time

    def state_regenerated(self):
        for report in self:
            report.state = 'generated'
            report.regenerate = 'rege'
            report._invoice_status_regenerate()




    def get_606_tree_view(self):
        return {
            'name': '606',
            'view_mode': 'tree',
            'res_model': 'dgii.reports.purchase.line',
            'type': 'ir.actions.act_window',
            'view_id':
                self.env.ref('dgii_reports_second.dgii_report_purchase_line_tree').id,
            'domain': [('dgii_report_id', '=', self.id)]
        }


    def get_607_tree_view(self):
        return {
            'name': '607',
            'view_mode': 'tree',
            'res_model': 'dgii.reports.sale.line',
            'type': 'ir.actions.act_window',
            'view_id':
                self.env.ref('dgii_reports_second.dgii_report_sale_line_tree').id,
            'domain': ['&',('dgii_report_id', '=', self.id), ('is_csmr','=',False)]
        }

    def get_consumer_tree_view(self):
        return {
            'name': 'Consumer invoices detail',
            'view_mode': 'tree',
            'res_model': 'dgii.reports.sale.line',
            'type': 'ir.actions.act_window',
            'view_id':
                self.env.ref('dgii_reports_second.dgii_report_sale_line_tree').id,
            'domain': ['&',('dgii_report_id', '=', self.id), ('is_cs','=',True)]
        }


    def get_608_tree_view(self):
        return {
            'name': '608',
            'view_mode': 'tree',
            'res_model': 'dgii.reports.cancel.line',
            'type': 'ir.actions.act_window',
            'view_id':
                self.env.ref('dgii_reports_second.dgii_cancel_report_line_tree').id,
            'domain': [('dgii_report_id', '=', self.id)]
        }

    def get_609_tree_view(self):
        return {
            'name': '609',
            'view_mode': 'tree',
            'res_model': 'dgii.reports.exterior.line',
            'type': 'ir.actions.act_window',
            'view_id':
                self.env.ref('dgii_reports_second.dgii_exterior_report_line_tree').id,
            'domain': [('dgii_report_id', '=', self.id)]
        }


class DgiiReportPurchaseLine(models.Model):
    _name = 'dgii.reports.purchase.line'
    _description = "DGII Reports Purchase Line"
    _order = 'line asc'

    dgii_report_id = fields.Many2one('dgii.reports', ondelete='cascade')
    line = fields.Integer()

    rnc_cedula = fields.Char(size=11)
    identification_type = fields.Char(size=1)
    expense_type = fields.Char(size=2)
    fiscal_invoice_number = fields.Char(size=19)
    modified_invoice_number = fields.Char(size=19)
    invoice_date = fields.Date()
    payment_date = fields.Date()
    service_total_amount = fields.Float()
    good_total_amount = fields.Float()
    invoiced_amount = fields.Float()
    invoiced_itbis = fields.Float()
    withholded_itbis = fields.Float()
    proportionality_tax = fields.Float()
    cost_itbis = fields.Float()
    advance_itbis = fields.Float()
    purchase_perceived_itbis = fields.Float()
    isr_withholding_type = fields.Char()
    income_withholding = fields.Float()
    purchase_perceived_isr = fields.Float()
    selective_tax = fields.Float()
    other_taxes = fields.Float()
    legal_tip = fields.Float()
    payment_type = fields.Char()

    invoice_partner_id = fields.Many2one('res.partner')
    invoice_id = fields.Many2one('account.move')
    credit_note = fields.Boolean()


class DgiiReportSaleLine(models.Model):
    _name = 'dgii.reports.sale.line'
    _description = "DGII Reports Sale Line"

    dgii_report_id = fields.Many2one('dgii.reports', ondelete='cascade')
    line = fields.Integer()

    rnc_cedula = fields.Char(size=11)
    identification_type = fields.Char(size=1)
    fiscal_invoice_number = fields.Char(size=19)
    modified_invoice_number = fields.Char(size=19)
    income_type = fields.Char()
    invoice_date = fields.Date()
    withholding_date = fields.Date()
    invoiced_amount = fields.Float()
    invoiced_itbis = fields.Float()
    third_withheld_itbis = fields.Float()
    perceived_itbis = fields.Float()
    third_income_withholding = fields.Float()
    perceived_isr = fields.Float()
    selective_tax = fields.Float()
    other_taxes = fields.Float()
    legal_tip = fields.Float()

    # Tipo de Venta/ Forma de pago
    cash = fields.Float()
    bank = fields.Float()
    card = fields.Float()
    credit = fields.Float()
    bond = fields.Float()
    swap = fields.Float()
    others = fields.Float()

    invoice_partner_id = fields.Many2one('res.partner')
    invoice_id = fields.Many2one('account.move')
    credit_note = fields.Boolean()
    is_csmr = fields.Boolean()
    is_cs = fields.Boolean()


class DgiiCancelReportLine(models.Model):
    _name = 'dgii.reports.cancel.line'
    _description = "DGII Reports Cancel Line"

    dgii_report_id = fields.Many2one('dgii.reports', ondelete='cascade')
    line = fields.Integer()

    fiscal_invoice_number = fields.Char(size=19)
    invoice_date = fields.Date()
    anulation_type = fields.Char(size=2)

    invoice_partner_id = fields.Many2one('res.partner')
    invoice_id = fields.Many2one('account.move')


class DgiiExteriorReportLine(models.Model):
    _name = 'dgii.reports.exterior.line'
    _description = "DGII Reports Exterior Line"

    dgii_report_id = fields.Many2one('dgii.reports', ondelete='cascade')
    line = fields.Integer()

    legal_name = fields.Char()
    tax_id_type = fields.Integer()
    tax_id = fields.Char()
    country_code = fields.Char()
    purchased_service_type = fields.Char(size=2)
    service_type_detail = fields.Char(size=2)
    related_part = fields.Integer()
    doc_number = fields.Char()
    doc_date = fields.Date()
    invoiced_amount = fields.Float()
    isr_withholding_date = fields.Date()
    presumed_income = fields.Float()
    withholded_isr = fields.Float()
    invoice_id = fields.Many2one('account.move')
